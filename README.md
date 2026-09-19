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
```

`DATABRICKS_WAREHOUSE_ID` is optional. Catalog provision looks up warehouse `ecommerce-genie-ontology` by name. Genie uses the same host/token unless you set `GENIE_HOST` / `GENIE_TOKEN`.

```bash
uv sync
```

## GitHub Actions (no local CLI)

Use **Actions → Run workflow**. Create starts a 3-hour timer; a later Create cancels the previous timer. Destroy can be run by hand any time before that.

1. **Create Databricks stack** — workspace, SQL warehouse, catalog `ecommerce_genie_ontology`
2. **Destroy Databricks stack in 3 hours** — queued automatically after Create
3. **Destroy Databricks stack** — manual wipe (cancels the 3-hour timer)

Destroy drops the catalog, deletes the warehouse and workspace, then emails `CLEANUP_NOTIFY_EMAIL` that this codebase’s Databricks demo stack is gone and should not keep billing.

Repo **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
|---|---|
| `DATABRICKS_ACCOUNT_ID` | Account API |
| `DATABRICKS_CLIENT_ID` | OAuth M2M service principal |
| `DATABRICKS_CLIENT_SECRET` | OAuth M2M secret |
| `DATABRICKS_WORKSPACE_ADMIN_EMAILS` | Users who can open the workspace UI |
| `CLEANUP_NOTIFY_EMAIL` | Inbox for the “stack cleaned” email |
| `SMTP_HOST` | SMTP server (for example `smtp.gmail.com`) |
| `SMTP_PORT` | `587` (STARTTLS) or `465` (SSL) |
| `SMTP_USERNAME` | SMTP login |
| `SMTP_PASSWORD` | SMTP password or app password |
| `SMTP_FROM` | Optional From address; defaults to `SMTP_USERNAME` |

Optional: `DATABRICKS_ACCOUNT_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_HOST`, `DATABRICKS_WORKSPACE_NAME`, `DATABRICKS_AWS_REGION`, `DATABRICKS_WAREHOUSE_NAME`, `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`.

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
uv run genie-ontology run truncate --confirm DELETE
```

## Create the Databricks workspace

Account-admin credentials in `.env`: `DATABRICKS_ACCOUNT_ID` plus `DATABRICKS_TOKEN` or OAuth client id/secret.

```bash
npm run ecommerce:workspace:databricks-setup
```

Each `ecommerce:*:databricks-setup` command restarts local FastAPI so it always loads current code, then POSTs, then stops the server. No need to start `ecommerce:api:run` first or Ctrl+C afterward.

That calls `POST /api/v1/ontology/provision-workspace` and creates or reuses the serverless workspace named `ecommerce-genie-ontology`. Set `DATABRICKS_WORKSPACE_ADMIN_EMAILS` in `.env` (comma-separated) so those account users are assigned workspace ADMIN and can open the UI. The OAuth service principal is also assigned ADMIN; without a human email, only the SP can call APIs and you will see “You do not have permission to access this page”.

## Create the SQL warehouse

After the workspace is `RUNNING`, create a serverless SQL warehouse (PRO + serverless compute, 2X-Small) named `ecommerce-genie-ontology`:

```bash
npm run ecommerce:warehouse:databricks-setup
```

That restarts FastAPI, POSTs `WhReq` to `/api/v1/ontology/provision-warehouse`, then stops the server. The warehouse is found later by name; copying `warehouse_id` into `.env` is optional.

## Create the catalog, schema, and demo tables

This is the reference-repo **provision** workflow: `CREATE CATALOG` / `CREATE SCHEMA`, star-schema tables, metric views, tags, and pages. Catalog name defaults to `ecommerce_genie_ontology` (`DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA` in `.env`).

```bash
npm run ecommerce:catalog:databricks-setup
```

That restarts FastAPI, POSTs `WfReq` `{ "workflow": "provision" }` to `/api/v1/ontology/workflows/run`, then stops the server.

## Drop the catalog

Runs as the service principal (so you do not need MANAGE in the SQL Editor). Drops `DATABRICKS_CATALOG` with `CASCADE` and trashes the Genie agent. Workspace, warehouse, and metastore stay.

```bash
npm run ecommerce:catalog:databricks-truncate
```

Then recreate with `npm run ecommerce:catalog:databricks-setup`.

## HTTP interface

```bash
npm run ecommerce:api:run
```

- `GET /health`
- `GET /api/v1/ontology/workflows`
- `POST /api/v1/ontology/workflows/run` body: `WfReq`
- `POST /api/v1/ontology/workflows/deploy` body: `DpReq`
- `POST /api/v1/ontology/provision-workspace` body: `PwReq`
- `POST /api/v1/ontology/provision-warehouse` body: `WhReq`
- `POST /api/v1/ontology/truncate` body: `TcReq` (`confirm` must be `DELETE`)
- `POST /api/v1/ontology/destroy` body: `DyReq` (`confirm` must be `DELETE`; drops catalog, warehouse, and workspace)


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
