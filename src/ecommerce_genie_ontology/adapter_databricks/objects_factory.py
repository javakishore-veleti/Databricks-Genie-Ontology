"""Singleton lookup for Databricks DAOs and facade implementations."""

from __future__ import annotations

from typing import Any

from ecommerce_genie_ontology.adapter_databricks.daos.apps_dao import AppsDao
from ecommerce_genie_ontology.adapter_databricks.daos.genie_dao import GenieDao
from ecommerce_genie_ontology.adapter_databricks.daos.jobs_dao import JobsDao
from ecommerce_genie_ontology.adapter_databricks.daos.sql_dao import SqlDao
from ecommerce_genie_ontology.adapter_databricks.daos.tags_dao import TagsDao
from ecommerce_genie_ontology.adapter_databricks.facades.genie_facade import GenieFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.facades.governance_facade import GovernanceFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.facades.jobs_facade import JobsFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.facades.dy_facade import DyFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.facades.pipeline_facade import PipelineFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.facades.pw_facade import PwFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.facades.sql_facade import SqlFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.facades.tc_facade import TcFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.facades.wh_facade import WhFacadeImpl
from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.dtos.account import AccountSettings
from ecommerce_genie_ontology.common.dtos.settings import Settings
from ecommerce_genie_ontology.common.interfaces.genie import GenieFacade
from ecommerce_genie_ontology.common.interfaces.governance import GovernanceFacade
from ecommerce_genie_ontology.common.interfaces.jobs import JobsFacade
from ecommerce_genie_ontology.common.interfaces.pipeline import PipelineFacade
from ecommerce_genie_ontology.common.interfaces.dy import DyFacade
from ecommerce_genie_ontology.common.interfaces.pw import PwFacade
from ecommerce_genie_ontology.common.interfaces.sql import SqlFacade
from ecommerce_genie_ontology.common.interfaces.tc import TcFacade
from ecommerce_genie_ontology.common.interfaces.wh import WhFacade
from ecommerce_genie_ontology.common.utils.objects_factory import ObjectsFactory


class AdapterDatabricksObjectsFactory(ObjectsFactory):
    def __init__(self, settings: Settings | None = None, session: WorkspaceSession | None = None) -> None:
        super().__init__()
        self._settings = settings
        self._session = session

    @classmethod
    def instance(cls) -> AdapterDatabricksObjectsFactory:
        return super().instance()  # type: ignore[return-value]

    @classmethod
    def from_databricks(cls, dbutils: Any, spark: Any) -> AdapterDatabricksObjectsFactory:
        factory = cls(session=WorkspaceSession.from_databricks(dbutils, spark))
        ObjectsFactory._factories[cls] = factory
        return factory

    def settings(self) -> Settings:
        return self.singleton("settings", lambda: self._settings or Settings.load())

    def session(self) -> WorkspaceSession:
        return self.singleton(
            "session",
            lambda: self._session or WorkspaceSession.from_settings(self.settings()),
        )

    def sql_dao(self) -> SqlDao:
        return self.singleton("sql_dao", lambda: SqlDao(self.session()))

    def genie_dao(self) -> GenieDao:
        return self.singleton("genie_dao", lambda: GenieDao(self.session()))

    def tags_dao(self) -> TagsDao:
        return self.singleton("tags_dao", lambda: TagsDao(self.session()))

    def jobs_dao(self) -> JobsDao:
        return self.singleton("jobs_dao", lambda: JobsDao(self.session(), self.settings()))

    def apps_dao(self) -> AppsDao:
        return self.singleton("apps_dao", lambda: AppsDao(self.session()))

    def sql_facade(self) -> SqlFacade:
        return self.singleton("sql_facade", lambda: SqlFacadeImpl(self.sql_dao()))

    def genie_facade(self) -> GenieFacade:
        return self.singleton(
            "genie_facade",
            lambda: GenieFacadeImpl(self.session(), self.genie_dao(), self.sql_dao()),
        )

    def governance_facade(self) -> GovernanceFacade:
        return self.singleton(
            "governance_facade",
            lambda: GovernanceFacadeImpl(self.tags_dao()),
        )

    def jobs_facade(self) -> JobsFacade:
        return self.singleton(
            "jobs_facade",
            lambda: JobsFacadeImpl(self.jobs_dao(), self.settings()),
        )

    def account_settings(self) -> AccountSettings:
        return self.singleton("account_settings", AccountSettings.load)

    def account_session(self):
        from ecommerce_genie_ontology.adapter_databricks.account_session import AccountSession

        return self.singleton(
            "account_session",
            lambda: AccountSession.from_settings(self.account_settings()),
        )

    def account_dao(self):
        from ecommerce_genie_ontology.adapter_databricks.daos.account_dao import AccountDao

        return self.singleton("account_dao", lambda: AccountDao(self.account_session()))

    def pw_facade(self) -> PwFacade:
        return self.singleton("pw_facade", lambda: PwFacadeImpl(self.account_dao()))

    def wh_facade(self) -> WhFacade:
        return self.singleton("wh_facade", lambda: WhFacadeImpl(self.account_dao()))

    def tc_facade(self) -> TcFacade:
        return self.singleton(
            "tc_facade",
            lambda: TcFacadeImpl(self.session(), self.sql_facade(), self.genie_facade()),
        )

    def dy_facade(self) -> DyFacade:
        return self.singleton(
            "dy_facade",
            lambda: DyFacadeImpl(self.account_dao(), self.settings()),
        )

    def pipeline_facade(self) -> PipelineFacade:
        return self.singleton(
            "pipeline_facade",
            lambda: PipelineFacadeImpl.from_factory(self),
        )
