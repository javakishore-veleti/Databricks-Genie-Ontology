from __future__ import annotations

from typing import Any, Protocol


class SqlFacade(Protocol):
    def execute(self, statement: str) -> Any: ...

    def execute_ok(self, statement: str) -> bool: ...

    def first_cell(self, result: Any) -> str | None: ...

    def insert_pandas(
        self,
        pdf: Any,
        table_name: str,
        column_types: dict[str, str],
        batch_size: int = 80,
    ) -> None: ...
