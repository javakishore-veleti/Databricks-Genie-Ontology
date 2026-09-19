from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecommerce_genie_ontology.common.utils.env import load_env, optional_env, required_env


@dataclass(frozen=True)
class Settings:
    host: str
    token: str
    warehouse_id: str
    catalog: str
    schema: str
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
    def package_workspace_path(self) -> str:
        return f"{self.workspace_path.rstrip('/')}/src"

    @property
    def notebooks_workspace_path(self) -> str:
        return f"{self.workspace_path.rstrip('/')}/notebooks"

    @classmethod
    def load(cls) -> Settings:
        env_file = load_env()
        host = required_env("DATABRICKS_HOST").rstrip("/")
        token = optional_env("DATABRICKS_TOKEN")
        client_id = optional_env("DATABRICKS_CLIENT_ID")
        client_secret = optional_env("DATABRICKS_CLIENT_SECRET")
        if not token and not (client_id and client_secret):
            raise SystemExit(
                "Set DATABRICKS_TOKEN, or DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET, in .env."
            )
        return cls(
            host=host,
            token=token,
            warehouse_id=required_env("DATABRICKS_WAREHOUSE_ID"),
            catalog=optional_env("DATABRICKS_CATALOG", "genie_ontology_demo"),
            schema=optional_env("DATABRICKS_SCHEMA", "retail_demo"),
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
