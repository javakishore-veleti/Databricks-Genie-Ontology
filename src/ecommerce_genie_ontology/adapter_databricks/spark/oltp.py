from __future__ import annotations

from datetime import date

from ecommerce_genie_ontology.common.constants.schema_ddl import oltp_statements
from ecommerce_genie_ontology.common.constants.transaction_types import (
    ACCOUNT_PRODUCTS,
    COUNTERPARTY_KINDS,
    LAB_POSTINGS_PER_YEAR,
    MAX_GENERATED_ORDERS,
    MAX_GENERATED_POSTINGS,
    TRANSACTION_TYPES,
)

SEGMENTS = ["Consumer", "Small Business", "Enterprise"]
REGIONS = ["Northeast", "Southeast", "Midwest", "Southwest", "West"]
ADDRESS_TYPES = ["billing", "shipping", "home"]
CHANNELS = ["Online", "In-Store"]
STATUSES = ["placed", "paid", "shipped", "delivered", "cancelled"]
CARRIERS = ["UPS", "FedEx", "USPS", "DHL"]
CASE15_CUSTOMERS = 20
CASE15_ADDR_SUFFIX = "AGEO"


def history_start(today: date, year_count: int) -> date:
    month = today.month
    try:
        return date(today.year - year_count, month, today.day)
    except ValueError:
        return date(today.year - year_count, month, 28)


def window_start(today: date, year_window: str) -> date:
    mapping = {"latest": 1, "last_2": 2, "last_3": 3, "all": 3}
    years = mapping.get(year_window, 1)
    return history_start(today, years)


def clamp_cdc_count(count: int) -> int:
    return max(100, min(10_000, int(count)))


def ensure_oltp_schema(spark, catalog: str, oltp_schema: str) -> str:
    fq = f"{catalog}.{oltp_schema}"
    for sql in oltp_statements(fq):
        spark.sql(sql)
    return fq


