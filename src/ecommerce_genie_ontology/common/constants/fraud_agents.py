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
    ("fact_sales", "star", "Sales facts aligned to OLTP lines"),
    ("fact_returns", "star", "Returns derived from cancelled orders"),
    ("fact_inventory", "star", "Inventory snapshots by product"),
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
        "description": "Orders versus inventory mismatch on facts.",
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
            "You are Fraud Geo Agent. Investigate case 15 Impossible geo two regions one hour.\n"
            "\n"
            "What this analysis detects:\n"
            "- Customers with transactions or orders in two regions within one hour "
            "(possible account compromise from a different location than the account holder).\n"
            "- Geographic impossibility: travel between those regions is not possible in the elapsed time.\n"
            "- High-risk region pairs that show up in impossible-geo activity.\n"
            "- Repeat customers with more than one impossible-geo instance.\n"
            "\n"
            "Required data (query these; LIMIT 50; never dump full tables):\n"
            "- customer_transaction: customer_id, txn_ts\n"
            "- customer / dim_customer: home region\n"
            "- customer_order and customer_address: ship and bill regions\n"
            "- analytics_log_customer: prior per-customer outcomes when present\n"
            "\n"
            "If tables are empty, report row counts are zero and stop. "
            "Do not invent next steps, load-data instructions, or operational advice."
        ),
        "sample_questions": (
            "Run fraud case 15 Impossible geo two regions one hour",
            "Which customers have transactions in two regions within one hour?",
            "Which region pairs appear in impossible-geo activity?",
            "Which customers repeat impossible-geo more than once?",
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
