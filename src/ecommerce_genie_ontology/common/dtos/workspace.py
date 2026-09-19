from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkspaceContext:
    catalog: str
    schema_name: str
    warehouse_id: str
    agent_title: str
    parent_path: str
    space_id: str
    package_path: str
    question: str = ""
    confirm: str = ""
    admin_emails: tuple[str, ...] = ()
    workspace_id: int | None = None
    oltp_schema: str = "retail_oltp"
    customer_count: int = 200
    orders_per_year: int = 25000
    year_count: int = 3
    cdc_count: int = 1000
    year_window: str = "latest"

    @property
    def fq_schema(self) -> str:
        return f"{self.catalog}.{self.schema_name}"

    @property
    def fq_oltp(self) -> str:
        return f"{self.catalog}.{self.oltp_schema}"
