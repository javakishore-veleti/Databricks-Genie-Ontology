"""Ten Databricks Genie fraud specialists. All share the same OLTP + star-schema tables.

case_ids stay for MCP / API routing only. Genie instructions and sample
questions use plain English — no 01–15 labels.
"""

from __future__ import annotations

from ecommerce_genie_ontology.common.constants.fraud_cases import FRAUD_CASES

# Genie Sources for every fraud specialist. Keep analytics_log,
# analytics_log_customer, ingestion_tracker, and ingestion_log off this
# list — those are MCP / Spark operator tables, not Genie questions.
SHARED_TABLES = (
    ("customer", "oltp", "Retail customers"),
    ("customer_address", "oltp", "Billing, shipping, and home addresses (3 per customer)"),
    ("customer_account", "oltp", "Four accounts per customer: checking, CD, credit card, brokerage"),
    ("customer_order", "oltp", "Orders with status, amount, bill-to and ship-to"),
    ("customer_order_line", "oltp", "Order lines with sku, quantity, unit price"),
    ("customer_order_shipment", "oltp", "Shipments and carriers"),
    ("customer_transaction", "oltp", "Funds-movement postings with type, amount, and balances"),
    ("entity_link", "oltp", "1-2 hop entity relationships for shared address"),
    ("dim_customer", "star", "Customer dimension"),
    ("dim_product", "star", "Product dimension"),
    ("dim_account", "star", "Customer accounts"),
    ("dim_transaction_type", "star", "Funds-movement type codes"),
    ("dim_counterparty", "star", "Bank, brokerage, or card issuer on a posting"),
    ("dim_region", "star", "Conformed region for home, billing, and shipping"),
    ("dim_address", "star", "Billing, shipping, home, and far-region shipping addresses"),
    ("fact_order_event", "star", "Current order-grain fraud fact: hour-level ts, ship/bill regions"),
    ("fact_sales", "star", "STALE merchandising sales fact (order line). Do not use for fraud."),
    ("fact_returns", "star", "Returns derived from cancelled orders"),
    ("fact_inventory", "star", "STALE monthly inventory snapshot. Do not use for geo or velocity."),
    ("fact_transaction", "star", "One row per posting"),
)

_LIMIT = (
    "Return at most 50 rows. Never dump a full table. If a query returns no rows, "
    "say zero rows and stop. Do not invent load steps or next actions. "
    "Do not use fact_sales or fact_inventory except where this instruction says to. "
    "Prefer fact_order_event for order timing and ship-to vs bill-to."
)


