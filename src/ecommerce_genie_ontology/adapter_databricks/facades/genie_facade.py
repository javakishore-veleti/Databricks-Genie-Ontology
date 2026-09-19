from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ecommerce_genie_ontology.adapter_databricks.daos.genie_dao import GenieDao
from ecommerce_genie_ontology.adapter_databricks.daos.sql_dao import SqlDao
from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.interfaces.genie import GenieFacade
from ecommerce_genie_ontology.common.utils.sql_text import sql_string


class GenieFacadeImpl:
    def __init__(self, session: WorkspaceSession, genie_dao: GenieDao, sql_dao: SqlDao) -> None:
        self._session = session
        self._genie = genie_dao
        self._sql = sql_dao

    def upsert_agent(self, serialized_space: str, description: str) -> str:
        space = self._genie.create_or_update_space(serialized_space, description)
        if not space.space_id:
            raise RuntimeError("Genie create/update returned no space_id")
        self.write_registry(space.space_id)
        return space.space_id

    def certify_and_tag_agent(self, space_id: str) -> None:
        for tag_key, tag_value in (("system.certification_status", "certified"), ("Sales", "")):
            try:
                self._genie.assign_entity_tag(space_id, tag_key, tag_value)
                print(f"OK    tagged Genie agent via {tag_key}")
            except Exception as exc:
                print(f"SKIP  Genie agent tag {tag_key} -> {exc}")

    def write_registry(self, space_id: str) -> None:
        fq = self._session.fq_schema
        self._sql.execute(
            f"""
CREATE TABLE IF NOT EXISTS {fq}._genie_agent_registry (
  space_id STRING,
  title STRING,
  warehouse_id STRING,
  updated_at TIMESTAMP
)
COMMENT 'Registry of Genie agents created by the ontology workflows'
"""
        )
        title = sql_string(self._session.agent_title)
        self._sql.execute(f"DELETE FROM {fq}._genie_agent_registry WHERE title = {title}")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self._sql.execute(
            f"""
INSERT INTO {fq}._genie_agent_registry (space_id, title, warehouse_id, updated_at)
VALUES ({sql_string(space_id)}, {title}, {sql_string(self._session.warehouse_id)}, TIMESTAMP '{now}')
"""
        )

    def resolve_space_id(self) -> str:
        if self._session.space_id:
            return self._session.space_id
        try:
            rows = self._sql.execute(
                f"SELECT space_id FROM {self._session.fq_schema}._genie_agent_registry "
                f"WHERE title = {sql_string(self._session.agent_title)} LIMIT 1"
            )
            found = self._sql.first_cell(rows)
            if found:
                return found
        except Exception as exc:
            print(f"SKIP  registry lookup -> {exc}")
        space = self._genie.find_space()
        if space and space.space_id:
            return space.space_id
        raise RuntimeError(
            f"Could not find Genie agent '{self._session.agent_title}'. Run create_agents first or set GENIE_SPACE_ID."
        )

    def ask(self, question: str) -> None:
        space_id = self.resolve_space_id()
        print(f"SPACE_ID = {space_id}")
        print(f"QUESTION = {question}")
        message = self._genie.start_conversation(space_id, question)
        print(f"STATUS   = {getattr(message, 'status', None)}")
        if getattr(message, "error", None):
            print(f"ERROR    = {message.error}")
        if getattr(message, "content", None):
            print(f"CONTENT  = {message.content}")
        rendered = _attachment_text(message)
        if rendered:
            print(rendered)
        conversation_id = getattr(message, "conversation_id", None)
        message_id = getattr(message, "id", None)
        for attachment in getattr(message, "attachments", None) or []:
            query = getattr(attachment, "query", None)
            attachment_id = getattr(attachment, "attachment_id", None) or getattr(attachment, "id", None)
            if query and attachment_id and conversation_id and message_id:
                try:
                    result = self._genie.query_result(
                        space_id, conversation_id, message_id, attachment_id
                    )
                    print(f"QUERY RESULT = {result}")
                except Exception as exc:
                    print(f"SKIP  query result -> {exc}")

    def trash_agent(self) -> None:
        try:
            space = self._genie.find_space()
        except Exception as exc:
            print(f"SKIP  list Genie spaces -> {exc}")
            return
        if not space or not space.space_id:
            print(f"SKIP  no Genie agent named '{self._session.agent_title}' to trash")
            return
        try:
            self._genie.trash_space(space.space_id)
            print(f"Trashed Genie agent {space.space_id}")
        except Exception as exc:
            print(f"SKIP  trash Genie agent {space.space_id} -> {exc}")


def _attachment_text(message: Any) -> str:
    parts: list[str] = []
    for attachment in getattr(message, "attachments", None) or []:
        text = getattr(attachment, "text", None)
        if text and getattr(text, "content", None):
            parts.append(text.content)
        query = getattr(attachment, "query", None)
        if query and getattr(query, "query", None):
            parts.append(f"SQL:\n{query.query}")
    return "\n\n".join(parts)


def _assert_protocol() -> None:
    _: type[GenieFacade] = GenieFacadeImpl
