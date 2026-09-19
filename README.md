# Ecommerce Genie Ontology workflows

Programmatic version of the Northwind Retail **Genie Ontology** demo. The
reference notebooks in [`../genie_ontology`](../genie_ontology) stay untouched.
This repo turns each of those `.py` files into a **workflow task** and runs them
through a local Python script or FastAPI (credentials from `.env`) instead of
importing the folder into Databricks by hand.

Layers depend inward only: **api → workflows → adapter_databricks**, with shared
contracts in **common**. Databricks can be swapped by adding another adapter that
implements the same interfaces.

Each of `api`, `workflows`, and `adapter_databricks` has an `ObjectsFactory`
that looks up named components and caches singleton instances.

```text
src/ecommerce_genie_ontology/
  api/                                 # FastAPI + CliApp
    objects_factory.py                 # ApiObjectsFactory
  workflows/
    objects_factory.py                 # WorkflowsObjectsFactory
    orchestrator.py                    # WorkflowRunner
    provision|create_agents|invoke_agents|cleanup/
      workflow.py
      workspace_facade/{interface,impl}.py
      tasks/
  adapter_databricks/
    objects_factory.py                 # AdapterDatabricksObjectsFactory
    daos/                              # SDK / REST
    facades/                           # SqlFacade, GenieFacade, GovernanceFacade, JobsFacade
  common/
    interfaces/                        # Protocols used for DI
    dtos/ constants/ utils/
```

| Workflow | Job name | Tasks |
|---|---|---|
| **provision** | `ecommerce-genie-ontology-provision` | `00_config` → `01_create_catalog_schema_tables` → `02_create_metric_views` → `04_apply_certification_and_domains` → `05_create_pages` |
| **create_agents** | `ecommerce-genie-ontology-create-agents` | `03_create_genie_agent` |
| **invoke_agents** | `ecommerce-genie-ontology-invoke-agents` | one task per sample question |
| **cleanup** | `ecommerce-genie-ontology-cleanup` | `06_cleanup_delete_all_assets` |

## Prerequisites

- A Databricks workspace with Unity Catalog and a SQL warehouse
- Permission to create a catalog/schema, metric views, and Genie agents
- [`uv`](https://docs.astral.sh/uv/) (this project does not use pip)

## Setup

```bash
cp .env.example .env
```

Fill in at least:

```dotenv
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapiXXXXXXXX
DATABRICKS_WAREHOUSE_ID=xxxxxxxxxxxxxxxx
```

Genie uses the same host/token unless you set `GENIE_HOST` / `GENIE_TOKEN`.

```bash
uv sync
```

## Run locally (uses .env, talks to Databricks APIs)

```bash
uv run genie-ontology run provision
uv run genie-ontology run create_agents
uv run genie-ontology run invoke_agents
```

Or all three in order:

```bash
uv run genie-ontology run all
```

```bash
uv run genie-ontology run invoke_agents --question "What was total revenue last quarter by product category?"
uv run genie-ontology run cleanup --confirm DELETE
```

## HTTP interface

```bash
uv run genie-ontology serve
```

- `GET /health`
- `GET /workflows`
- `POST /workflows/deploy`
- `POST /workflows/{name}/run` with optional `{ "question", "confirm", "as_job" }`

## Register and run Databricks Jobs

```bash
uv run genie-ontology deploy
uv run genie-ontology run provision --as-job
uv run genie-ontology run create_agents --as-job
uv run genie-ontology run invoke_agents --as-job
```

`deploy` uploads this package plus thin wrapper notebooks to
`DATABRICKS_WORKSPACE_PATH` and creates or updates the four jobs.

Pages still have no documented public create API. Provision stores the same
content as `05_pages_content.py` in `<catalog>.<schema>._ontology_pages` and
tries the Discover endpoints; publish in the UI if those APIs are unavailable.