def generate_historical(
    spark,
    catalog: str,
    oltp_schema: str,
    customer_count: int,
    orders_per_year: int,
    year_count: int,
) -> dict[str, int]:
    from pyspark.sql import functions as F

    fq = ensure_oltp_schema(spark, catalog, oltp_schema)
    today = date.today()
    start = history_start(today, year_count)
    days = max((today - start).days, 1)
    n_customers = max(int(customer_count), 1)
    n_orders = min(
        n_customers * max(int(orders_per_year), 1) * max(int(year_count), 1),
        MAX_GENERATED_ORDERS,
    )
    n_accounts = n_customers * len(ACCOUNT_PRODUCTS)
    n_postings = min(n_customers * LAB_POSTINGS_PER_YEAR * max(int(year_count), 1), MAX_GENERATED_POSTINGS)
    if n_customers * max(int(orders_per_year), 1) * max(int(year_count), 1) > MAX_GENERATED_ORDERS:
        print(
            f"CLAMP generate orders to {n_orders:,}. "
            "30 billion postings is capacity, not a generate run."
        )

    customers = (
        spark.range(n_customers)
        .withColumn("customer_id", F.format_string("C%06d", F.col("id") + 1))
        .withColumn("customer_name", F.concat(F.lit("Customer "), F.col("id") + 1))
        .withColumn("segment", F.element_at(F.array(*[F.lit(s) for s in SEGMENTS]), (F.col("id") % 3 + 1).cast("int")))
        .withColumn("region", F.element_at(F.array(*[F.lit(s) for s in REGIONS]), (F.col("id") % 5 + 1).cast("int")))
        .withColumn("signup_date", F.date_sub(F.lit(str(start)), (F.col("id") % 400).cast("int")))
        .withColumn("created_at", F.current_timestamp())
        .withColumn("updated_at", F.current_timestamp())
        .drop("id")
    )
    customers.write.mode("overwrite").saveAsTable(f"{fq}.customer")

    addresses = (
        spark.range(n_customers * 3)
        .withColumn("customer_seq", (F.col("id") / 3).cast("int"))
        .withColumn("addr_n", (F.col("id") % 3).cast("int"))
        .withColumn("customer_id", F.format_string("C%06d", F.col("customer_seq") + 1))
        .withColumn("address_id", F.concat(F.col("customer_id"), F.lit("-A"), F.col("addr_n")))
        .withColumn(
            "address_type",
            F.element_at(F.array(*[F.lit(s) for s in ADDRESS_TYPES]), (F.col("addr_n") + 1).cast("int")),
        )
        .withColumn("line1", F.concat(F.lit((F.col("id") + 100).cast("string")), F.lit(" Market St")))
        .withColumn("city", F.concat(F.lit("City "), (F.col("customer_seq") % 50).cast("string")))
        .withColumn("region", F.element_at(F.array(*[F.lit(s) for s in REGIONS]), (F.col("customer_seq") % 5 + 1).cast("int")))
        .withColumn("postal_code", F.format_string("%05d", (F.col("id") % 90000) + 10000))
        .withColumn("is_primary", F.col("addr_n") == 0)
        .drop("id", "customer_seq", "addr_n")
    )
    addresses.write.mode("overwrite").saveAsTable(f"{fq}.customer_address")

    accounts = (
        spark.range(n_accounts)
        .withColumn("customer_seq", (F.col("id") / len(ACCOUNT_PRODUCTS)).cast("int"))
        .withColumn("acct_n", (F.col("id") % len(ACCOUNT_PRODUCTS)).cast("int"))
        .withColumn("customer_id", F.format_string("C%06d", F.col("customer_seq") + 1))
        .withColumn("account_id", F.concat(F.col("customer_id"), F.lit("-ACCT"), F.col("acct_n")))
        .withColumn(
            "product",
            F.element_at(F.array(*[F.lit(s) for s in ACCOUNT_PRODUCTS]), (F.col("acct_n") + 1).cast("int")),
        )
        .withColumn("opened_date", F.date_sub(F.lit(str(start)), (F.col("id") % 200).cast("int")))
        .withColumn("status", F.lit("open"))
        .drop("id", "customer_seq", "acct_n")
    )
    accounts.write.mode("overwrite").saveAsTable(f"{fq}.customer_account")

    type_codes = [item[0] for item in TRANSACTION_TYPES]
    counterparties = [item[0] for item in COUNTERPARTY_KINDS]
    postings = (
        spark.range(n_postings)
        .withColumn("customer_seq", (F.col("id") % n_customers).cast("int"))
        .withColumn("acct_n", (F.col("id") % len(ACCOUNT_PRODUCTS)).cast("int"))
        .withColumn("customer_id", F.format_string("C%06d", F.col("customer_seq") + 1))
        .withColumn("account_id", F.concat(F.col("customer_id"), F.lit("-ACCT"), F.col("acct_n")))
        .withColumn("transaction_id", F.format_string("T%012d", F.col("id") + 1))
        .withColumn(
            "type_code",
            F.element_at(F.array(*[F.lit(s) for s in type_codes]), (F.col("id") % len(type_codes) + 1).cast("int")),
        )
        .withColumn(
            "counterparty_id",
            F.element_at(
                F.array(*[F.lit(s) for s in counterparties]),
                (F.col("id") % len(counterparties) + 1).cast("int"),
            ),
        )
        .withColumn("day_off", (F.col("id") % days).cast("int"))
        .withColumn(
            "txn_ts",
            F.from_unixtime(
                F.unix_timestamp(F.date_add(F.lit(str(start)), F.col("day_off")))
                + (F.col("id") % 24) * 3600
                + ((F.col("id") * 7) % 60) * 60
            ).cast("timestamp"),
        )
        .withColumn("txn_date", F.to_date("txn_ts"))
        .withColumn("amount", ((F.col("id") % 240) * 5 + 25).cast("decimal(12,2)"))
        .withColumn("balance_before", ((F.col("id") % 4000) * 3 + 200).cast("decimal(14,2)"))
        .withColumn("balance_after", (F.col("balance_before") + F.col("amount")).cast("decimal(14,2)"))
        .withColumn("status", F.lit("posted"))
        .drop("id", "customer_seq", "acct_n", "day_off")
    )
    postings.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fq}.customer_transaction")

    orders = (
        spark.range(n_orders)
        .withColumn("customer_seq", (F.col("id") % n_customers).cast("int"))
        .withColumn("customer_id", F.format_string("C%06d", F.col("customer_seq") + 1))
        .withColumn("order_id", F.format_string("O%012d", F.col("id") + 1))
        .withColumn("day_off", (F.col("id") % days).cast("int"))
        .withColumn(
            "order_ts",
            F.from_unixtime(
                F.unix_timestamp(F.date_add(F.lit(str(start)), F.col("day_off")))
                + (F.col("id") % 24) * 3600
                + ((F.col("id") * 11) % 60) * 60
            ).cast("timestamp"),
        )
        .withColumn("status", F.element_at(F.array(*[F.lit(s) for s in STATUSES]), (F.col("id") % 5 + 1).cast("int")))
        .withColumn("store_id", (F.col("id") % 10 + 1).cast("int"))
        .withColumn("billing_address_id", F.concat(F.col("customer_id"), F.lit("-A0")))
        .withColumn(
            "shipping_address_id",
            F.concat(F.col("customer_id"), F.lit("-A"), (F.col("id") % 3).cast("string")),
        )
        .withColumn("order_amount", ((F.col("id") % 90) * 3 + 15).cast("decimal(12,2)"))
        .drop("id", "customer_seq", "day_off")
    )
    orders.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fq}.customer_order")

    lines = (
        spark.range(n_orders * 3)
        .withColumn("order_seq", (F.col("id") / 3).cast("long"))
        .withColumn("line_n", (F.col("id") % 3).cast("int"))
        .withColumn("order_id", F.format_string("O%012d", F.col("order_seq") + 1))
        .withColumn("order_line_id", F.concat(F.col("order_id"), F.lit("-L"), F.col("line_n")))
        .withColumn("sku", F.format_string("SKU-%03d", (F.col("id") % 50 + 1).cast("int")))
        .withColumn("quantity", (F.col("id") % 4 + 1).cast("int"))
        .withColumn("unit_price", ((F.col("id") % 40) + 9.99).cast("decimal(10,2)"))
        .withColumn("line_amount", (F.col("quantity") * F.col("unit_price")).cast("decimal(12,2)"))
        .drop("id", "order_seq", "line_n")
    )
    lines.write.mode("overwrite").saveAsTable(f"{fq}.customer_order_line")

    shipments = (
        orders.filter(F.col("status").isin("shipped", "delivered", "paid"))
        .select(
            F.concat(F.col("order_id"), F.lit("-S0")).alias("shipment_id"),
            "order_id",
            F.col("order_ts") + F.expr("INTERVAL 2 DAYS").alias("ship_ts"),
            F.element_at(F.array(*[F.lit(s) for s in CARRIERS]), (F.abs(F.hash("order_id")) % 4 + 1).cast("int")).alias(
                "carrier"
            ),
            F.concat(F.lit("TRK"), F.col("order_id")).alias("tracking_number"),
            F.lit("in_transit").alias("status"),
            "shipping_address_id",
        )
        .withColumnRenamed("shipping_address_id", "ship_address_id")
    )
    shipments.write.mode("overwrite").saveAsTable(f"{fq}.customer_order_shipment")

    seed_case15(spark, fq, start)
    _write_entity_links(spark, fq)
    from ecommerce_genie_ontology.adapter_databricks.spark.ingest import snapshot_oltp

    snapshot_oltp(spark, catalog, oltp_schema, pipeline="oltp_historical")
    return {
        "customers": n_customers,
        "addresses": n_customers * 3,
        "accounts": n_accounts,
        "orders": n_orders,
        "lines": n_orders * 3,
        "postings": n_postings,
    }


