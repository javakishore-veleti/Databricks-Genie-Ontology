from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from ecommerce_genie_ontology.common.dtos.workspace import WorkspaceContext
from ecommerce_genie_ontology.common.utils.env import env_emails, load_env, optional_env, optional_int


@dataclass(frozen=True)
class Settings:
    host: str
    token: str
    warehouse_id: str
    warehouse_name: str
    workspace_name: str
    catalog: str
    schema: str
    oltp_schema: str
    customer_count: int
    orders_per_year: int
    year_count: int
    admin_emails: tuple[str, ...]
    workspace_path: str
    agent_title: str
    client_id: str
    client_secret: str
    genie_host: str
    genie_token: str
    genie_space_id: str
    genie_parent_path: str
    env_file: Path | None

    @property
    def fq_schema(self) -> str:
        return f"{self.catalog}.{self.schema}"

    @property
    def fq_oltp(self) -> str:
        return f"{self.catalog}.{self.oltp_schema}"

    @property
    def package_workspace_path(self) -> str:
        return f"{self.workspace_path.rstrip('/')}/src"

    @property
    def notebooks_workspace_path(self) -> str:
        return f"{self.workspace_path.rstrip('/')}/notebooks"

    @classmethod
    def from_workspace_context(cls, ctx: WorkspaceContext) -> Settings:
        """Job-runtime settings from widgets. No PAT / OAuth — the cluster identity is enough."""
        package = (ctx.package_path or "").rstrip("/")
        workspace_path = (
            package[: -len("/src")]
            if package.endswith("/src")
            else package or "/Workspace/Shared/ecommerce-genie-ontology"
        )
        return cls(
            host="",
            token="",
            warehouse_id=ctx.warehouse_id,
            warehouse_name="",
            workspace_name="",
            catalog=ctx.catalog,
            schema=_star_schema(ctx.schema_name),
            oltp_schema=ctx.oltp_schema,
            customer_count=ctx.customer_count,
            orders_per_year=ctx.orders_per_year,
            year_count=ctx.year_count,
            admin_emails=ctx.admin_emails,
            workspace_path=workspace_path,
            agent_title=ctx.agent_title,
            client_id="",
            client_secret="",
            genie_host="",
            genie_token="",
            genie_space_id=ctx.space_id,
            genie_parent_path=ctx.parent_path,
            env_file=None,
        )

    @classmethod
    def load(cls) -> Settings:
        env_file = load_env()
        host = optional_env("DATABRICKS_HOST").rstrip("/")
        token = optional_env("DATABRICKS_TOKEN")
        client_id = optional_env("DATABRICKS_CLIENT_ID")
        client_secret = optional_env("DATABRICKS_CLIENT_SECRET")
        on_cluster = bool(os.getenv("DATABRICKS_RUNTIME_VERSION"))
        if not on_cluster and not token and not (client_id and client_secret):
            raise SystemExit(
                "Set DATABRICKS_TOKEN, or DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET, in .env."
            )
        return cls(
            host=host,
            token=token,
            warehouse_id=optional_env("DATABRICKS_WAREHOUSE_ID"),
            warehouse_name=optional_env("DATABRICKS_WAREHOUSE_NAME", "ecommerce-genie-ontology"),
            workspace_name=optional_env("DATABRICKS_WORKSPACE_NAME", "ecommerce-genie-ontology"),
            catalog=optional_env("DATABRICKS_CATALOG", "ecommerce_genie_ontology"),
            schema=_star_schema(optional_env("DATABRICKS_SCHEMA", "retail_star")),
            oltp_schema=optional_env("DATABRICKS_OLTP_SCHEMA", "retail_oltp"),
            customer_count=optional_int("DATABRICKS_OLTP_CUSTOMERS", 200),
            orders_per_year=optional_int("DATABRICKS_OLTP_ORDERS_PER_YEAR", 25000),
            year_count=optional_int("DATABRICKS_OLTP_YEARS", 3),
            admin_emails=env_emails("DATABRICKS_WORKSPACE_ADMIN_EMAILS"),
            workspace_path=optional_env(
                "DATABRICKS_WORKSPACE_PATH", "/Workspace/Shared/ecommerce-genie-ontology"
            ),
            agent_title=optional_env("GENIE_AGENT_TITLE", "Retail Analytics Genie"),
            client_id=client_id,
            client_secret=client_secret,
            genie_host=optional_env("GENIE_HOST", host).rstrip("/"),
            genie_token=optional_env("GENIE_TOKEN", token),
            genie_space_id=optional_env("GENIE_SPACE_ID"),
            genie_parent_path=optional_env("GENIE_PARENT_PATH"),
            env_file=env_file,
        )


def _star_schema(name: str) -> str:
    return "retail_star" if name in {"", "retail_demo"} else name
