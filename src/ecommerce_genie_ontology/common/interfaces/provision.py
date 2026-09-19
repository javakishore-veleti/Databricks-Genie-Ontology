from __future__ import annotations

from typing import Any, Protocol


class ProvisionWorkspaceFacade(Protocol):
    catalog: str
    schema_name: str
    warehouse_id: str
    agent_title: str
    spark: Any
    admin_emails: tuple[str, ...]

    @property
    def fq_schema(self) -> str: ...

    @property
    def fq_oltp(self) -> str: ...

    def sql(self, statement: str) -> Any: ...

    def sql_ok(self, statement: str) -> bool: ...

    def insert_pandas(
        self,
        pdf: Any,
        table_name: str,
        column_types: dict[str, str],
        batch_size: int = 80,
    ) -> None: ...

    def ensure_domain_tag_policies(self, domain_names: list[str]) -> None: ...

    def try_create_page(self, page: dict) -> bool: ...

    def share_catalog(self) -> None: ...
