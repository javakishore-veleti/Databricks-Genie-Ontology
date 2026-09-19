from __future__ import annotations

from typing import Any, Protocol


class CreateAgentsWorkspaceFacade(Protocol):
    catalog: str
    schema_name: str
    warehouse_id: str
    agent_title: str
    parent_path: str
    space_id: str

    @property
    def fq_schema(self) -> str: ...

    def sql(self, statement: str) -> Any: ...

    def upsert_genie_agent(self, serialized_space: str, description: str) -> str: ...

    def certify_and_tag_agent(self, space_id: str) -> None: ...
