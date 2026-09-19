# Ecommerce Genie Ontology workflows

Programmatic version of the Northwind Retail **Genie Ontology** demo. The
reference notebooks in [`../genie_ontology`](../genie_ontology) stay untouched.
This repo turns each of those `.py` files into a **workflow task** and runs them
through a local Python script or FastAPI (credentials from `.env`) instead of
importing the folder into Databricks by hand.

Layers depend inward only: **api → workflows → adapter_databricks**, with shared
contracts in **common**. Databricks can be swapped by adding another adapter that
implements the same interfaces.

## Business Context

Customer behavior is how a person buys, pays, ships, and moves money over
time: orders and lines, the addresses they use, channel, status, and — once
funds movement is in scope — wires, cash, book transfers, CDs, brokerage,
demand drafts, and cards. Most of that activity is legitimate. What matters is
the baseline per customer: typical amount, velocity, counterparties, and
whether a new address or a sudden outflow sits outside changing transaction
behaviors.

The purpose of this context is fraud detection: pick out abnormal behaviors
and rare fraud cases in real time, while keeping false alarms down. Fixed
thresholds and rule-based checks miss identity theft and automated attacks,
and they raise false-positives when fraudulent transactions are extremely rare
compared with legitimate ones. Amount, sudden loss of balance, and type of
movement are the high-ranking signals; agents should use them for risk
analysis without dumping ten years of rows into a model.

Sales and funds movement live in OLTP (`customer`, `customer_address`,
`customer_order`, `customer_order_line`, `customer_order_shipment`) plus
conformed dimensions and facts. Design volume is **100,000 customers**,
**30,000 transactions per customer per year**, and **10 years** of history
(**300,000 transactions per customer**). Agents are **customer-scoped**: MCP
returns only `customer_id` values for a date range, then each agent loops
(parallel or sequential) and hydrates **one customer** from star schema and/or
OLTP. Databricks **Genie** agents run in the workspace. **Non-Genie** agents
(LangGraph, Google ADK, AWS Strands) come through the portal via FastAPI and
MCP. The LangGraph and Google ADK packages are conformance clients so the MCP
tools stay honest.

## Business Data Architecture

Sales fraud and funds-movement fraud share `dim_customer` and `dim_date` only.
Do not hang wire transfers or card dues off `customer_order` / `fact_sales`.
Add a second grain: **posting** (`customer_transaction` / `fact_transaction`)
with account, type, counterparty, amount, and balance before/after.

![Business data architecture](docs/images/business-data-architecture.png)

**MCP contract (customer first)**

1. `list_customer_ids(from_date, to_date)` — IDs only, paged
2. Agent loop (parallel with a small concurrency cap, or sequential)
3. `get_customer_oltp` and/or `get_customer_star` for that `customer_id` and the same window (max 50 rows; never 300,000 postings)

Databricks Genie agents query Unity Catalog in the workspace. Portal users reach
non-Genie agents (LangGraph, Google ADK, AWS Strands) through FastAPI; those
agents call MCP, not raw tables.

**Dims to add (few, conformed)**

| Dim | Why |
|---|---|
| `dim_transaction_type` | Type signal for funds-movement agents |
| `dim_account` | Same vs other account; product (checking / CD / card / brokerage) |
| `dim_counterparty` | Other bank, other person, brokerage |
| `dim_date` | Already present |

Do not add `dim_wire`, `dim_cash`, or `dim_credit_card`. Those are rows in
`dim_transaction_type`.

**`dim_transaction_type`**

| type_code | class | direction | same_bank | same_account |
|---|---|---|---|---|
| wire_transfer | transfer | out | no | no |
| cash_deposit | cash | in | yes | yes |
| cash_withdrawal | cash | out | yes | yes |
| bank_transfer_other | transfer | out | no | no |
| bank_transfer_same_acct | transfer | book | yes | yes |
| intra_bank_same_accts | transfer | book | yes | no |
| cd_withdraw | term | out | yes | no |
| cd_deposit | term | in | yes | no |
| brokerage_in | securities | in | no | no |
| brokerage_out | securities | out | no | no |
| demand_draft_request | instrument | out | yes | no |
| demand_draft_issue | instrument | out | yes | no |
| card_purchase | card | out | no | no |
| card_payment | card | in | yes | no |
| card_due | card | obligation | yes | no |

OLTP posting row: `transaction_id`, `customer_id`, `account_id`,
`counterparty_id`, `type_code`, `txn_ts`, `amount`, `balance_before`,
`balance_after`, `status`. Partition facts by date and cluster on
`customer_id` / `account_id`. Refresh `fact_transaction` incrementally; do not
overwrite 10 years on every run.

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
| **generate_historical** | `ecommerce-genie-ontology-generate-historical` | PySpark OLTP history (`customer`, `customer_address`, `customer_order`, `customer_order_line`, `customer_order_shipment`, `entity_link`) |
| **generate_realtime** | `ecommerce-genie-ontology-generate-realtime` | Append 100–10,000 new OLTP orders for CDC |
| **etl_historical** | `ecommerce-genie-ontology-etl-historical` | Overwrite star-schema dims/facts from OLTP |
| **etl_cdc** | `ecommerce-genie-ontology-etl-cdc` | Apply Delta change feed into `fact_sales` |

Default volume is **200 customers**, **3 addresses each**, **25,000 orders per customer per year**, **3 years** ending this month (about 15 million orders). That is per year, not per day. Dims/facts are rebuilt from those OLTP tables so they match.

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

Use **Actions → Run workflow**. Create starts a 3-hour timer; a later Create cancels the previous timer. Destroy can be run by hand any time before that. Pipeline workflows are also **manual** (`workflow_dispatch` only).