def generate_realtime(
    spark,
    catalog: str,
    oltp_schema: str,
    count: int,
    year_window: str,
) -> dict[str, int]:
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    fq = ensure_oltp_schema(spark, catalog, oltp_schema)
    n = clamp_cdc_count(count)
    today = date.today()
    start = window_start(today, year_window)
    days = max((today - start).days, 1)
    max_id = spark.sql(
        f"SELECT COALESCE(MAX(CAST(substring(order_id, 2) AS BIGINT)), 0) AS m FROM {fq}.customer_order"
    ).collect()[0]["m"]
    customers = spark.table(f"{fq}.customer").select("customer_id").withColumn(
        "customer_seq", F.row_number().over(Window.orderBy("customer_id")) - 1
    )
    n_customers = customers.count() or 1
    new_orders = (
        spark.range(n)
        .withColumn("seq", F.col("id") + int(max_id) + 1)
        .withColumn("customer_seq", (F.col("id") % n_customers).cast("int"))
        .join(customers, "customer_seq", "left")
        .withColumn("order_id", F.format_string("O%012d", F.col("seq")))
        .withColumn(
            "order_ts",
            F.from_unixtime(
                F.unix_timestamp(F.date_add(F.lit(str(start)), (F.col("id") % days).cast("int")))
                + (F.col("id") % 24) * 3600
                + ((F.col("id") * 11) % 60) * 60
            ).cast("timestamp"),
        )
        .withColumn("status", F.lit("placed"))
        .withColumn("store_id", (F.col("id") % 10 + 1).cast("int"))
        .withColumn("billing_address_id", F.concat(F.col("customer_id"), F.lit("-A0")))
        .withColumn("shipping_address_id", F.concat(F.col("customer_id"), F.lit("-A"), (F.col("id") % 3).cast("string")))
        .withColumn("order_amount", ((F.col("id") % 90) * 3 + 15).cast("decimal(12,2)"))
        .select(
            "order_id",
            "customer_id",
            "order_ts",
            "status",
            "store_id",
            "billing_address_id",
            "shipping_address_id",
            "order_amount",
        )
    )
    new_orders.write.mode("append").saveAsTable(f"{fq}.customer_order")
    lines = (
        spark.range(n * 3)
        .withColumn("order_off", (F.col("id") / 3).cast("long"))
        .withColumn("line_n", (F.col("id") % 3).cast("int"))
        .withColumn("seq", F.col("order_off") + int(max_id) + 1)
        .withColumn("order_id", F.format_string("O%012d", F.col("seq")))
        .withColumn("order_line_id", F.concat(F.col("order_id"), F.lit("-L"), F.col("line_n")))
        .withColumn("sku", F.format_string("SKU-%03d", (F.col("id") % 50 + 1).cast("int")))
        .withColumn("quantity", (F.col("id") % 4 + 1).cast("int"))
        .withColumn("unit_price", ((F.col("id") % 40) + 9.99).cast("decimal(10,2)"))
        .withColumn("line_amount", (F.col("quantity") * F.col("unit_price")).cast("decimal(12,2)"))
        .select("order_line_id", "order_id", "sku", "quantity", "unit_price", "line_amount")
    )
    lines.write.mode("append").saveAsTable(f"{fq}.customer_order_line")
    shipments = new_orders.select(
        F.concat(F.col("order_id"), F.lit("-S0")).alias("shipment_id"),
        "order_id",
        (F.col("order_ts") + F.expr("INTERVAL 2 DAYS")).alias("ship_ts"),
        F.element_at(F.array(*[F.lit(s) for s in CARRIERS]), (F.abs(F.hash("order_id")) % 4 + 1).cast("int")).alias(
            "carrier"
        ),
        F.concat(F.lit("TRK"), F.col("order_id")).alias("tracking_number"),
        F.lit("in_transit").alias("status"),
        F.col("shipping_address_id").alias("ship_address_id"),
    )
    shipments.write.mode("append").saveAsTable(f"{fq}.customer_order_shipment")
    max_txn = spark.sql(
        f"SELECT COALESCE(MAX(CAST(substring(transaction_id, 2) AS BIGINT)), 0) AS m FROM {fq}.customer_transaction"
    ).collect()[0]["m"]
    type_codes = [item[0] for item in TRANSACTION_TYPES]
    counterparties = [item[0] for item in COUNTERPARTY_KINDS]
    new_postings = (
        spark.range(n)
        .withColumn("seq", F.col("id") + int(max_txn) + 1)
        .withColumn("customer_seq", (F.col("id") % n_customers).cast("int"))
        .join(customers, "customer_seq", "left")
        .withColumn("acct_n", (F.col("id") % len(ACCOUNT_PRODUCTS)).cast("int"))
        .withColumn("account_id", F.concat(F.col("customer_id"), F.lit("-ACCT"), F.col("acct_n")))
        .withColumn("transaction_id", F.format_string("T%012d", F.col("seq")))
        .withColumn(
            "type_code",
            F.element_at(F.array(*[F.lit(s) for s in type_codes]), (F.col("id") % len(type_codes) + 1).cast("int")),
        )
        .withColumn(
            "counterparty_id",
            F.element_at(
                F.array(*[F.lit(s) for s in counterparties]),
                (F.col("id") % len(counterparties) + 1).cast("int"),
            ),
        )
        .withColumn(
            "txn_ts",
            F.from_unixtime(
                F.unix_timestamp(F.date_add(F.lit(str(start)), (F.col("id") % days).cast("int")))
                + (F.col("id") % 24) * 3600
                + ((F.col("id") * 7) % 60) * 60
            ).cast("timestamp"),
        )
        .withColumn("txn_date", F.to_date("txn_ts"))
        .withColumn("amount", ((F.col("id") % 240) * 5 + 25).cast("decimal(12,2)"))
        .withColumn("balance_before", ((F.col("id") % 4000) * 3 + 200).cast("decimal(14,2)"))
        .withColumn("balance_after", (F.col("balance_before") + F.col("amount")).cast("decimal(14,2)"))
        .withColumn("status", F.lit("posted"))
        .select(
            "transaction_id",
            "customer_id",
            "account_id",
            "counterparty_id",
            "type_code",
            "txn_ts",
            "txn_date",
            "amount",
            "balance_before",
            "balance_after",
            "status",
        )
    )
    new_postings.write.mode("append").saveAsTable(f"{fq}.customer_transaction")
    seed_case15(spark, fq, start)
    return {"orders": n, "lines": n * 3, "postings": n, "year_window": year_window}


