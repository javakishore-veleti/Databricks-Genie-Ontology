"""Northwind Retail / Genie Ontology definitions from the reference repo."""

from __future__ import annotations

DOMAIN_NAMES = ["Sales", "Customer", "Supply Chain", "Finance"]

DISCOVER_DOMAINS = [
    {
        "tag_key": "Sales",
        "subtitle": "Orders, revenue, and certified sales performance.",
        "description": (
            "Northwind Retail sales: fact_sales, dim_product, dim_store, and the "
            "certified metric view mv_sales_performance. Assets tagged Sales appear here."
        ),
        "icon": {"name": "PRESENTATION_CHART", "color": "#1B3139"},
    },
    {
        "tag_key": "Customer",
        "subtitle": "Customers, segments, and return rate.",
        "description": (
            "Customer dimension, returns, and mv_customer_returns. Use the Customer Return "
            "Rate Page for the cross-fact refund ratio."
        ),
        "icon": {"name": "USERS_THREE", "color": "#FF3621"},
    },
    {
        "tag_key": "Supply Chain",
        "subtitle": "Stores, inventory health, and fulfillment.",
        "description": (
            "Store and inventory assets tagged Supply Chain, including fact_inventory "
            "and certified mv_inventory_health."
        ),
        "icon": {"name": "PACKAGE", "color": "#00A972"},
    },
    {
        "tag_key": "Finance",
        "subtitle": "Funds movement, counterparties, and total revenue.",
        "description": (
            "Finance-tagged facts and dimensions: fact_transaction, dim_counterparty, "
            "dim_account, and the Total Revenue Page."
        ),
        "icon": {"name": "BANK", "color": "#3BA3F7"},
    },
]

ASSET_DOMAINS: dict[str, list[str]] = {
    "dim_product": ["Sales"],
    "dim_store": ["Sales", "Supply Chain"],
    "dim_customer": ["Customer"],
    "dim_date": [],
    "dim_account": ["Finance", "Customer"],
    "dim_transaction_type": ["Finance"],
    "dim_counterparty": ["Finance"],
    "dim_region": ["Sales", "Customer"],
    "dim_address": ["Customer"],
    "fact_sales": ["Sales", "Finance"],
    "fact_returns": ["Customer"],
    "fact_inventory": ["Supply Chain"],
    "fact_transaction": ["Finance"],
    "fact_order_event": ["Sales", "Customer"],
    "mv_sales_performance": ["Sales", "Finance"],
    "mv_customer_returns": ["Customer"],
    "mv_inventory_health": ["Supply Chain"],
    "mv_order_event": ["Sales", "Customer"],
}

METRIC_VIEWS = {
    "mv_sales_performance",
    "mv_customer_returns",
    "mv_inventory_health",
    "mv_order_event",
}

AGENT_TITLE = "Retail Analytics Genie"

AGENT_DESCRIPTION = """Answers natural-language questions about Northwind Retail sales performance,
customer returns, and inventory health using certified metric views. Covers
revenue, units sold, orders, average order value, returns and return volume,
and stock-on-hand, sliced by date, product category/brand, customer
segment/region, and store region/channel."""

AGENT_INSTRUCTIONS = """You are a retail analytics assistant for Northwind Retail.

- For order timing, ship-to vs bill-to, and impossible geo, use
  mv_order_event / fact_order_event (hour-level order_ts, shipping_region_key).
- fact_sales and fact_inventory are STALE merchandising snapshots. Do not use
  them for fraud or same-hour geography. Prefer mv_order_event.
- "Revenue" or "sales" for merchandising still means total_revenue in
  mv_sales_performance (stale line-grain).
- "Return rate" is not a stored measure - compute it as
  mv_customer_returns.return_amount / mv_sales_performance.total_revenue for the
  same time period and dimension slice, and say so when you do.
- All monetary figures are in USD.
- When a question is ambiguous about time range, default to the trailing 12
  months and state the range you used."""

SAMPLE_QUESTIONS = [
    "What was total revenue last quarter by product category?",
    "What's our customer return rate this year vs last year?",
    "Which customers have orders in two shipping regions within one hour?",
    "Which region has the highest revenue but also high returns?",
    "What is the average order value by customer segment?",
    "Which products have the lowest average stock on hand?",
]

