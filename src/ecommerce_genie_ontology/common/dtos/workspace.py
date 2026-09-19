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

    @property
    def fq_schema(self) -> str:
        return f"{self.catalog}.{self.schema_name}"