def seed_case15(spark, fq: str, event_date: date) -> int:
    """Add a far-region shipping address and two orders 25 minutes apart for Case 15."""
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    already = (
        spark.table(f"{fq}.customer_order")
        .filter(F.col("shipping_address_id").endswith(f"-{CASE15_ADDR_SUFFIX}"))
        .limit(1)
        .count()
    )
    if already:
        print("OK    Case 15 impossible-geo orders already present")
        return 0

    customers = (
        spark.table(f"{fq}.customer")
        .select("customer_id", "region")
        .orderBy("customer_id")
        .limit(CASE15_CUSTOMERS)
    )
    far = customers.select(
        F.concat(F.col("customer_id"), F.lit(f"-{CASE15_ADDR_SUFFIX}")).alias("address_id"),
        "customer_id",
        F.lit("shipping").alias("address_type"),
        F.concat(F.lit("900 Distant Ave "), F.col("customer_id")).alias("line1"),
        F.lit("Remote City").alias("city"),
        F.when(F.col("region") == "West", F.lit("Northeast")).otherwise(F.lit("West")).alias("region"),
        F.lit("99999").alias("postal_code"),
        F.lit(False).alias("is_primary"),
    )
    have = spark.table(f"{fq}.customer_address").select("address_id")
    new_addr = far.join(have, "address_id", "left_anti")
    added_addr = new_addr.count()
    if added_addr:
        new_addr.write.mode("append").saveAsTable(f"{fq}.customer_address")
        print(f"OK    Case 15 far-region addresses: {added_addr}")

    targets = (
        spark.table(f"{fq}.customer_address")
        .filter(F.col("address_id").endswith(f"-{CASE15_ADDR_SUFFIX}"))
        .select("customer_id", "address_id")
        .orderBy("customer_id")
    )
    n = targets.count()
    if n == 0:
        return 0
    max_order = spark.sql(
        f"SELECT COALESCE(MAX(CAST(substring(order_id, 2) AS BIGINT)), 0) AS m FROM {fq}.customer_order"
    ).collect()[0]["m"]
    base = targets.withColumn("rn", F.row_number().over(Window.orderBy("customer_id")) - 1)
    home = base.select(
        F.format_string("O%012d", F.lit(int(max_order)) + F.col("rn") * 2 + 1).alias("order_id"),
        "customer_id",
        F.to_timestamp(F.lit(f"{event_date.isoformat()} 10:00:00")).alias("order_ts"),
        F.lit("paid").alias("status"),
        F.lit(1).alias("store_id"),
        F.concat(F.col("customer_id"), F.lit("-A0")).alias("billing_address_id"),
        F.concat(F.col("customer_id"), F.lit("-A0")).alias("shipping_address_id"),
        F.lit("188.00").cast("decimal(12,2)").alias("order_amount"),
    )
    distant = base.select(
        F.format_string("O%012d", F.lit(int(max_order)) + F.col("rn") * 2 + 2).alias("order_id"),
        "customer_id",
        F.to_timestamp(F.lit(f"{event_date.isoformat()} 10:25:00")).alias("order_ts"),
        F.lit("paid").alias("status"),
        F.lit(1).alias("store_id"),
        F.concat(F.col("customer_id"), F.lit("-A0")).alias("billing_address_id"),
        F.col("address_id").alias("shipping_address_id"),
        F.lit("412.00").cast("decimal(12,2)").alias("order_amount"),
    )
    orders = home.unionByName(distant)
    orders.write.mode("append").saveAsTable(f"{fq}.customer_order")
    lines = (
        orders.select("order_id")
        .withColumn("line_n", F.lit(0))
        .select(
            F.concat(F.col("order_id"), F.lit("-L0")).alias("order_line_id"),
            "order_id",
            F.lit("SKU-015").alias("sku"),
            F.lit(1).alias("quantity"),
            F.lit("99.00").cast("decimal(10,2)").alias("unit_price"),
            F.lit("99.00").cast("decimal(12,2)").alias("line_amount"),
        )
    )
    lines.write.mode("append").saveAsTable(f"{fq}.customer_order_line")
    shipments = orders.select(
        F.concat(F.col("order_id"), F.lit("-S0")).alias("shipment_id"),
        "order_id",
        (F.col("order_ts") + F.expr("INTERVAL 2 DAYS")).alias("ship_ts"),
        F.lit("FedEx").alias("carrier"),
        F.concat(F.lit("TRK"), F.col("order_id")).alias("tracking_number"),
        F.lit("in_transit").alias("status"),
        F.col("shipping_address_id").alias("ship_address_id"),
    )
    shipments.write.mode("append").saveAsTable(f"{fq}.customer_order_shipment")
    print(f"OK    Case 15 impossible-geo orders: {n * 2} (25 minutes, West vs Northeast)")
    return n * 2


def _write_entity_links(spark, fq: str) -> None:
    from pyspark.sql import functions as F

    addr = spark.table(f"{fq}.customer_address").select(
        F.lit("customer").alias("src_type"),
        F.col("customer_id").alias("src_id"),
        F.lit("has_address").alias("rel"),
        F.lit("address").alias("dst_type"),
        F.col("address_id").alias("dst_id"),
        F.lit(1.0).alias("weight"),
    )
    shared = (
        spark.table(f"{fq}.customer_address")
        .groupBy("line1", "postal_code")
        .agg(F.collect_set("customer_id").alias("cids"))
        .filter(F.size("cids") > 1)
        .select(F.explode("cids").alias("src_id"), "cids")
        .select(
            F.lit("customer").alias("src_type"),
            "src_id",
            F.lit("shared_address").alias("rel"),
            F.lit("customer").alias("dst_type"),
            F.explode("cids").alias("dst_id"),
            F.lit(1.0).alias("weight"),
        )
        .filter(F.col("src_id") != F.col("dst_id"))
    )
    addr.unionByName(shared).write.mode("overwrite").saveAsTable(f"{fq}.entity_link")
