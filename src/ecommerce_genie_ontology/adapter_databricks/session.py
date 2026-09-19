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
        workspace = build_workspace_client(settings)
        parent_path = settings.genie_parent_path
        if not parent_path:
            me = workspace.current_user.me()
            parent_path = f"/Workspace/Users/{me.user_name or 'Shared'}"
        return cls(
            context=WorkspaceContext(
                catalog=settings.catalog,
                schema_name=settings.schema,
                warehouse_id=settings.warehouse_id,
                agent_title=settings.agent_title,
                parent_path=parent_path,
                space_id=settings.genie_space_id,
                package_path=settings.package_workspace_path,
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
                catalog=widget("catalog_name", "genie_ontology_demo"),
                schema_name=widget("schema_name", "retail_demo"),
                warehouse_id=warehouse_id,
                agent_title=widget("agent_title", "Retail Analytics Genie"),
                parent_path=widget("parent_path"),
                space_id=widget("space_id"),
                package_path=widget("package_path"),
                question=widget("question"),
                confirm=widget("confirm"),
            ),
            workspace=WorkspaceClient(),
            spark=spark,
        )
