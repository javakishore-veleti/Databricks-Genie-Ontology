"""Ten Databricks Genie fraud specialists. All share the same OLTP + star-schema tables."""

from __future__ import annotations

from ecommerce_genie_ontology.common.constants.fraud_cases import FRAUD_CASES

SHARED_TABLES = (
    ("customer", "oltp", "Retail customers"),
    ("customer_address", "oltp", "Billing, shipping, and home addresses (3 per customer)"),
    ("customer_account", "oltp", "Four accounts per customer: checking, CD, credit card, brokerage"),
    ("customer_order", "oltp", "Orders with status, amount, bill-to and ship-to"),
    ("customer_order_line", "oltp", "Order lines with sku, quantity, unit price"),
    ("customer_order_shipment", "oltp", "Shipments and carriers"),
    ("customer_transaction", "oltp", "Funds-movement postings with type, amount, and balances"),
    ("entity_link", "oltp", "1-2 hop entity relationships for shared address"),
    ("analytics_log", "oltp", "Fraud analytics session header"),
    ("analytics_log_customer", "oltp", "Per-customer fraud outcome and counts"),
    ("dim_customer", "star", "Customer dimension"),
    ("dim_product", "star", "Product dimension"),
    ("dim_account", "star", "Customer accounts"),
    ("dim_transaction_type", "star", "Funds-movement type codes"),
    ("dim_counterparty", "star", "Bank, brokerage, or card issuer on a posting"),
    ("dim_region", "star", "Conformed region for home, billing, and shipping"),
    ("dim_address", "star", "Billing, shipping, home, and Case 15 far-region addresses"),
    ("fact_order_event", "star", "Current order-grain fraud fact: hour-level ts, ship/bill regions"),
    ("fact_sales", "star", "STALE merchandising sales fact (order line). Do not use for fraud."),
    ("fact_returns", "star", "Returns derived from cancelled orders"),
    ("fact_inventory", "star", "STALE monthly inventory snapshot. Do not use for geo or velocity."),
    ("fact_transaction", "star", "One row per posting"),
)

FRAUD_AGENTS: tuple[dict[str, object], ...] = (
    {
        "id": "velocity",
        "title": "Fraud Velocity Agent",
        "case_ids": ("01", "07"),
        "description": "Detects order-velocity bursts and split orders under a dollar threshold.",
    },
    {
        "id": "address_link",
        "title": "Fraud Address Link Agent",
        "case_ids": ("02", "06", "13"),
        "description": "Finds shared addresses across unrelated customers and duplicate accounts.",
    },
    {
        "id": "ship_bill",
        "title": "Fraud Ship-to Bill-to Agent",
        "case_ids": ("03",),
        "description": "Flags orders where shipping address is not the billing address.",
    },
    {
        "id": "returns",
        "title": "Fraud Returns Agent",
        "case_ids": ("04", "12"),
        "description": "High return rate versus peers and rapid return after delivery.",
    },
    {
        "id": "first_order",
        "title": "Fraud First-Order Agent",
        "case_ids": ("05",),
        "description": "High-value first orders from new customers.",
    },
    {
        "id": "address_surge",
        "title": "Fraud Address Surge Agent",
        "case_ids": ("08", "09"),
        "description": "New address plus expedited ship, and address change followed by order surge.",
    },
    {
        "id": "promo",
        "title": "Fraud Promo Agent",
        "case_ids": ("10",),
        "description": "Promo and discount abuse on order lines.",
    },
    {
        "id": "inventory",
        "title": "Fraud Inventory Agent",
        "case_ids": ("11",),
        "description": "Orders versus STALE fact_inventory. Prefer fact_order_event for customer fraud.",
    },
    {
        "id": "cancel",
        "title": "Fraud Cancel Agent",
        "case_ids": ("14",),
        "description": "Orders that are cancelled or abort shipment.",
    },
    {
        "id": "geo",
        "title": "Fraud Geo Agent",
        "case_ids": ("15",),
        "description": "Impossible geography: two regions on the same customer in a short window.",
        "instructions": (
            "You are Fraud Geo Agent. Investigate Case 15 Impossible geo — two shipping "
            "regions within one hour.\n"
            "Join retail_star.fact_order_event to itself on customer_key where "
            "shipping_region_key differs and order_ts is at most 60 minutes apart. "
            "Prefer mv_order_event when you only need counts.\n"
            "Do not use customer.region (home, static). Do not use fact_sales or "
            "fact_inventory — those are STALE merchandising snapshots with midnight "
            "dates and no shipping address.\n"
            "Seeded customers have address_id *-AGEO (West vs Northeast) and a pair of "
            "orders 25 minutes apart. Report customer_key, both order ids, regions, "
            "timestamps, and minutes_apart. LIMIT 50. Do not say the tables are empty."
        ),
        "sample_questions": (
            "Run fraud case 15 Impossible geo two regions one hour",
            "Monthly time series aggregation of order_amount from customer_order table",
            "Distribution of segment in the customer table",
            "What tables are there and how are they connected? Give me a short summary.",
            "Distribution of customer_id count in the analytics_log table",
        ),
    },
)


def agent_by_id(agent_id: str) -> dict[str, object] | None:
    return next((item for item in FRAUD_AGENTS if item["id"] == agent_id), None)


def case_names(case_ids: tuple[str, ...] | list[str]) -> list[str]:
    wanted = set(case_ids)
    return [f"{item['id']} {item['name']}" for item in FRAUD_CASES if item["id"] in wanted]


def route_agent_id(prompt: str) -> str:
    text = prompt.lower()
    keywords = (
        ("velocity", ("burst", "velocity", "split order", "many orders")),
        ("address_link", ("shared address", "duplicate", "same address", "unrelated")),
        ("ship_bill", ("ship-to", "bill-to", "shipping address", "billing")),
        ("returns", ("return", "refund")),
        ("first_order", ("first order", "new customer", "first-order")),
        ("address_surge", ("expedited", "address change", "new address")),
        ("promo", ("promo", "discount", "coupon")),
        ("inventory", ("inventory", "stock", "mismatch")),
        ("cancel", ("cancel", "abort")),
        ("geo", ("geo", "region", "impossible", "two cities")),
    )
    for agent_id, words in keywords:
        if any(word in text for word in words):
            return agent_id
    return "velocity"