PAGES = [
    {
        "name": "Total Revenue",
        "domain": "Finance",
        "synonyms": ["revenue", "sales", "gross sales", "GMV"],
        "description": (
            "Sum of gross revenue (quantity x unit price) across all order lines, with no "
            "adjustment for returns or discounts."
        ),
        "body": """Definition
Total Revenue is the sum of gross revenue (quantity x unit price) across all
order lines in fact_sales, with no adjustment for returns or discounts.

Formula: SUM(fact_sales.revenue)

Business use
Use the total_revenue measure in mv_sales_performance rather than querying
fact_sales directly - it carries the certified definition and pre-built
dimension joins (date, product, customer, store).

See also: Customer Return Rate for how returns relate to this figure.""",
        "related_assets": [
            "mv_sales_performance",
            "fact_sales",
            "Retail Analytics Genie",
        ],
    },
    {
        "name": "Customer Return Rate",
        "domain": "Customer",
        "synonyms": ["return rate", "returns ratio"],
        "description": (
            "Share of revenue that is later refunded: total return amount divided by total "
            "revenue for the same period and dimension slice."
        ),
        "body": """Definition
Customer Return Rate measures what share of revenue is later refunded.

Formula: SUM(fact_returns.return_amount) / SUM(fact_sales.revenue)
for the same time period and dimension slice.

This is a cross-fact metric, so it is not a single stored measure - combine
the return_amount measure from mv_customer_returns with the total_revenue
measure from mv_sales_performance for the period you're comparing.

Business use
Use this Page as the authoritative formula whenever someone asks about return
rate - Genie cannot derive the cross-fact ratio on its own from either metric
view alone.

See also: Total Revenue.""",
        "related_assets": [
            "mv_customer_returns",
            "mv_sales_performance",
            "fact_returns",
            "Retail Analytics Genie",
        ],
    },
    {
        "name": "Retail Analytics Genie Agent",
        "domain": "Sales",
        "synonyms": ["retail genie", "sales genie", "retail analytics assistant"],
        "description": (
            "Onboarding page for the Retail Analytics Genie Agent - what it answers and "
            "which certified metric views it draws from."
        ),
        "body": """Definition
Retail Analytics Genie is the Genie Agent for Northwind Retail sales,
returns, and inventory questions. It answers from three certified metric
views: mv_sales_performance, mv_customer_returns, and mv_inventory_health.

Business use
Ask things like:
- "What was total revenue last quarter by product category?"
- "What's our customer return rate this year vs last year?"
- "Which region has the highest revenue but also high returns?"
- "Which products have the lowest average stock on hand?"

For metric definitions, see Total Revenue, Customer Return Rate, and Impossible Geo.
fact_sales and fact_inventory are STALE merchandising snapshots.""",
        "related_assets": [
            "Retail Analytics Genie",
            "mv_sales_performance",
            "mv_customer_returns",
            "mv_inventory_health",
            "mv_order_event",
        ],
    },
    {
        "name": "Impossible Geo",
        "domain": "Customer",
        "synonyms": ["impossible geo", "two regions one hour", "case 15"],
        "description": (
            "Same customer with two fact_order_event rows whose shipping regions differ "
            "and order_ts is at most 60 minutes apart."
        ),
        "body": """Definition
Impossible Geo (Fraud Case 15) is two orders for one customer shipped to
different dim_region values with order_ts at most one hour apart.

Formula: join fact_order_event to itself on customer_key where
shipping_region_key differs and unix_timestamp(later) - unix_timestamp(earlier)
<= 3600.

Do not use customer.region (home, static) or fact_sales / fact_inventory (STALE,
no hour, no shipping address). Seeded rows use address_id suffix -AGEO
(West vs Northeast, 25 minutes).

See also: fact_order_event, dim_address, dim_region.""",
        "related_assets": [
            "fact_order_event",
            "dim_address",
            "dim_region",
            "mv_order_event",
            "Fraud Geo Agent",
        ],
    },
    {
        "name": "Order Event Fact",
        "domain": "Sales",
        "synonyms": ["order event", "fact_order_event", "fraud order grain"],
        "description": (
            "Current order-grain fact for fraud: hour-level order_ts, ship/bill addresses, "
            "and regions. fact_sales is STALE line-grain merchandising only."
        ),
        "body": """Definition
fact_order_event is one row per customer_order. It carries order_ts (hour),
shipping_region_key, billing_region_key, ship_ne_bill, and cross_region.

Business use
Velocity, ship-to≠bill-to, and Impossible Geo read this fact (or mv_order_event).
fact_sales and fact_inventory remain in the catalog as STALE merchandising
tables for Retail Analytics history only.""",
        "related_assets": [
            "fact_order_event",
            "mv_order_event",
            "dim_address",
            "dim_region",
        ],
    },
]
