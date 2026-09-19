from __future__ import annotations

from typing import Any

from ecommerce_genie_ontology.adapter_databricks.objects_factory import AdapterDatabricksObjectsFactory
from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.interfaces.create_agents import CreateAgentsWorkspaceFacade
from ecommerce_genie_ontology.common.interfaces.genie import GenieFacade
from ecommerce_genie_ontology.common.interfaces.sql import SqlFacade


class CreateAgentsWorkspaceFacadeImpl:
    def __init__(
        self,
        session: WorkspaceSession,
        sql_facade: SqlFacade,
        genie_facade: GenieFacade,
    ) -> None:
        self._session = session
        self._sql = sql_facade
        self._genie = genie_facade

    @classmethod
    def from_factory(cls, factory: AdapterDatabricksObjectsFactory) -> CreateAgentsWorkspaceFacadeImpl:
        return cls(factory.session(), factory.sql_facade(), factory.genie_facade())

    @classmethod
    def from_databricks(cls, dbutils: Any, spark: Any) -> CreateAgentsWorkspaceFacadeImpl:
        return cls.from_factory(AdapterDatabricksObjectsFactory.from_databricks(dbutils, spark))

    @property
    def catalog(self) -> str:
        return self._session.catalog

    @property
    def schema_name(self) -> str:
        return self._session.schema_name

    @property
    def warehouse_id(self) -> str:
        return self._session.warehouse_id

    @property
    def agent_title(self) -> str:
        return self._session.agent_title

    @property
    def parent_path(self) -> str:
        return self._session.parent_path

    @property
    def space_id(self) -> str:
        return self._session.space_id

    @property
    def fq_schema(self) -> str:
        return self._session.fq_schema

    @property
    def fq_oltp(self) -> str:
        return self._session.context.fq_oltp

    def sql(self, statement: str) -> Any:
        return self._sql.execute(statement)

    def upsert_genie_agent(
        self, serialized_space: str, description: str, title: str | None = None
    ) -> str:
        return self._genie.upsert_agent(serialized_space, description, title=title)

    def certify_and_tag_agent(self, space_id: str) -> None:
        self._genie.certify_and_tag_agent(space_id)


def _assert_protocol() -> None:
    _: type[CreateAgentsWorkspaceFacade] = CreateAgentsWorkspaceFacadeImpl
