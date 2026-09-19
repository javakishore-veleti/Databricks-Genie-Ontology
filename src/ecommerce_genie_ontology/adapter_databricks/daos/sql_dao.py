from __future__ import annotations

import math
import time
from datetime import datetime
from decimal import Decimal
from typing import Any

from databricks.sdk.service.sql import StatementState

from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.utils.sql_text import sql_string

_PENDING = {
    getattr(StatementState, name)
    for name in ("PENDING", "RUNNING")
    if hasattr(StatementState, name)
}
_SUCCESS = {
    getattr(StatementState, name)
    for name in ("SUCCEEDED", "SUCCESS")
    if hasattr(StatementState, name)
}


class SqlDao:
    def __init__(self, session: WorkspaceSession) -> None:
        self._session = session

    def execute(self, statement: str) -> Any:
        if self._session.spark is not None:
            return self._session.spark.sql(statement)
        client = self._session.workspace.statement_execution
        result = client.execute_statement(
            warehouse_id=self._session.warehouse_id,
            statement=statement,
            wait_timeout="50s",
            catalog=self._session.catalog,
            schema=self._session.schema_name,
        )
        deadline = time.time() + 600
        while result.status and result.status.state in _PENDING:
            if time.time() > deadline:
                raise TimeoutError(f"SQL timed out: {statement[:200]}")
            time.sleep(2)
            if not result.statement_id:
                break
            result = client.get_statement(result.statement_id)
        state = result.status.state if result.status else None
        if state is None or state in _SUCCESS:
            return result
        if state in _PENDING:
            raise TimeoutError(f"SQL still pending: {statement[:200]}")
        message = ""
        if result.status and result.status.error:
            message = result.status.error.message or str(result.status.error)
        raise RuntimeError(f"SQL failed ({state}): {message or statement[:200]}")

    def execute_ok(self, statement: str) -> bool:
        try:
            self.execute(statement)
            print(f"OK    {statement}")
            return True
        except Exception as exc:
            print(f"SKIP  {statement} -> {exc}")
            return False

    def first_cell(self, result: Any) -> str | None:
        if self._session.spark is not None:
            collected = result.collect()
            return collected[0][0] if collected else None
        data = getattr(getattr(result, "result", None), "data_array", None)
        return data[0][0] if data else None

    def insert_pandas(
        self,
        pdf: Any,
        table_name: str,
        column_types: dict[str, str],
        batch_size: int = 80,
    ) -> None:
        fq_table = f"{self._session.fq_schema}.{table_name}"
        columns = list(column_types)
        if self._session.spark is not None:
            sdf = self._session.spark.createDataFrame(pdf)
            for col, dtype in column_types.items():
                sdf = sdf.withColumn(col, sdf[col].cast(dtype))
            sdf = sdf.select(*columns)
            sdf.write.insertInto(fq_table, overwrite=True)
            print(f"Loaded {sdf.count()} rows into {fq_table}")
            return
        self.execute(f"TRUNCATE TABLE {fq_table}")
        total = 0
        for start in range(0, len(pdf), batch_size):
            chunk = pdf.iloc[start : start + batch_size]
            values = []
            for row in chunk[columns].itertuples(index=False, name=None):
                rendered = ", ".join(
                    _sql_literal(value, column_types[col]) for col, value in zip(columns, row)
                )
                values.append(f"({rendered})")
            self.execute(
                f"INSERT INTO {fq_table} ({', '.join(columns)}) VALUES {', '.join(values)}"
            )
            total += len(chunk)
        print(f"Loaded {total} rows into {fq_table}")


def _to_python(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _sql_literal(value: Any, dtype: str) -> str:
    value = _to_python(value)
    kind = dtype.lower()
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NULL"
    if kind.startswith("bool"):
        return "TRUE" if bool(value) else "FALSE"
    if kind.startswith("date"):
        if isinstance(value, datetime):
            value = value.date()
        return f"DATE '{value}'"
    if kind.startswith(("int", "bigint", "smallint", "tinyint", "double", "float", "decimal")):
        return str(value)
    return sql_string(str(value))
