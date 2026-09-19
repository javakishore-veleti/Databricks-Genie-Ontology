from __future__ import annotations

from typing import Any

from ecommerce_genie_ontology.adapter_databricks.daos.sql_dao import SqlDao
from ecommerce_genie_ontology.common.interfaces.sql import SqlFacade


class SqlFacadeImpl:
    def __init__(self, sql_dao: SqlDao) -> None:
        self._sql = sql_dao

    def execute(self, statement: str) -> Any:
        return self._sql.execute(statement)

    def execute_ok(self, statement: str) -> bool:
        return self._sql.execute_ok(statement)

    def first_cell(self, result: Any) -> str | None:
        return self._sql.first_cell(result)

    def insert_pandas(
        self,
        pdf: Any,
        table_name: str,
        column_types: dict[str, str],
        batch_size: int = 80,
    ) -> None:
        self._sql.insert_pandas(pdf, table_name, column_types, batch_size)


def _assert_protocol() -> None:
    _: type[SqlFacade] = SqlFacadeImpl