1. **Create Databricks stack** — workspace, SQL warehouse, catalog `ecommerce_genie_ontology`
2. **Generate Historical Data** — OLTP tables for N customers / years
3. **Run ETL Star Schema - Historical Data** — overwrite dims/facts from OLTP
4. **Generate Realtime Orders Data** — 100 / 250 / 500 / 1,000 / 2,500 / 5,000 / 10,000 orders; window `latest` / `last_2` / `last_3` / `all`
5. **Run ETL Star Schema - CDC Data** — Delta CDF into `fact_sales`
6. **Pipeline Historical OLTP and Star Schema** — steps 2 then 3
7. **Pipeline Realtime Orders and CDC Star Schema** — steps 4 then 5
8. **Destroy Databricks stack in 3 hours** — queued automatically after Create
9. **Destroy Databricks stack** — manual wipe (cancels the 3-hour timer)

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

Optional: `DATABRICKS_ACCOUNT_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_HOST`, `DATABRICKS_WORKSPACE_NAME`, `DATABRICKS_AWS_REGION`, `DATABRICKS_WAREHOUSE_NAME`, `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`, `DATABRICKS_OLTP_SCHEMA`.

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
- `POST /api/v1/ontology/oltp/historical` body: `OhReq`
- `POST /api/v1/ontology/oltp/realtime` body: `OdReq` (`count` 100–10000, `year_window` `latest` \| `last_2` \| `last_3` \| `all`)
- `POST /api/v1/ontology/etl/historical` body: `EhReq`
- `POST /api/v1/ontology/etl/cdc` body: `EcReq`
- `GET /api/v1/ontology/fraud/cases`
- `POST /api/v1/ontology/fraud/run` body: `FcReq` (`case_id` `01`–`15`)
- `GET /api/v1/ontology/fraud/agents`
- `POST /api/v1/ontology/chat` body: `ChReq` (`backend` `langgraph` \| `google_adk` \| `genie`)

Historical generate and ETL should run as Databricks jobs (`as_job: true`, the default) because 15 million orders need Spark. The local process only triggers the job.

## MCP: Genie vs this repo

Databricks already hosts MCP for analytics. Point an agent at the workspace Genie space for NL questions over certified dims, facts, and metric views:

- `{DATABRICKS_HOST}/api/2.0/mcp/genie/{GENIE_SPACE_ID}`
- `{DATABRICKS_HOST}/api/2.0/mcp/sql`

Do **not** put generate/CDC tools inside Genie. This repo’s operational MCP is separate: it triggers OLTP generation, CDC ETL, and 15 fraud **evidence packs** (at most 50 SQL rows). It never loads fact tables into the model.

```bash
uv sync --extra mcp
uv run --extra mcp genie-ontology mcp
```

Cursor / Claude Desktop stdio config:

```json
{
  "mcpServers": {
    "ecommerce-oltp": {
      "command": "uv",
      "args": ["run", "--extra", "mcp", "genie-ontology", "mcp"],
      "cwd": "/path/to/Databricks-Genie-Ontology"
    }
  }
}
```

Tools: `list_fraud_cases`, `list_fraud_agents`, `run_fraud_case`, `run_fraud_agent_cases`, `generate_historical_oltp`, `generate_realtime_orders`, `etl_star_historical`, `etl_star_cdc`, `query_dataset`.

## Fraud agents (inside `ecommerce_genie_ontology`)

FastAPI never imports LangGraph or Google ADK. It calls a facade; the facade invokes that stack.

```text
src/ecommerce_genie_ontology/
  agents_langgraph/     # LgFacade → LangGraph StateGraph → MCP tools
    facade.py graph.py
  agents_google_adk/    # GaFacade → ADK root + 10 sub-agents → MCP tools
    facade.py agent.py runtime.py
```

```bash
uv sync --extra agents
# or: uv sync --extra langgraph --extra google-adk --extra mcp
```

`POST /api/v1/ontology/chat` with `"backend": "langgraph"` or `"google_adk"` or `"genie"`. The 10 Databricks Genie specialists are created by `create_agents` on the same OLTP + dims/facts.

Run all 15 fraud packs without an LLM:

```bash
uv run genie-ontology fraud-agent
uv run genie-ontology fraud-agent --cases 01,02,06
uv run genie-ontology run fraud --case-id 02
```

### Context management and graph databases

The agent never sees 15 million orders. Spark/SQL stay in Databricks. Each fraud case is a named query plus a small evidence pack. `retail_oltp.entity_link` stores 1–2 hop relationships (`has_address`, `shared_address`) so you do not need Neo4j for these 15 cases. Add a graph store later only if you need unbounded multi-hop traversal or a live investigation UI.

## OLTP and CDC locally (uses .env, talks to Databricks Jobs)

```bash
uv run genie-ontology deploy
uv run genie-ontology run generate_historical --as-job --customers 200 --orders-per-year 25000 --years 3
uv run genie-ontology run etl_historical --as-job
uv run genie-ontology run generate_realtime --as-job --count 1000 --year-window latest
uv run genie-ontology run etl_cdc --as-job
```


## Register and run Databricks Jobs

```bash
uv run genie-ontology deploy
uv run genie-ontology run provision --as-job
uv run genie-ontology run create_agents --as-job
uv run genie-ontology run invoke_agents --as-job
```

`deploy` uploads this package plus thin wrapper notebooks to
`DATABRICKS_WORKSPACE_PATH` and creates or updates the jobs (Genie provision plus OLTP/CDC Spark jobs).

Pages still have no documented public create API. Provision stores the same
content as `05_pages_content.py` in `<catalog>.<schema>._ontology_pages` and
tries the Discover endpoints; publish in the UI if those APIs are unavailable.
