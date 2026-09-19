# Databricks Genie Ontology

Governed customer sales and funds-movement data: Unity Catalog, OLTP, star
schema, and fraud-ready MCP. Portal teams call **LangGraph**, **Google ADK**,
or **AWS Strands** through FastAPI. Provision, load, and tear down with GitHub
Actions — no notebook import.

All data management is currently managed in Databricks and Databricks Genie
and its AI Agents.

## Table of Contents

- [Business Context](#business-context)
  - [Customer behavior](#customer-behavior)
  - [Purpose](#purpose)
  - [Fraud Detection behavior](#fraud-detection-behavior)
  - [Customer Data Capacity Considered](#customer-data-capacity-considered)
  - [OLTP and Star Schema Models](#oltp-and-star-schema-models)
- [Business Data Architecture](#business-data-architecture)
  - [DataWarehouse](#datawarehouse)
  - [The Architecture behind MCP](#the-architecture-behind-mcp)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [GitHub Actions (no local CLI)](#github-actions-no-local-cli)
- [Run locally (uses .env, talks to Databricks APIs)](#run-locally-uses-env-talks-to-databricks-apis)
- [Create the Databricks workspace](#create-the-databricks-workspace)
- [Create the SQL warehouse](#create-the-sql-warehouse)
- [Create the catalog, schema, and star tables](#create-the-catalog-schema-and-star-tables)
- [Drop the catalog](#drop-the-catalog)
- [HTTP interface](#http-interface)
- [MCP tools](#mcp-tools)
  - [MCP tools in Databricks Genie](#mcp-tools-in-databricks-genie)
  - [MCP tools in this codebase](#mcp-tools-in-this-codebase)
- [Fraud agents (inside `ecommerce_genie_ontology`)](#fraud-agents-inside-ecommerce_genie_ontology)
  - [Context management and graph databases](#context-management-and-graph-databases)
- [OLTP and CDC without GitHub Actions](#oltp-and-cdc-without-github-actions)
- [Register and run Databricks Jobs without GitHub Actions](#register-and-run-databricks-jobs-without-github-actions)
- [Running Agentic Fraud Analytics - Start To Finish](#running-agentic-fraud-analytics---start-to-finish)

## Running Agentic Fraud Analytics - Start To Finish

Use **Actions → Run workflow**. Times include Databricks Job start (cold warehouse / cluster). Look at the GitHub run first, then the Databricks account and workspace pages.

Template URLs only — replace the `{placeholders}`:

- Account workspace: `https://accounts.cloud.databricks.com/workspaces/{WORKSPACE_ID}?account_id={ACCOUNT_ID}`
- Workspace home: `https://{WORKSPACE_HOST}`
- Catalog: `https://{WORKSPACE_HOST}/explore/data/{CATALOG}`
- Genie: `https://{WORKSPACE_HOST}/genie`
- Genie MCP (one space): `https://{WORKSPACE_HOST}/api/2.0/mcp/genie/{SPACE_ID}`
- This run: `https://github.com/{OWNER}/{REPO}/actions/runs/{RUN_ID}`

| S. No | GitHub workflow name | Time | What to look at | Comments |
|---|---|---|---|---|
| 1 | 01 - Setup - Step 01 - Create Databricks stack | 20–45 min | GitHub job green; workspace **RUNNING**; SQL warehouse up; catalog empty tables | Account page `https://accounts.cloud.databricks.com/workspaces/{WORKSPACE_ID}?account_id={ACCOUNT_ID}`. Then open `https://{WORKSPACE_HOST}`. Starts the 3-hour destroy timer. Does **not** create Genie spaces. |
| 2 | 01 - Setup - Step 02 - Create all Genie agents | 5–15 min | 11 Genie spaces (Retail Analytics + 10 fraud specialists) | Genie `https://{WORKSPACE_HOST}/genie`. Rerun this if agents fail; do not rerun Step 01. Each space MCP: `https://{WORKSPACE_HOST}/api/2.0/mcp/genie/{SPACE_ID}`. |
| 3 | 01 - Setup - Step 03 - Invoke Retail Analytics Genie | 5–20 min | Sample questions return SQL + a short answer | Confirms Genie MCP on the retail space. Optional question input. |
| 4 | 01 - Setup - Step 04 - Populate next 100000 OLTP rows | 10–40 min | `ingestion_tracker` / `ingestion_log`; row counts on `customer_order` and `customer_transaction` | Catalog `https://{WORKSPACE_HOST}/explore/data/{CATALOG}`. Default 100,000 rows. Repeat until `caught_up`. |
| 5 | 01 - Setup - Step 05 - Populate next N months of dims and facts | 10–30 min | `fact_sales`, `fact_returns`, `fact_inventory`, `fact_transaction` grow for that window | Same catalog. Months 1–12 (default 3). No error if less OLTP remains. |
| 6 | 01 - Setup - Step 06 - Pipeline next 100000 OLTP and next N months star | 20–60 min | Step 4 then step 5 in one run | Use this instead of running 4 and 5 separately. |
| 7 | 02 - Fraud Agent - 01 - Fraud Velocity Agent | 3–10 min | Space **Fraud Velocity Agent** | Genie MCP for velocity bursts and split orders. |
| 8 | 02 - Fraud Agent - 02 - Fraud Address Link Agent | 3–10 min | Space **Fraud Address Link Agent** | Shared-address / duplicate-account hops. |
| 9 | 02 - Fraud Agent - 03 - Fraud Ship-to Bill-to Agent | 3–10 min | Space **Fraud Ship-to Bill-to Agent** | Ship-to ≠ bill-to. |
| 10 | 02 - Fraud Agent - 04 - Fraud Returns Agent | 3–10 min | Space **Fraud Returns Agent** | High / rapid returns. |
| 11 | 02 - Fraud Agent - 05 - Fraud First-Order Agent | 3–10 min | Space **Fraud First-Order Agent** | High-value first orders. |
| 12 | 02 - Fraud Agent - 06 - Fraud Address Surge Agent | 3–10 min | Space **Fraud Address Surge Agent** | New address + expedite / surge. |
| 13 | 02 - Fraud Agent - 07 - Fraud Promo Agent | 3–10 min | Space **Fraud Promo Agent** | Promo and discount abuse. |
| 14 | 02 - Fraud Agent - 08 - Fraud Inventory Agent | 3–10 min | Space **Fraud Inventory Agent** | Orders vs stock mismatch. |
| 15 | 02 - Fraud Agent - 09 - Fraud Cancel Agent | 3–10 min | Space **Fraud Cancel Agent** | Cancel / abort shipment. |
| 16 | 02 - Fraud Agent - 10 - Fraud Geo Agent | 3–10 min | Space **Fraud Geo Agent** | Impossible geography. |
| 17 | 01 - Setup - Step 13 - Destroy Databricks stack | 10–20 min | Workspace gone from account console; cleanup email | Type `DELETE`. Cancels the 3-hour timer. Account list: `https://accounts.cloud.databricks.com/?account_id={ACCOUNT_ID}`. |

Optional lab path (not required for the 100k loop): Step 07 Historical, Step 08 ETL Historical, or Step 11 pipeline; realtime CDC is Step 09 + 10 or Step 12.

## Business Context

### Customer behavior

Customer behavior is how a person buys, pays, ships, and moves money over
time: orders and lines, the addresses they use, channel, status, and — once
funds movement is in scope — wires, cash, book transfers, CDs, brokerage,
demand drafts, and cards. Most of that activity is legitimate. What matters is
the baseline per customer: typical amount, velocity, counterparties, and
whether a new address or a sudden outflow sits outside changing transaction
behaviors.

### Purpose

The purpose of this context is fraud detection: pick out abnormal behaviors
and rare fraud cases in real time, while keeping false alarms down. Fixed
thresholds and rule-based checks miss identity theft and automated attacks,
and they raise false-positives when fraudulent transactions are extremely rare
compared with legitimate ones. Amount, sudden loss of balance, and type of
movement are the high-ranking signals; agents should use them for risk
analysis without dumping ten years of rows into a model.

### Fraud Detection behavior

- Fraud judgment is the **LLM fraud agent**, not PySpark.
- Each specialist has its own **system prompt** (amount vs baseline, sudden drain, transaction type, shared-address network, velocity, changing behavior, rare event, explain the why).
- The agent writes **one outcome per customer**, not one verdict for a list.
- A customer list is only for **paging** the work. Do not ask the model to judge thousands of IDs in one shot.
- Outcome values: `fraud_found` or `not_found`.
- Persist on `analytics_log_customer`: `analytics_outcome` plus `analytics_log_info` (JSON: the why — amount, velocity, address, type).
- Session table `analytics_log`: requesting user, customer count, date range, requested datetime, analytics start/end, status `In Progress` or `Completed`.
- `initiate_fraud_analytics(from_date, to_date)` finds customer IDs **on the server**. It does not dump IDs into the LLM.
- That call creates `analytics_log` and one `analytics_log_customer` row per customer, with dim/fact **counts** for the same window.
- PySpark / SQL only **prepare**: customers in range, counts, optional evidence pack (named case, max 50 rows) as **signals**.
- PySpark does **not** set `fraud_found`. Spark `HAVING` / dollar thresholds are a rule engine — they miss changing behavior and raise false positives.
- MCP never returns 300,000 postings or 15 million orders. Hydrate **one customer** at a time (max 50 evidence rows).
- Agents stay **customer-scoped**. Loop sequential or parallel with a small concurrency cap.
- Databricks **Genie** specialists run in the workspace on the same warehouse.
- Portal agents (**LangGraph**, **Google ADK**, **AWS Strands**) call MCP through FastAPI — not raw tables.
- Same customer and date explain both a velocity flag and a wire-outflow flag.
- Sales fraud and funds-movement fraud share only `dim_customer` and `dim_date`.
- Network hops use `entity_link` (`has_address`, `shared_address`). No graph database for these cases.
- Generate / ETL / next-100k / next-N-months jobs **load data**. They do not classify fraud.
- `close_analytics` sets status `Completed` when the agent says the run is done.

### Customer Data Capacity Considered

Capacity is planned from **18 September 2016** through **18 September 2026**
(ten years ending 18 September 2026). Agents never load this volume; they
hydrate one customer at a time.

| Item | Planned | Notes |
|---|---|---|
| Customers | 100,000 | One person is one customer |
| Accounts per customer | 4 | Checking, certificate of deposit, credit card, brokerage |
| Transactions per customer per year | 30,000 | Sales lines and funds-movement postings in that year |
| Years of history | 10 | End date 18 September 2026; start 18 September 2016 |
| Transactions per customer | 300,000 | 30,000 × 10 years |
| Postings in the warehouse | about 30 billion | 100,000 × 300,000 — design ceiling, not a generate job |

Create / Generate Historical never writes 30 billion rows. That load would run
for days on a large warehouse and blow the 3-hour stack window. Default
generate is **200 customers**, **3 years**, **500 postings per customer per
year** (about 300,000 postings) plus sales orders. Orders are also capped at
20 million rows per run.

### OLTP and Star Schema Models

Sales and funds movement live in OLTP (`customer`, `customer_address`,
`customer_account`, `customer_order`, `customer_order_line`,
`customer_order_shipment`, `customer_transaction`, `ingestion_tracker`,
`ingestion_log`, `analytics_log`, `analytics_log_customer`) plus conformed dimensions
and facts (`dim_account`, `dim_transaction_type`, `dim_counterparty`,
`fact_transaction` with the sales stars). Design volume is the capacity above.
Agents are **customer-scoped**: `initiate_fraud_analytics` keeps IDs on the
server; the agent pages, hydrates **one customer**, and writes the outcome.
Databricks **Genie** agents run in the workspace. **Non-Genie** agents
(LangGraph, Google ADK, AWS Strands) come through the portal via FastAPI and
MCP. The LangGraph and Google ADK packages are conformance clients so the MCP
tools stay honest.

## Business Data Architecture

### DataWarehouse

A data warehouse turns ten years of customer activity into a place agents and
people can ask the same question and get the same answer. Facts hold the
numbers. Each fact row is one event (one sale line, one return, one money
movement). Dimensions hold the who, when, what, and where. That is what makes
amount, velocity, segment, and type comparable across 100,000 customers
without each team rewriting joins on raw OLTP.

### The Architecture behind MCP

The architecture behind MCP is what makes agentic AI fraud detection safe at
this volume. Other teams build **functional agents** — amount vs baseline,
sudden drain, type of movement, shared-address network, changing behavior,
rare events. MCP does not scan 300,000 postings per customer. It answers
those questions for one customer at a time from star facts (baselines, peers,
type mix) or OLTP (the supporting orders and postings). Genie agents and
portal agents call the same warehouse, so a velocity flag and a wire-outflow
flag can be explained from the same customer and date.

Sales fraud and funds-movement fraud share `dim_customer` and `dim_date` only.
Do not hang wire transfers or card dues off `customer_order` / `fact_sales`.
Add a second fact table: one row per **posting** (`customer_transaction` /
`fact_transaction`) with account, type, counterparty, amount, and balance
before/after.

![Customer, transaction types, and banks](docs/images/customer-banks-transactions.png)

![Business data architecture](docs/images/business-data-architecture.png)

| Fraud idea | Functional agent |
|---|---|
| Amount + sudden origin-balance drain | Amount vs baseline — spend far above this customer's recent median; sudden drain |
| Transaction type as a signal | Transaction-type — wire, cash, card, cancel, expedite, promo |
| Graph / network features | Shared-address network — hops on `entity_link` |
| Behavioral vs transactional vs network | Velocity, returns, geo, and first-order specialists |
| Adaptive / changing fraud | Changing-behavior — realtime CDC windows, not a static snapshot |
| Rare events + fewer false positives | Rare-event — peer baselines, not a blanket dollar threshold |
| Feature importance / explainability | Explain the why — amount, velocity, address; not a black box |

**Sales star** — each row is one sales line (one product on one order).

![Sales star schema](docs/images/star-schema-sales.png)

**Returns star** — each row is one return, tied to the same customer, date, and product as sales.

![Returns star schema](docs/images/star-schema-returns.png)

**Inventory star** — each row is how many units of one product a store had on one day (so you can compare sales to stock).

![Inventory star schema](docs/images/star-schema-inventory.png)

**Funds-movement star** — each row is one money movement. Customer and date match sales; account, type, and counterparty are new.

![Funds-movement star schema](docs/images/star-schema-transactions.png)

**MCP contract (customer first)**

- `initiate_fraud_analytics(from_date, to_date)` — server finds IDs; writes `analytics_log` + `analytics_log_customer`
- Agent pages customers; hydrates **one** customer (counts + max 50 evidence rows)
- `record_customer_outcome` — `fraud_found` / `not_found` + JSON why
- `close_analytics` — status `Completed`
- Genie in the workspace; LangGraph / Google ADK / AWS Strands via FastAPI → MCP, not raw tables

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
| **generate_next_oltp** | `ecommerce-genie-ontology-generate-next-oltp` | Append next 100,000 OLTP rows plus `entity_link`; update `ingestion_tracker` / `ingestion_log` |
| **etl_next_months** | `ecommerce-genie-ontology-etl-next-months` | Append `fact_sales` / `fact_returns` / `fact_inventory` / `fact_transaction` for the next 1–12 months |

Default generate is **200 customers**, **3 addresses**, **4 accounts**, **25,000 orders per customer per year**, **500 postings per customer per year**, **3 years** ending this month (about 15 million orders and 300,000 postings). That is per year, not per day. Dims/facts are rebuilt from those OLTP tables so they match. Do not set Generate to 100,000 × 30,000 × 10 — that is the design ceiling, not a GitHub Action.

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

**01 - Setup**

1. **01 - Setup - Step 01 - Create Databricks stack** — workspace, SQL warehouse, catalog, deploy jobs
2. **01 - Setup - Step 02 - Create all Genie agents** — Retail Analytics + 10 fraud specialists
3. **01 - Setup - Step 03 - Invoke Retail Analytics Genie**
4. **01 - Setup - Step 04 - Populate next 100000 OLTP rows**
5. **01 - Setup - Step 05 - Populate next N months of dims and facts**
6. **01 - Setup - Step 06 - Pipeline next 100000 OLTP and next N months star**
7. **01 - Setup - Step 07 - Generate Historical Data**
8. **01 - Setup - Step 08 - Run ETL Star Schema - Historical Data**
9. **01 - Setup - Step 09 - Generate Realtime Orders Data**
10. **01 - Setup - Step 10 - Run ETL Star Schema - CDC Data**
11. **01 - Setup - Step 11 - Pipeline Historical OLTP and Star Schema**
12. **01 - Setup - Step 12 - Pipeline Realtime Orders and CDC Star Schema**
13. **01 - Setup - Step 13 - Destroy Databricks stack**
14. **01 - Setup - Step 14 - Destroy Databricks stack in 3 hours**

**02 - Fraud Agent** (each Action creates that specialist’s Genie space; Databricks hosts Genie MCP at `/api/2.0/mcp/genie/{space_id}`)

1. **02 - Fraud Agent - 01 - Fraud Velocity Agent**
2. **02 - Fraud Agent - 02 - Fraud Address Link Agent**
3. **02 - Fraud Agent - 03 - Fraud Ship-to Bill-to Agent**
4. **02 - Fraud Agent - 04 - Fraud Returns Agent**
5. **02 - Fraud Agent - 05 - Fraud First-Order Agent**
6. **02 - Fraud Agent - 06 - Fraud Address Surge Agent**
7. **02 - Fraud Agent - 07 - Fraud Promo Agent**
8. **02 - Fraud Agent - 08 - Fraud Inventory Agent**
9. **02 - Fraud Agent - 09 - Fraud Cancel Agent**
10. **02 - Fraud Agent - 10 - Fraud Geo Agent**

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

Optional if you skip **Actions → Run workflow**. Same Databricks APIs; you run them from a machine with `.env`.

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

## Create the catalog, schema, and star tables

This is the reference-repo **provision** workflow: `CREATE CATALOG` / `CREATE SCHEMA`, star-schema tables, metric views, tags, and pages. Catalog defaults to `ecommerce_genie_ontology`; schemas default to `retail_oltp` (source) and `retail_star` (dims/facts) (`DATABRICKS_CATALOG` / `DATABRICKS_OLTP_SCHEMA` / `DATABRICKS_SCHEMA` in `.env`).

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
- `POST /api/v1/ontology/oltp/next` body: `NxReq` (`row_count` default 100000)
- `POST /api/v1/ontology/etl/next-months` body: `EmReq` (`months` 1–12, default 3)
- `GET /api/v1/ontology/fraud/cases`
- `POST /api/v1/ontology/fraud/run` body: `FcReq` (`case_id` `01`–`15`)
- `GET /api/v1/ontology/fraud/agents`
- `POST /api/v1/ontology/fraud/analytics/initiate` body: `AnInitReq`
- `POST /api/v1/ontology/fraud/analytics/get` body: `AnIdReq`
- `POST /api/v1/ontology/fraud/analytics/customers` body: `AnListReq`
- `POST /api/v1/ontology/fraud/analytics/customer` body: `AnCustomerReq`
- `POST /api/v1/ontology/fraud/analytics/customer/oltp` body: `AnCustomerReq`
- `POST /api/v1/ontology/fraud/analytics/customer/star` body: `AnCustomerReq`
- `POST /api/v1/ontology/fraud/analytics/outcome` body: `AnOutcomeReq`
- `POST /api/v1/ontology/fraud/analytics/close` body: `AnIdReq`
- `POST /api/v1/ontology/chat` body: `ChReq` (`backend` `langgraph` \| `google_adk` \| `genie`)

Historical generate and ETL should run as Databricks jobs (`as_job: true`, the default) because 15 million orders need Spark. The local process only triggers the job.

## MCP tools

There are two MCP surfaces. Databricks Genie is the managed analytics path
inside the workspace. This repo also runs its own MCP server for load,
ETL, and fraud evidence. Do not put generate or CDC tools on Genie.

### MCP tools in Databricks Genie

Databricks hosts these servers. `create_agents` publishes one Retail Analytics
Genie space plus ten fraud specialist spaces on the same OLTP and star tables.
An MCP client authenticates to the workspace and calls Genie; Genie writes the
SQL.

| Server | URL | When to use |
|---|---|---|
| Genie One | `{DATABRICKS_HOST}/api/2.0/mcp/genie` | Natural-language questions across the workspace |
| Genie Agent | `{DATABRICKS_HOST}/api/2.0/mcp/genie/{GENIE_SPACE_ID}` | Questions scoped to one Genie space (retail analytics or one fraud specialist) |
| Databricks SQL | `{DATABRICKS_HOST}/api/2.0/mcp/sql` | A query you already wrote (not fraud generate / CDC) |

Genie One / Genie Agent tools (the client calls `genie_ask`; the rest are for
the in-flight turn):

| Tool | What it does |
|---|---|
| `genie_ask` | Ask a natural-language data question. Returns `conversation_id`, `response_id`, and `status`. Pass `conversation_id` to continue. |
| `genie_poll_response` | Read progress, the final answer, and links back to Databricks sources. |
| `genie_get_query_result` | Fetch the SQL result Genie ran (schema and rows). |
| `genie_cancel_response` | Cancel an in-flight Genie turn. |
| `view_ask` | Same ask, opens the interactive View (MCP Apps clients). |

Genie spaces created here: **Retail Analytics Genie** (certified metric views)
and the ten fraud specialists (`velocity`, `address_link`, `ship_bill`,
`returns`, `first_order`, `address_surge`, `promo`, `inventory`, `cancel`,
`geo`). Those specialists answer questions; they do not run Spark jobs.

### MCP tools in this codebase

The non-Databricks MCP is `ecommerce-oltp-mcp` in
`src/ecommerce_genie_ontology/mcp/`. LangGraph, Google ADK, Cursor, and Claude
Desktop call it over stdio. Portal chat reaches the same functions through
FastAPI facades. Every evidence tool returns at most 50 rows.

```bash
uv sync --extra mcp
uv run --extra mcp genie-ontology mcp
```

Cursor / Claude Desktop:

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

**Evidence and specialists**

| Tool | What it does |
|---|---|
| `list_fraud_cases` | The 15 named fraud cases (evidence packs, not full tables). |
| `list_fraud_agents` | The 10 specialists and which cases each owns. |
| `run_fraud_case` | Run one case (`01`–`15`). At most 50 evidence rows. |
| `run_fraud_agent_cases` | Run every pack owned by one specialist. |
| `initiate_fraud_analytics` | Date range in; server finds IDs; writes `analytics_log` + per-customer counts. |
| `get_analytics` | Session header and pending customer count. |
| `list_analytics_customers` | Page of customers (max 50) with counts and outcome. |
| `get_customer_analytics` | One customer: counts + at most 50 evidence rows. |
| `get_customer_oltp` | At most 25 orders and 25 postings for one customer. |
| `get_customer_star` | At most 25 sales facts and 25 posting facts for one customer. |
| `record_customer_outcome` | `fraud_found` or `not_found` plus JSON why. |
| `close_analytics` | Status `Completed`. |
| `query_dataset` | One `SELECT` or `WITH` against OLTP or star. Forced `LIMIT 50`. |

**Load and ETL (operators; not on Genie)**

| Tool | What it does |
|---|---|
| `generate_historical_oltp` | Write customer, address, order, line, shipment, and `entity_link`. Default: Databricks Job. |
| `generate_realtime_orders` | Append 100–10,000 new orders. Window: `latest` / `last_2` / `last_3` / `all`. |
| `etl_star_historical` | Overwrite star dims and facts from OLTP. |
| `etl_star_cdc` | Apply Delta change feed from `customer_order` into `fact_sales`. |
| `generate_next_oltp` | Next 100,000 OLTP rows. Writes `ingestion_tracker` and `ingestion_log`. |
| `etl_next_months` | Next N months of dims/facts (1–12). No error if less OLTP remains. |

Customer-first contract is on this server, not Genie: open a session, page
customers, hydrate one customer, write the outcome, then close.

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

## OLTP and CDC without GitHub Actions

Same jobs as **01 - Setup** Steps 07–10. Use this only if you are not running those Actions.

```bash
uv run genie-ontology deploy
uv run genie-ontology run generate_historical --as-job --customers 200 --orders-per-year 25000 --years 3
uv run genie-ontology run etl_historical --as-job
uv run genie-ontology run generate_realtime --as-job --count 1000 --year-window latest
uv run genie-ontology run etl_cdc --as-job
```

## Register and run Databricks Jobs without GitHub Actions

Same as **01 - Setup** Steps 01–03. Use this only if you are not running those Actions.

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
