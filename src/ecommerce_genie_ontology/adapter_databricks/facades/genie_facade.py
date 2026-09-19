from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ecommerce_genie_ontology.adapter_databricks.daos.genie_dao import GenieDao
from ecommerce_genie_ontology.adapter_databricks.daos.sql_dao import SqlDao
from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.constants.fraud_agents import FRAUD_AGENTS
from ecommerce_genie_ontology.common.constants.ontology import AGENT_TITLE
from ecommerce_genie_ontology.common.interfaces.genie import GenieFacade
from ecommerce_genie_ontology.common.utils.sql_text import sql_string


class GenieFacadeImpl:
    def __init__(self, session: WorkspaceSession, genie_dao: GenieDao, sql_dao: SqlDao) -> None:
        self._session = session
        self._genie = genie_dao
        self._sql = sql_dao

    def upsert_agent(self, serialized_space: str, description: str, title: str | None = None) -> str:
        space = self._genie.create_or_update_space(serialized_space, description, title=title)
        if not space.space_id:
            raise RuntimeError("Genie create/update returned no space_id")
        self.write_registry(space.space_id, title=title)
        return space.space_id

    def certify_and_tag_agent(self, space_id: str) -> None:
        for tag_key, tag_value in (("system.certification_status", "certified"), ("Sales", "")):
            try:
                self._genie.assign_entity_tag(space_id, tag_key, tag_value)
                print(f"OK    tagged Genie agent via {tag_key}")
            except Exception as exc:
                print(f"SKIP  Genie agent tag {tag_key} -> {exc}")

    def write_registry(self, space_id: str, title: str | None = None) -> None:
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
        agent_title = title or self._session.agent_title
        quoted = sql_string(agent_title)
        self._sql.execute(f"DELETE FROM {fq}._genie_agent_registry WHERE title = {quoted}")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self._sql.execute(
            f"""
INSERT INTO {fq}._genie_agent_registry (space_id, title, warehouse_id, updated_at)
VALUES ({sql_string(space_id)}, {quoted}, {sql_string(self._session.warehouse_id)}, TIMESTAMP '{now}')
"""
        )

    def resolve_space_id(self, title: str | None = None) -> str:
        wanted = title or self._session.agent_title
        if title is None and self._session.space_id:
            return self._session.space_id
        try:
            rows = self._sql.execute(
                f"SELECT space_id FROM {self._session.fq_schema}._genie_agent_registry "
                f"WHERE title = {sql_string(wanted)} LIMIT 1"
            )
            found = self._sql.first_cell(rows)
            if found:
                return found
        except Exception as exc:
            print(f"SKIP  registry lookup -> {exc}")
        space = self._genie.find_space(wanted)
        if space and space.space_id:
            return space.space_id
        raise RuntimeError(
            f"Could not find Genie agent {wanted!r}. Run create_agents first or set GENIE_SPACE_ID."
        )

    def ask(self, question: str) -> None:
        result = self.ask_reply(question)
        print(f"SPACE_ID = {result.get('space_id')}")
        print(f"QUESTION = {question}")
        print(f"STATUS   = {result.get('status')}")
        if result.get("error"):
            print(f"ERROR    = {result['error']}")
        if result.get("content"):
            print(f"CONTENT  = {result['content']}")
        if result.get("rendered"):
            print(result["rendered"])

    def ask_reply(self, question: str, title: str | None = None) -> dict:
        space_id = self.resolve_space_id(title)
        message = self._genie.start_conversation(space_id, question)
        rendered = _attachment_text(message)
        return {
            "space_id": space_id,
            "status": str(getattr(message, "status", "") or ""),
            "error": str(getattr(message, "error", "") or ""),
            "content": getattr(message, "content", None) or "",
            "rendered": rendered,
        }

    def trash_agent(self) -> None:
        titles = [AGENT_TITLE, self._session.agent_title, *[str(item["title"]) for item in FRAUD_AGENTS]]
        seen: set[str] = set()
        for title in titles:
            if title in seen:
                continue
            seen.add(title)
            try:
                space = self._genie.find_space(title)
            except Exception as exc:
                print(f"SKIP  list Genie spaces ({title}) -> {exc}")
                continue
            if not space or not space.space_id:
                print(f"SKIP  no Genie agent named {title!r} to trash")
                continue
            try:
                self._genie.trash_space(space.space_id)
                print(f"Trashed Genie agent {title} {space.space_id}")
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
