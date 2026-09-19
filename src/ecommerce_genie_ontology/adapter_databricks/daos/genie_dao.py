from __future__ import annotations

from datetime import timedelta
from typing import Any

from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession


class GenieDao:
    def __init__(self, session: WorkspaceSession) -> None:
        self._session = session

    def list_spaces(self) -> list[Any]:
        spaces: list[Any] = []
        page_token = None
        while True:
            response = self._session.workspace.genie.list_spaces(
                page_size=100, page_token=page_token
            )
            spaces.extend(response.spaces or [])
            page_token = response.next_page_token
            if not page_token:
                break
        return spaces

    def find_space(self, title: str | None = None) -> Any | None:
        wanted = title or self._session.agent_title
        if title is None and self._session.space_id:
            return self._session.workspace.genie.get_space(
                self._session.space_id, include_serialized_space=True
            )
        for space in self.list_spaces():
            if space.title == wanted:
                return space
        return None

    def create_or_update_space(
        self,
        serialized_space: str,
        description: str,
        title: str | None = None,
    ) -> Any:
        space_title = title or self._session.agent_title
        existing = self.find_space(space_title)
        parent_path = self._session.parent_path or None
        if existing and existing.space_id:
            return self._session.workspace.genie.update_space(
                space_id=existing.space_id,
                title=space_title,
                description=description,
                warehouse_id=self._session.warehouse_id,
                serialized_space=serialized_space,
                parent_path=parent_path,
            )
        return self._session.workspace.genie.create_space(
            warehouse_id=self._session.warehouse_id,
            serialized_space=serialized_space,
            title=space_title,
            description=description,
            parent_path=parent_path,
        )

    def trash_space(self, space_id: str) -> None:
        self._session.workspace.genie.trash_space(space_id)

    def start_conversation(self, space_id: str, question: str) -> Any:
        return self._session.workspace.genie.start_conversation_and_wait(
            space_id=space_id,
            content=question,
            timeout=timedelta(minutes=10),
        )

    def query_result(
        self,
        space_id: str,
        conversation_id: str,
        message_id: str,
        attachment_id: str,
    ) -> Any:
        return self._session.workspace.genie.get_message_attachment_query_result(
            space_id=space_id,
            conversation_id=conversation_id,
            message_id=message_id,
            attachment_id=attachment_id,
        )

    def assign_entity_tag(self, entity_name: str, tag_key: str, tag_value: str = "") -> None:
        self._session.workspace.api_client.do(
            "POST",
            "/api/2.1/unity-catalog/entity-tag-assignments",
            body={
                "entity_name": entity_name,
                "entity_type": "GENIE_SPACE",
                "tag_key": tag_key,
                "tag_value": tag_value,
            },
        )
