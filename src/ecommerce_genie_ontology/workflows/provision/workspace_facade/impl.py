from __future__ import annotations

from typing import Any

from ecommerce_genie_ontology.adapter_databricks.objects_factory import AdapterDatabricksObjectsFactory
from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.interfaces.governance import GovernanceFacade
from ecommerce_genie_ontology.common.interfaces.provision import ProvisionWorkspaceFacade
from ecommerce_genie_ontology.common.interfaces.sql import SqlFacade


class ProvisionWorkspaceFacadeImpl:
    def __init__(
        self,
        session: WorkspaceSession,
        sql_facade: SqlFacade,
        governance_facade: GovernanceFacade,
    ) -> None:
        self._session = session
        self._sql = sql_facade
        self._governance = governance_facade

    @classmethod
    def from_factory(cls, factory: AdapterDatabricksObjectsFactory) -> ProvisionWorkspaceFacadeImpl:
        return cls(factory.session(), factory.sql_facade(), factory.governance_facade())

    @classmethod
    def from_databricks(cls, dbutils: Any, spark: Any) -> ProvisionWorkspaceFacadeImpl:
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
    def admin_emails(self) -> tuple[str, ...]:
        return self._session.context.admin_emails

    @property
    def spark(self) -> Any:
        return self._session.spark

    @property
    def fq_schema(self) -> str:
        return self._session.fq_schema

    @property
    def fq_oltp(self) -> str:
        return self._session.context.fq_oltp

    def sql(self, statement: str) -> Any:
        return self._sql.execute(statement)

    def sql_ok(self, statement: str) -> bool:
        return self._sql.execute_ok(statement)

    def insert_pandas(
        self,
        pdf: Any,
        table_name: str,
        column_types: dict[str, str],
        batch_size: int = 80,
    ) -> None:
        self._sql.insert_pandas(pdf, table_name, column_types, batch_size)

    def ensure_domain_tag_policies(self, domain_names: list[str]) -> None:
        self._governance.ensure_domain_tag_policies(domain_names)

    def ensure_discover_domains(self, domains: list[dict]) -> list[dict]:
        return self._governance.ensure_discover_domains(domains)

    def try_create_page(self, page: dict) -> bool:
        return self._governance.try_create_page(page)

    def share_catalog(self) -> None:
        from databricks.sdk.service.catalog import IsolationMode, PermissionsChange, Privilege

        name = self.catalog
        client = self._session.workspace
        try:
            client.catalogs.update(name, isolation_mode=IsolationMode.ISOLATION_MODE_OPEN)
            print(f"OK    catalog {name} isolation OPEN")
        except Exception as exc:
            print(f"SKIP  catalog isolation -> {exc}")
        workspace_id = self._session.context.workspace_id
        if workspace_id:
            try:
                client.workspace_bindings.update(name, assign_workspaces=[int(workspace_id)])
                print(f"OK    bound catalog {name} to workspace {workspace_id}")
            except Exception as exc:
                print(f"SKIP  catalog bind -> {exc}")
        principals = ["account users", *self.admin_emails]
        privileges = [
            Privilege.ALL_PRIVILEGES,
            Privilege.BROWSE,
            Privilege.USE_CATALOG,
            Privilege.USE_SCHEMA,
            Privilege.SELECT,
        ]
        try:
            client.grants.update(
                "catalog",
                name,
                changes=[PermissionsChange(principal=principal, add=privileges) for principal in principals],
            )
            print(f"OK    granted catalog {name} to {len(principals)} principal(s)")
        except Exception as exc:
            print(f"SKIP  catalog grant -> {exc}")


def _assert_protocol() -> None:
    _: type[ProvisionWorkspaceFacade] = ProvisionWorkspaceFacadeImpl