FRAUD_AGENTS: tuple[dict[str, object], ...] = (
    {
        "id": "velocity",
        "title": "Fraud Velocity Agent",
        "case_ids": ("01", "07"),
        "description": "Detects order-velocity bursts and split orders under a dollar threshold.",
        "instructions": (
            "You are Fraud Velocity Agent. Look for two shopping patterns only.\n"
            "Velocity burst: the same customer places many orders on one calendar day "
            "(more than 20). That looks like a bot or a stolen account.\n"
            "Split orders: the same customer places at least three orders on one day "
            "whose amounts add up to about 80 to 120. That looks like one larger purchase "
            "cut into pieces to stay under a review limit.\n"
            "Use customer_order or fact_order_event. Group by customer and date. "
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which customers placed more than 20 orders on a single day?",
            "Which customers placed at least three orders on one day that add up to 80 to 120?",
        ),
    },
    {
        "id": "address_link",
        "title": "Fraud Address Link Agent",
        "case_ids": ("02", "06", "13"),
        "description": "Finds shared addresses across unrelated customers and duplicate accounts.",
        "instructions": (
            "You are Fraud Address Link Agent. Find customers who should not share a home.\n"
            "Look for the same street and postal code on more than one customer_id "
            "(customer_address or entity_link with rel shared_address or has_address).\n"
            "Also flag many new customers hanging off one address.\n"
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which addresses are used by more than one customer?",
            "Which customers share a street and postal code?",
        ),
    },
    {
        "id": "ship_bill",
        "title": "Fraud Ship-to Bill-to Agent",
        "case_ids": ("03",),
        "description": "Flags orders where shipping address is not the billing address.",
        "instructions": (
            "You are Fraud Ship-to Bill-to Agent. Find orders where the shipping address "
            "is not the billing address (customer_order or fact_order_event ship_ne_bill / "
            "different address keys).\n"
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which orders ship to an address that is not the billing address?",
        ),
    },
    {
        "id": "returns",
        "title": "Fraud Returns Agent",
        "case_ids": ("04", "12"),
        "description": "High return rate versus peers and rapid return after delivery.",
        "instructions": (
            "You are Fraud Returns Agent. Find customers with many returns versus peers, "
            "and returns that happen quickly after delivery.\n"
            "Use fact_returns with dim_customer. You may join shipments for return-after-delivery.\n"
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which customers have the most returns?",
            "Which returns happened soon after the order was delivered?",
        ),
    },
    {
        "id": "first_order",
        "title": "Fraud First-Order Agent",
        "case_ids": ("05",),
        "description": "High-value first orders from new customers.",
        "instructions": (
            "You are Fraud First-Order Agent. For each customer, take only their earliest "
            "order. Flag it when the amount is high (over 200).\n"
            "Use customer_order or fact_order_event.\n"
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which customers' first orders were over 200?",
        ),
    },
    {
        "id": "address_surge",
        "title": "Fraud Address Surge Agent",
        "case_ids": ("08", "09"),
        "description": "New address plus expedited ship, and address change followed by order surge.",
        "instructions": (
            "You are Fraud Address Surge Agent. Find a new or changed ship-to plus hurry: "
            "expedited carrier, or a burst of orders right after the address change.\n"
            "Use customer_order, customer_order_shipment, and customer_address.\n"
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which orders use a new shipping address and an expedited carrier?",
            "Which customers changed address and then ordered many times?",
        ),
    },
    {
        "id": "promo",
        "title": "Fraud Promo Agent",
        "case_ids": ("10",),
        "description": "Promo and discount abuse on order lines.",
        "instructions": (
            "You are Fraud Promo Agent. Find heavy discount or promo use on order lines "
            "(customer_order_line). Look for repeated low unit prices or the same customer "
            "stacking discounts.\n"
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which customers have unusually low unit prices or repeated discounts on order lines?",
        ),
    },
    {
        "id": "inventory",
        "title": "Fraud Inventory Agent",
        "case_ids": ("11",),
        "description": "Orders versus STALE fact_inventory. Prefer fact_order_event for customer fraud.",
        "instructions": (
            "You are Fraud Inventory Agent. Compare ordered quantity to stock on "
            "fact_inventory (STALE monthly snapshot). Say when you use that snapshot. "
            "Prefer fact_order_event for who ordered what. Do not use inventory for geography.\n"
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which products were ordered in amounts that exceed stock on hand?",
        ),
    },
    {
        "id": "cancel",
        "title": "Fraud Cancel Agent",
        "case_ids": ("14",),
        "description": "Orders that are cancelled or abort shipment.",
        "instructions": (
            "You are Fraud Cancel Agent. Find orders with status cancelled, or shipments "
            "that abort after they start. Use customer_order and customer_order_shipment.\n"
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which orders were cancelled or had a shipment aborted?",
        ),
    },
    {
        "id": "geo",
        "title": "Fraud Geo Agent",
        "case_ids": ("15",),
        "description": "Impossible geography: two regions on the same customer in a short window.",
        "instructions": (
            "You are Fraud Geo Agent. Find the same customer with two shipping regions "
            "within one hour — physically unlikely travel.\n"
            "Join retail_star.fact_order_event to itself on customer_key where "
            "shipping_region_key differs and order_ts is at most 60 minutes apart.\n"
            "Do not use customer.region (home, static). Do not use fact_sales or "
            "fact_inventory — those are STALE merchandising snapshots with midnight "
            "dates and no shipping address.\n"
            "Seeded customers have address_id ending in AGEO (West vs Northeast) and a "
            "pair of orders 25 minutes apart. Report customer_key, both order ids, "
            "regions, timestamps, and minutes_apart. "
            f"{_LIMIT}"
        ),
        "sample_questions": (
            "Which customers had orders shipped to two different regions within one hour?",
            "Monthly time series aggregation of order_amount from customer_order table",
            "Distribution of segment in the customer table",
            "What tables are there and how are they connected? Give me a short summary.",
        ),
    },
)


def agent_by_id(agent_id: str) -> dict[str, object] | None:
    return next((item for item in FRAUD_AGENTS if item["id"] == agent_id), None)


def case_names(case_ids: tuple[str, ...] | list[str]) -> list[str]:
    wanted = set(case_ids)
    return [item["name"] for item in FRAUD_CASES if item["id"] in wanted]


def case_ids_and_names(case_ids: tuple[str, ...] | list[str]) -> list[str]:
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
        ("geo", ("geo", "region", "impossible", "two cities", "two different regions")),
    )
    for agent_id, words in keywords:
        if any(word in text for word in words):
            return agent_id
    return "velocity"
