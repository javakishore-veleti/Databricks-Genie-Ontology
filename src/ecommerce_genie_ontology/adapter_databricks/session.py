from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from databricks.sdk import WorkspaceClient

from ecommerce_genie_ontology.common.dtos.settings import Settings
from ecommerce_genie_ontology.common.dtos.workspace import WorkspaceContext


def build_workspace_client(settings: Settings) -> WorkspaceClient:
    kwargs: dict[str, str] = {"host": settings.host}
    if settings.token:
        kwargs["token"] = settings.token
    if settings.client_id and settings.client_secret:
        kwargs["client_id"] = settings.client_id
        kwargs["client_secret"] = settings.client_secret
    return WorkspaceClient(**kwargs)


@dataclass
class WorkspaceSession:
    context: WorkspaceContext
    workspace: WorkspaceClient
    spark: Any = None

    @property
    def catalog(self) -> str:
        return self.context.catalog

    @property
    def schema_name(self) -> str:
        return self.context.schema_name

    @property
    def warehouse_id(self) -> str:
        return self.context.warehouse_id

    @property
    def agent_title(self) -> str:
        return self.context.agent_title

    @property
    def parent_path(self) -> str:
        return self.context.parent_path

    @property
    def space_id(self) -> str:
        return self.context.space_id

    @property
    def fq_schema(self) -> str:
        return self.context.fq_schema

    @classmethod
    def from_settings(cls, settings: Settings) -> WorkspaceSession:
        account_workspace = _account_workspace(settings)
        workspace = (
            _client_for_account_workspace(account_workspace)
            if account_workspace is not None
            else None
        )
        if workspace is None and settings.host:
            workspace = build_workspace_client(settings)
        if workspace is None:
            raise RuntimeError(
                f"Workspace {settings.workspace_name!r} not found. "
                "Run npm run ecommerce:workspace:databricks-setup first."
            )
        warehouse_id = settings.warehouse_id or _warehouse_id_by_name(workspace, settings.warehouse_name)
        if not warehouse_id:
            raise RuntimeError(
                f"SQL warehouse {settings.warehouse_name!r} not found. "
                "Run npm run ecommerce:warehouse:databricks-setup first."
            )
        _ensure_warehouse_running(workspace, warehouse_id)
        parent_path = settings.genie_parent_path
        if not parent_path:
            me = workspace.current_user.me()
            parent_path = f"/Workspace/Users/{me.user_name or 'Shared'}"
        return cls(
            context=WorkspaceContext(
                catalog=settings.catalog,
                schema_name=settings.schema,
                warehouse_id=warehouse_id,
                agent_title=settings.agent_title,
                parent_path=parent_path,
                space_id=settings.genie_space_id,
                package_path=settings.package_workspace_path,
                admin_emails=settings.admin_emails,
                workspace_id=account_workspace.workspace_id if account_workspace else None,
                oltp_schema=settings.oltp_schema,
                customer_count=settings.customer_count,
                orders_per_year=settings.orders_per_year,
                year_count=settings.year_count,
            ),
            workspace=workspace,
        )

    @classmethod
    def from_databricks(cls, dbutils: Any, spark: Any) -> WorkspaceSession:
        def widget(name: str, default: str = "") -> str:
            try:
                value = dbutils.widgets.get(name)
            except Exception:
                return default
            return value if value is not None else default

        warehouse_id = widget("warehouse_id")
        if not warehouse_id:
            raise RuntimeError("warehouse_id widget is required for Databricks job tasks.")
        return cls(
            context=WorkspaceContext(
                catalog=widget("catalog_name", "ecommerce_genie_ontology"),
                schema_name=widget("schema_name", "retail_star"),
                warehouse_id=warehouse_id,
                agent_title=widget("agent_title", "Retail Analytics Genie"),
                parent_path=widget("parent_path"),
                space_id=widget("space_id"),
                package_path=widget("package_path"),
                question=widget("question"),
                confirm=widget("confirm"),
                oltp_schema=widget("oltp_schema", "retail_oltp"),
                customer_count=int(widget("customer_count", "200") or "200"),
                orders_per_year=int(widget("orders_per_year", "25000") or "25000"),
                year_count=int(widget("year_count", "3") or "3"),
                cdc_count=int(widget("cdc_count", "1000") or "1000"),
                year_window=widget("year_window", "latest") or "latest",
                row_count=int(widget("row_count", "100000") or "100000"),
                months=int(widget("months", "3") or "3"),
                agent_id=widget("agent_id", ""),
            ),
            workspace=WorkspaceClient(),
            spark=spark,
        )


def _account_workspace(settings: Settings):
    try:
        from ecommerce_genie_ontology.adapter_databricks.account_session import AccountSession
        from ecommerce_genie_ontology.common.dtos.account import AccountSettings

        account = AccountSession.from_settings(AccountSettings.load())
        for workspace in account.account.workspaces.list():
            if workspace.workspace_name == settings.workspace_name:
                return workspace
    except Exception:
        return None
    return None


def _client_for_account_workspace(workspace) -> WorkspaceClient:
    from ecommerce_genie_ontology.adapter_databricks.account_session import AccountSession
    from ecommerce_genie_ontology.common.dtos.account import AccountSettings

    account = AccountSession.from_settings(AccountSettings.load())
    return account.account.get_workspace_client(workspace)


def _warehouse_id_by_name(client: WorkspaceClient, name: str) -> str:
    for warehouse in client.warehouses.list():
        if warehouse.name == name and warehouse.id:
            return warehouse.id
    return ""


def _ensure_warehouse_running(client: WorkspaceClient, warehouse_id: str) -> None:
    warehouse = client.warehouses.get(warehouse_id)
    state = warehouse.state.value if getattr(warehouse, "state", None) else ""
    if state in {"RUNNING", "STARTING"}:
        if state == "STARTING":
            client.warehouses.wait_get_warehouse_running(warehouse_id)
        return
    if hasattr(client.warehouses, "start_and_wait"):
        client.warehouses.start_and_wait(warehouse_id)
        return
    client.warehouses.start(warehouse_id)
    client.warehouses.wait_get_warehouse_running(warehouse_id)
