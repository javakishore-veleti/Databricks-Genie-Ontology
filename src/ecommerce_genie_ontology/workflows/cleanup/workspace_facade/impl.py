from __future__ import annotations

from typing import Any

from ecommerce_genie_ontology.adapter_databricks.objects_factory import AdapterDatabricksObjectsFactory
from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.interfaces.cleanup import CleanupWorkspaceFacade
from ecommerce_genie_ontology.common.interfaces.genie import GenieFacade
from ecommerce_genie_ontology.common.interfaces.sql import SqlFacade


class CleanupWorkspaceFacadeImpl:
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
    def from_factory(cls, factory: AdapterDatabricksObjectsFactory) -> CleanupWorkspaceFacadeImpl:
        return cls(factory.session(), factory.sql_facade(), factory.genie_facade())

    @classmethod
    def from_databricks(cls, dbutils: Any, spark: Any) -> CleanupWorkspaceFacadeImpl:
        return cls.from_factory(AdapterDatabricksObjectsFactory.from_databricks(dbutils, spark))

    @property
    def confirm(self) -> str:
        return self._session.context.confirm

    @confirm.setter
    def confirm(self, value: str) -> None:
        self._session.context.confirm = value

    @property
    def catalog(self) -> str:
        return self._session.catalog

    @property
    def agent_title(self) -> str:
        return self._session.agent_title

    def trash_agent(self) -> None:
        self._genie.trash_agent()

    def drop_catalog(self) -> None:
        self._sql.execute(f"DROP CATALOG IF EXISTS {self.catalog} CASCADE")
        print(f"Dropped catalog {self.catalog} (schema, tables, and metric views removed).")


def _assert_protocol() -> None:
    _: type[CleanupWorkspaceFacade] = CleanupWorkspaceFacadeImpl
