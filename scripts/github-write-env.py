from __future__ import annotations

import os
from pathlib import Path

KEYS = [
    "DATABRICKS_HOST",
    "DATABRICKS_TOKEN",
    "DATABRICKS_CLIENT_ID",
    "DATABRICKS_CLIENT_SECRET",
    "DATABRICKS_ACCOUNT_ID",
    "DATABRICKS_ACCOUNT_HOST",
    "DATABRICKS_WORKSPACE_NAME",
    "DATABRICKS_AWS_REGION",
    "DATABRICKS_PRICING_TIER",
    "DATABRICKS_WORKSPACE_ADMIN_EMAILS",
    "DATABRICKS_WAREHOUSE_ID",
    "DATABRICKS_WAREHOUSE_NAME",
    "DATABRICKS_CATALOG",
    "DATABRICKS_SCHEMA",
    "DATABRICKS_OLTP_SCHEMA",
    "DATABRICKS_OLTP_CUSTOMERS",
    "DATABRICKS_OLTP_ORDERS_PER_YEAR",
    "DATABRICKS_OLTP_YEARS",
    "GENIE_AGENT_TITLE",
]


def main() -> None:
    lines: list[str] = []
    present: list[str] = []
    for key in KEYS:
        value = os.environ.get(key, "").strip()
        if key == "DATABRICKS_SCHEMA" and value in {"", "retail_demo"}:
            value = "retail_star"
        if key == "DATABRICKS_OLTP_SCHEMA" and not value:
            value = "retail_oltp"
        if not value:
            continue
        lines.append(f"{key}={value}")
        present.append(key)
    Path(".env").write_text("\n".join(lines) + ("\n" if lines else ""))
    print(f"Wrote {len(present)} env keys to .env")


if __name__ == "__main__":
    main()
