"""Incremental OLTP batches and month-window star ETL, keyed by ingestion_tracker / ingestion_log."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from uuid import uuid4

from ecommerce_genie_ontology.adapter_databricks.spark import oltp as spark_oltp
from ecommerce_genie_ontology.common.constants.schema_ddl import ingest_statements
from ecommerce_genie_ontology.common.constants.transaction_types import (
    ACCOUNT_PRODUCTS,
    COUNTERPARTY_KINDS,
    TRANSACTION_TYPES,
)

CAPACITY_START = date(2016, 9, 18)
CAPACITY_END = date(2026, 9, 18)

OLTP_TABLES = (
    "customer",
    "customer_address",
    "customer_account",
    "customer_order",
    "customer_order_line",
    "customer_order_shipment",
    "customer_transaction",
)
STAR_TABLES = ("fact_sales", "fact_returns", "fact_inventory", "fact_transaction")


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def _ensure_tables(spark, fq: str) -> None:
    for sql in ingest_statements(fq):
        spark.sql(sql)


def _count(spark, fq: str, table_name: str) -> int:
    try:
        return int(spark.table(f"{fq}.{table_name}").count())
    except Exception:
        return 0


def _min_max_date(spark, fq: str, table_name: str, column: str) -> tuple[date | None, date | None]:
    from pyspark.sql import functions as F

    if _count(spark, fq, table_name) == 0:
        return None, None
    row = spark.table(f"{fq}.{table_name}").select(F.min(column).alias("lo"), F.max(column).alias("hi")).collect()[0]
    lo = row["lo"]
    hi = row["hi"]
    if lo is None:
        return None, None
    if hasattr(lo, "date"):
        lo = lo.date()
    if hasattr(hi, "date"):
        hi = hi.date()
    return lo, hi


def _latest_end(spark, fq: str, table_names: tuple[str, ...]) -> date | None:
    from pyspark.sql import functions as F

    if _count(spark, fq, "ingestion_tracker") == 0:
        return None
    row = (
        spark.table(f"{fq}.ingestion_tracker")
        .filter(F.col("table_name").isin(list(table_names)))
        .select(F.max("end_date").alias("d"))
        .collect()[0]
    )
    return row["d"]


def snapshot_tables(
    spark,
    fq: str,
    table_names: tuple[str, ...],
    *,
    start_date: date | None,
    end_date: date | None,
    pipeline: str,
    started_at: datetime,
    months: int | None = None,
    status: str = "ok",
) -> None:
    from pyspark.sql import functions as F

    _ensure_tables(spark, fq)
    now = datetime.utcnow()
    year = (end_date or start_date or CAPACITY_START).year
    existing = {}
    if _count(spark, fq, "ingestion_tracker"):
        for row in spark.table(f"{fq}.ingestion_tracker").collect():
            existing[row["table_name"]] = row
    track_rows = []
    log_rows = []
    for name in table_names:
        ending = _count(spark, fq, name)
        prior = existing.get(name)
        starting = int(prior["rows_inserted"]) if prior else 0
        first = start_date or (prior["start_date"] if prior else None) or CAPACITY_START
        last = end_date or (prior["end_date"] if prior else None) or first
        track_rows.append((name, name, ending, first, last, last.year, now))
        log_rows.append(
            (
                uuid4().hex,
                name,
                started_at,
                now,
                starting,
                ending,
                first,
                last,
                year,
                months,
                pipeline,
                status,
            )
        )
    spark.createDataFrame(
        track_rows,
        "tracker_id string, table_name string, rows_inserted bigint, start_date date, end_date date, year int, updated_at timestamp",
    ).write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{fq}.ingestion_tracker")
    if existing:
        kept = [
            (
                row["tracker_id"],
                row["table_name"],
                row["rows_inserted"],
                row["start_date"],
                row["end_date"],
                row["year"],
                row["updated_at"],
            )
            for name, row in existing.items()
            if name not in table_names
        ]
        if kept:
            spark.createDataFrame(
                kept,
                "tracker_id string, table_name string, rows_inserted bigint, start_date date, end_date date, year int, updated_at timestamp",
            ).unionByName(spark.table(f"{fq}.ingestion_tracker")).write.mode("overwrite").saveAsTable(
                f"{fq}.ingestion_tracker"
            )
    spark.createDataFrame(
        log_rows,
        "log_id string, tracker_id string, started_at timestamp, ended_at timestamp, starting_count bigint, "
        "ending_count bigint, start_date date, end_date date, year int, months int, pipeline string, status string",
    ).write.mode("append").saveAsTable(f"{fq}.ingestion_log")


def snapshot_oltp(spark, catalog: str, oltp_schema: str, pipeline: str = "oltp_snapshot") -> None:
    fq = spark_oltp.ensure_oltp_schema(spark, catalog, oltp_schema)
    lo, hi = _min_max_date(spark, fq, "customer_order", "order_ts")
    if lo is None:
        lo, hi = _min_max_date(spark, fq, "customer_transaction", "txn_date")
    snapshot_tables(
        spark,
        fq,
        OLTP_TABLES,
        start_date=lo or CAPACITY_START,
        end_date=hi or lo or CAPACITY_START,
        pipeline=pipeline,
        started_at=datetime.utcnow(),
    )


def _ensure_seed_customers(spark, fq: str) -> None:
    from pyspark.sql import functions as F

    if _count(spark, fq, "customer") > 0:
        return
    n_customers = 200
    customers = (
        spark.range(n_customers)
        .withColumn("customer_id", F.format_string("C%06d", F.col("id") + 1))
        .withColumn("customer_name", F.concat(F.lit("Customer "), F.col("id") + 1))
        .withColumn(
            "segment",
            F.element_at(F.array(*[F.lit(s) for s in spark_oltp.SEGMENTS]), (F.col("id") % 3 + 1).cast("int")),
        )
        .withColumn(
            "region",
            F.element_at(F.array(*[F.lit(s) for s in spark_oltp.REGIONS]), (F.col("id") % 5 + 1).cast("int")),
        )
        .withColumn("signup_date", F.lit(str(CAPACITY_START)).cast("date"))
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
            F.element_at(F.array(*[F.lit(s) for s in spark_oltp.ADDRESS_TYPES]), (F.col("addr_n") + 1).cast("int")),
        )
        .withColumn("line1", F.concat(F.lit((F.col("id") + 100).cast("string")), F.lit(" Market St")))
        .withColumn("city", F.concat(F.lit("City "), (F.col("customer_seq") % 50).cast("string")))
        .withColumn(
            "region",
            F.element_at(F.array(*[F.lit(s) for s in spark_oltp.REGIONS]), (F.col("customer_seq") % 5 + 1).cast("int")),
        )
        .withColumn("postal_code", F.format_string("%05d", (F.col("id") % 90000) + 10000))
        .withColumn("is_primary", F.col("addr_n") == 0)
        .drop("id", "customer_seq", "addr_n")
    )
    addresses.write.mode("overwrite").saveAsTable(f"{fq}.customer_address")
    accounts = (
        spark.range(n_customers * len(ACCOUNT_PRODUCTS))
        .withColumn("customer_seq", (F.col("id") / len(ACCOUNT_PRODUCTS)).cast("int"))
        .withColumn("acct_n", (F.col("id") % len(ACCOUNT_PRODUCTS)).cast("int"))
        .withColumn("customer_id", F.format_string("C%06d", F.col("customer_seq") + 1))
        .withColumn("account_id", F.concat(F.col("customer_id"), F.lit("-ACCT"), F.col("acct_n")))
        .withColumn(
            "product",
            F.element_at(F.array(*[F.lit(s) for s in ACCOUNT_PRODUCTS]), (F.col("acct_n") + 1).cast("int")),
        )
        .withColumn("opened_date", F.lit(str(CAPACITY_START)).cast("date"))
        .withColumn("status", F.lit("open"))
        .drop("id", "customer_seq", "acct_n")
    )
    accounts.write.mode("overwrite").saveAsTable(f"{fq}.customer_account")


def generate_next_oltp(spark, catalog: str, oltp_schema: str, row_count: int = 100_000) -> dict:
    from pyspark.sql import functions as F

    fq = spark_oltp.ensure_oltp_schema(spark, catalog, oltp_schema)
    _ensure_tables(spark, fq)
    started = datetime.utcnow()
    n = max(1, min(int(row_count), 100_000))
    _ensure_seed_customers(spark, fq)
    n_customers = _count(spark, fq, "customer") or 1
    cursor = _latest_end(spark, fq, ("customer_order", "customer_transaction"))
    next_start = CAPACITY_START if cursor is None else cursor + timedelta(days=1)
    if next_start > CAPACITY_END:
        snapshot_tables(
            spark,
            fq,
            OLTP_TABLES,
            start_date=CAPACITY_END,
            end_date=CAPACITY_END,
            pipeline="oltp_next",
            started_at=started,
            status="caught_up",
        )
        return {
            "rows": 0,
            "orders": 0,
            "postings": 0,
            "start_date": str(CAPACITY_END),
            "end_date": str(CAPACITY_END),
            "year": CAPACITY_END.year,
            "status": "caught_up",
            "message": "No OLTP days left in the 18 Sep 2016-2026 window",
        }

    remaining = (CAPACITY_END - next_start).days + 1
    window_days = min(remaining, 30)
    last_end = next_start + timedelta(days=window_days - 1)
    n_orders = min(int(n * 0.7) or n, n)
    n_postings = max(0, n - n_orders)
    max_order = spark.sql(
        f"SELECT COALESCE(MAX(CAST(substring(order_id, 2) AS BIGINT)), 0) AS m FROM {fq}.customer_order"
    ).collect()[0]["m"]
    max_txn = spark.sql(
        f"SELECT COALESCE(MAX(CAST(substring(transaction_id, 2) AS BIGINT)), 0) AS m FROM {fq}.customer_transaction"
    ).collect()[0]["m"]

    new_orders = (
        spark.range(n_orders)
        .withColumn("seq", F.col("id") + int(max_order) + 1)
        .withColumn("customer_seq", (F.col("id") % n_customers).cast("int"))
        .withColumn("customer_id", F.format_string("C%06d", F.col("customer_seq") + 1))
        .withColumn("order_id", F.format_string("O%012d", F.col("seq")))
        .withColumn("day_off", (F.col("id") % window_days).cast("int"))
        .withColumn("order_ts", F.to_timestamp(F.date_add(F.lit(str(next_start)), F.col("day_off"))))
        .withColumn(
            "status",
            F.element_at(F.array(*[F.lit(s) for s in spark_oltp.STATUSES]), (F.col("id") % 5 + 1).cast("int")),
        )
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
        spark.range(n_orders * 3)
        .withColumn("order_off", (F.col("id") / 3).cast("long"))
        .withColumn("line_n", (F.col("id") % 3).cast("int"))
        .withColumn("seq", F.col("order_off") + int(max_order) + 1)
        .withColumn("order_id", F.format_string("O%012d", F.col("seq")))
        .withColumn("order_line_id", F.concat(F.col("order_id"), F.lit("-L"), F.col("line_n")))
        .withColumn("sku", F.format_string("SKU-%03d", (F.col("id") % 50 + 1).cast("int")))
        .withColumn("quantity", (F.col("id") % 4 + 1).cast("int"))
        .withColumn("unit_price", ((F.col("id") % 40) + 9.99).cast("decimal(10,2)"))
        .withColumn("line_amount", (F.col("quantity") * F.col("unit_price")).cast("decimal(12,2)"))
        .select("order_line_id", "order_id", "sku", "quantity", "unit_price", "line_amount")
    )
    lines.write.mode("append").saveAsTable(f"{fq}.customer_order_line")
    shipments = new_orders.filter(F.col("status").isin("shipped", "delivered", "paid")).select(
        F.concat(F.col("order_id"), F.lit("-S0")).alias("shipment_id"),
        "order_id",
        (F.col("order_ts") + F.expr("INTERVAL 2 DAYS")).alias("ship_ts"),
        F.element_at(
            F.array(*[F.lit(s) for s in spark_oltp.CARRIERS]), (F.abs(F.hash("order_id")) % 4 + 1).cast("int")
        ).alias("carrier"),
        F.concat(F.lit("TRK"), F.col("order_id")).alias("tracking_number"),
        F.lit("in_transit").alias("status"),
        F.col("shipping_address_id").alias("ship_address_id"),
    )
    shipments.write.mode("append").saveAsTable(f"{fq}.customer_order_shipment")

    type_codes = [item[0] for item in TRANSACTION_TYPES]
    counterparties = [item[0] for item in COUNTERPARTY_KINDS]
    postings = (
        spark.range(n_postings)
        .withColumn("seq", F.col("id") + int(max_txn) + 1)
        .withColumn("customer_seq", (F.col("id") % n_customers).cast("int"))
        .withColumn("acct_n", (F.col("id") % len(ACCOUNT_PRODUCTS)).cast("int"))
        .withColumn("customer_id", F.format_string("C%06d", F.col("customer_seq") + 1))
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
        .withColumn("day_off", (F.col("id") % window_days).cast("int"))
        .withColumn("txn_ts", F.to_timestamp(F.date_add(F.lit(str(next_start)), F.col("day_off"))))
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
    postings.write.mode("append").saveAsTable(f"{fq}.customer_transaction")
    snapshot_tables(
        spark,
        fq,
        OLTP_TABLES,
        start_date=next_start,
        end_date=last_end,
        pipeline="oltp_next",
        started_at=started,
    )
    return {
        "rows": n_orders + n_postings,
        "orders": n_orders,
        "postings": n_postings,
        "start_date": str(next_start),
        "end_date": str(last_end),
        "year": last_end.year,
        "status": "ok",
        "message": f"appended {n_orders} orders and {n_postings} postings",
    }


def _refresh_dims(spark, catalog: str, star_schema: str, oltp_schema: str) -> None:
    from ecommerce_genie_ontology.adapter_databricks.spark import etl as spark_etl

    spark_etl.refresh_star_dims(spark, catalog, star_schema, oltp_schema)


def etl_next_months(
    spark,
    catalog: str,
    star_schema: str,
    oltp_schema: str,
    months: int = 3,
) -> dict:
    from pyspark.sql import functions as F

    months = max(1, min(12, int(months)))
    oltp = spark_oltp.ensure_oltp_schema(spark, catalog, oltp_schema)
    star = f"{catalog}.{star_schema}"
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {star}")
    _ensure_tables(spark, oltp)
    started = datetime.utcnow()

    oltp_end = _latest_end(spark, oltp, ("customer_order", "customer_transaction"))
    if oltp_end is None:
        _, oltp_end = _min_max_date(spark, oltp, "customer_order", "order_ts")
    if oltp_end is None:
        _, oltp_end = _min_max_date(spark, oltp, "customer_transaction", "txn_date")
    star_end = _latest_end(spark, oltp, STAR_TABLES)
    if star_end is None and _count(spark, star, "fact_sales"):
        row = spark.table(f"{star}.fact_sales").select(F.max("date_key").alias("d")).collect()[0]["d"]
        if row:
            text = str(int(row))
            star_end = date(int(text[0:4]), int(text[4:6]), int(text[6:8]))

    oltp_start, _ = _min_max_date(spark, oltp, "customer_order", "order_ts")
    if oltp_start is None:
        oltp_start, _ = _min_max_date(spark, oltp, "customer_transaction", "txn_date")
    window_start = (star_end + timedelta(days=1)) if star_end else (oltp_start or CAPACITY_START)
    wanted_end = add_months(window_start, months) - timedelta(days=1)
    available_end = oltp_end or window_start
    window_end = min(wanted_end, available_end, CAPACITY_END)
    if window_start > window_end or oltp_end is None:
        snapshot_tables(
            spark,
            oltp,
            STAR_TABLES,
            start_date=window_start,
            end_date=window_start,
            pipeline="star_next",
            started_at=started,
            months=months,
            status="caught_up",
        )
        return {
            "rows": 0,
            "months": months,
            "start_date": str(window_start),
            "end_date": str(window_start),
            "year": window_start.year,
            "status": "caught_up",
            "message": "No unused OLTP months left for star load",
        }

    lo = int(window_start.strftime("%Y%m%d"))
    hi = int(window_end.strftime("%Y%m%d"))
    _refresh_dims(spark, catalog, star_schema, oltp_schema)
    orders = spark.table(f"{oltp}.customer_order")
    lines = spark.table(f"{oltp}.customer_order_line")
    sales = (
        lines.join(orders, "order_id")
        .withColumn("date_key", F.date_format("order_ts", "yyyyMMdd").cast("int"))
        .filter((F.col("date_key") >= lo) & (F.col("date_key") <= hi))
        .withColumn("product_key", F.regexp_replace("sku", "SKU-", "").cast("int"))
        .withColumn("customer_key", F.regexp_replace("customer_id", "C", "").cast("int"))
        .withColumn("store_key", F.col("store_id"))
        .withColumn("revenue", F.col("line_amount"))
        .select(
            F.abs(F.hash("order_line_id")).cast("bigint").alias("order_id"),
            "date_key",
            "product_key",
            "customer_key",
            "store_key",
            "quantity",
            "unit_price",
            "revenue",
        )
    )
    sales.write.mode("append").saveAsTable(f"{star}.fact_sales")
    returns = (
        orders.filter(F.col("status") == "cancelled")
        .withColumn("date_key", F.date_format("order_ts", "yyyyMMdd").cast("int"))
        .filter((F.col("date_key") >= lo) & (F.col("date_key") <= hi))
        .select(
            F.abs(F.hash("order_id")).cast("bigint").alias("return_id"),
            F.abs(F.hash(F.concat(F.lit("ord"), F.col("order_id")))).cast("bigint").alias("order_id"),
            "date_key",
            F.regexp_replace("customer_id", "C", "").cast("int").alias("customer_key"),
            F.col("order_amount").alias("return_amount"),
        )
    )
    returns.write.mode("append").saveAsTable(f"{star}.fact_returns")
    if spark.catalog.tableExists(f"{oltp}.customer_transaction"):
        types = spark.table(f"{star}.dim_transaction_type").select("type_key", "type_code")
        cps = spark.table(f"{star}.dim_counterparty").select("counterparty_key", "counterparty_id")
        txns = (
            spark.table(f"{oltp}.customer_transaction")
            .join(types, "type_code", "left")
            .join(cps, "counterparty_id", "left")
            .withColumn("date_key", F.date_format("txn_ts", "yyyyMMdd").cast("int"))
            .filter((F.col("date_key") >= lo) & (F.col("date_key") <= hi))
            .withColumn("customer_key", F.regexp_replace("customer_id", "C", "").cast("int"))
            .withColumn("acct_n", F.regexp_extract("account_id", r"ACCT(\d+)$", 1).cast("int"))
            .withColumn("account_key", F.col("customer_key") * len(ACCOUNT_PRODUCTS) + F.col("acct_n"))
            .select(
                "transaction_id",
                "date_key",
                "customer_key",
                "account_key",
                "type_key",
                "counterparty_key",
                "amount",
                "balance_before",
                "balance_after",
            )
        )
        txns.write.mode("append").saveAsTable(f"{star}.fact_transaction")

    snapshot_tables(
        spark,
        oltp,
        STAR_TABLES,
        start_date=window_start,
        end_date=window_end,
        pipeline="star_next",
        started_at=started,
        months=months,
    )
    rows = _count(spark, star, "fact_sales") + _count(spark, star, "fact_transaction")
    return {
        "rows": rows,
        "months": months,
        "start_date": str(window_start),
        "end_date": str(window_end),
        "year": window_end.year,
        "status": "ok",
        "message": f"loaded star window {window_start} to {window_end}",
    }
