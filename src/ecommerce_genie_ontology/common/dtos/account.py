from __future__ import annotations

from dataclasses import dataclass

from ecommerce_genie_ontology.common.utils.env import env_emails, load_env, optional_env, required_env


@dataclass(frozen=True)
class AccountSettings:
    account_id: str
    account_host: str
    token: str
    client_id: str
    client_secret: str
    workspace_name: str
    aws_region: str
    pricing_tier: str
    admin_emails: tuple[str, ...]

    @classmethod
    def load(cls) -> AccountSettings:
        load_env()
        token = optional_env("DATABRICKS_TOKEN")
        client_id = optional_env("DATABRICKS_CLIENT_ID")
        client_secret = optional_env("DATABRICKS_CLIENT_SECRET")
        if not token and not (client_id and client_secret):
            raise SystemExit(
                "Set DATABRICKS_TOKEN, or DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET, "
                "for the Databricks Account API."
            )
        return cls(
            account_id=required_env("DATABRICKS_ACCOUNT_ID"),
            account_host=optional_env(
                "DATABRICKS_ACCOUNT_HOST", "https://accounts.cloud.databricks.com"
            ).rstrip("/"),
            token=token,
            client_id=client_id,
            client_secret=client_secret,
            workspace_name=optional_env("DATABRICKS_WORKSPACE_NAME", "ecommerce-genie-ontology"),
            aws_region=optional_env("DATABRICKS_AWS_REGION", "us-east-1"),
            pricing_tier=optional_env("DATABRICKS_PRICING_TIER", "PREMIUM"),
            admin_emails=env_emails("DATABRICKS_WORKSPACE_ADMIN_EMAILS"),
        )


@dataclass
class AccountWorkspace:
    workspace_id: int | None
    workspace_name: str
    workspace_status: str
    workspace_status_message: str
    deployment_name: str
    host: str
    aws_region: str
    created: bool = False
