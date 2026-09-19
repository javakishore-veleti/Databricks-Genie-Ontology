from __future__ import annotations

from datetime import date, datetime

from ecommerce_genie_ontology.common.constants.schema_ddl import (
    dim_counterparty_seed,
    dim_transaction_type_seed,
    funds_star_statements,
)
from ecommerce_genie_ontology.common.constants.transaction_types import ACCOUNT_PRODUCTS


def etl_historical(spark, catalog: str, star_schema: str, oltp_schema: str) -> None:
    from pyspark.sql import functions as F

    oltp = f"{catalog}.{oltp_schema}"
    star = f"{catalog}.{star_schema}"
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {star}")
    for sql in funds_star_statements(star):
        spark.sql(sql)
    spark.sql(dim_transaction_type_seed(star))
    spark.sql(dim_counterparty_seed(star))

    start = date(2016, 9, 18)
    end = date(2026, 9, 18)
    n_days = (end - start).days + 1
    dim_date = (
        spark.range(n_days)
        .withColumn("calendar_date", F.date_add(F.lit(str(start)), F.col("id").cast("int")))
        .withColumn("date_key", F.date_format("calendar_date", "yyyyMMdd").cast("int"))
        .withColumn("year", F.year("calendar_date"))
        .withColumn("quarter", F.quarter("calendar_date"))
        .withColumn("month", F.month("calendar_date"))
        .withColumn("month_name", F.date_format("calendar_date", "MMMM"))
        .withColumn("day_of_week", F.date_format("calendar_date", "EEEE"))
        .withColumn("is_weekend", F.dayofweek("calendar_date").isin(1, 7))
        .select(
            "date_key",
            "calendar_date",
            "year",
            "quarter",
            "month",
            "month_name",
            "day_of_week",
            "is_weekend",
        )
    )
    dim_date.write.mode("overwrite").saveAsTable(f"{star}.dim_date")

    customers = spark.table(f"{oltp}.customer").select(
        F.regexp_replace("customer_id", "C", "").cast("int").alias("customer_key"),
        "customer_name",
        "segment",
        "region",
        "signup_date",
    )
    customers.write.mode("overwrite").saveAsTable(f"{star}.dim_customer")

    if spark.catalog.tableExists(f"{oltp}.customer_account"):
        accounts = (
            spark.table(f"{oltp}.customer_account")
            .withColumn("customer_key", F.regexp_replace("customer_id", "C", "").cast("int"))
            .withColumn("acct_n", F.regexp_extract("account_id", r"ACCT(\d+)$", 1).cast("int"))
            .withColumn("account_key", F.col("customer_key") * len(ACCOUNT_PRODUCTS) + F.col("acct_n"))
            .select("account_key", "account_id", "customer_key", "product", "opened_date")
        )
        accounts.write.mode("overwrite").saveAsTable(f"{star}.dim_account")

    products = (
        spark.table(f"{oltp}.customer_order_line")
        .select("sku")
        .distinct()
        .withColumn("product_key", F.regexp_replace("sku", "SKU-", "").cast("int"))
        .withColumn("product_name", F.concat(F.lit("Product "), "sku"))
        .withColumn("category", F.lit("General"))
        .withColumn("brand", F.lit("Northwind"))
        .withColumn("unit_cost", F.lit(5.00).cast("decimal(10,2)"))
        .select("product_key", F.col("sku"), "product_name", "category", "brand", "unit_cost")
    )
    products.write.mode("overwrite").saveAsTable(f"{star}.dim_product")

    orders = spark.table(f"{oltp}.customer_order")
    lines = spark.table(f"{oltp}.customer_order_line")
    facts = (
        lines.join(orders, "order_id")
        .withColumn("date_key", F.date_format("order_ts", "yyyyMMdd").cast("int"))
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
    facts.write.mode("overwrite").saveAsTable(f"{star}.fact_sales")
    returns = (
        orders.filter(F.col("status") == "cancelled")
        .select(
            F.abs(F.hash("order_id")).cast("bigint").alias("return_id"),
            F.abs(F.hash(F.concat(F.lit("ord"), F.col("order_id")))).cast("bigint").alias("order_id"),
            F.regexp_replace("customer_id", "C", "").cast("int").alias("customer_key"),
            F.col("order_amount").alias("return_amount"),
        )
    )
    returns.write.mode("overwrite").saveAsTable(f"{star}.fact_returns")
    inventory = products.select(
        F.lit(int(date.today().strftime("%Y%m%d"))).alias("snapshot_date_key"),
        "product_key",
        F.lit(1).cast("int").alias("store_key"),
        F.lit(1000).cast("int").alias("stock_on_hand"),
        F.lit(50).cast("int").alias("stock_received"),
    )
    inventory.write.mode("overwrite").saveAsTable(f"{star}.fact_inventory")

    stores = (
        orders.select(F.col("store_id").alias("store_key"))
        .distinct()
        .withColumn("store_name", F.concat(F.lit("Store "), F.lpad(F.col("store_key").cast("string"), 2, "0")))
        .withColumn("region", F.lit("West"))
        .withColumn("channel", F.when(F.col("store_key") <= 5, F.lit("Online")).otherwise(F.lit("In-Store")))
    )
    stores.write.mode("overwrite").saveAsTable(f"{star}.dim_store")

    if spark.catalog.tableExists(f"{oltp}.customer_transaction"):
        types = spark.table(f"{star}.dim_transaction_type").select("type_key", "type_code")
        cps = spark.table(f"{star}.dim_counterparty").select("counterparty_key", "counterparty_id")
        facts_txn = (
            spark.table(f"{oltp}.customer_transaction")
            .join(types, "type_code", "left")
            .join(cps, "counterparty_id", "left")
            .withColumn("date_key", F.date_format("txn_ts", "yyyyMMdd").cast("int"))
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
        facts_txn.write.mode("overwrite").saveAsTable(f"{star}.fact_transaction")
    spark.sql(
        f"""
CREATE OR REPLACE TABLE {star}._etl_run (
  pipeline STRING,
  ran_at TIMESTAMP,
  note STRING
)
"""
    )
    spark.createDataFrame(
        [("historical", datetime.utcnow(), f"loaded from {oltp}")],
        "pipeline string, ran_at timestamp, note string",
    ).write.mode("append").saveAsTable(f"{star}._etl_run")


def _watermark(spark, oltp: str, table_name: str) -> int:
    from pyspark.sql import functions as F

    rows = spark.sql(
        f"SELECT COALESCE(MAX(version), 0) AS v FROM {oltp}._cdc_watermark WHERE table_name = '{table_name}'"
    ).collect()
    return int(rows[0]["v"] or 0) if rows else 0


def etl_cdc(spark, catalog: str, star_schema: str, oltp_schema: str) -> dict[str, int]:
    from pyspark.sql import functions as F

    oltp = f"{catalog}.{oltp_schema}"
    star = f"{catalog}.{star_schema}"
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS {oltp}._cdc_watermark "
        "(table_name STRING, version BIGINT, updated_at TIMESTAMP) USING DELTA"
    )
    marks: list[tuple] = []
    count = 0
    current = spark.sql(f"DESCRIBE HISTORY {oltp}.customer_order").select(F.max("version").alias("v")).collect()[0]["v"] or 0
    last = _watermark(spark, oltp, "customer_order")
    if current > last:
        changes = spark.sql(
            f"SELECT * FROM table_changes('{oltp}.customer_order', {int(last)}, {int(current)}) "
            "WHERE _change_type IN ('insert', 'update_postimage')"
        )
        count = changes.count()
        if count:
            lines = spark.table(f"{oltp}.customer_order_line")
            facts = (
                lines.join(
                    changes.select("order_id", "customer_id", "order_ts", "store_id").dropDuplicates(["order_id"]),
                    "order_id",
                )
                .withColumn("date_key", F.date_format("order_ts", "yyyyMMdd").cast("int"))
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
            facts.write.mode("append").saveAsTable(f"{star}.fact_sales")
        marks.append(("customer_order", int(current), datetime.utcnow()))

    txn_rows = 0
    if spark.catalog.tableExists(f"{oltp}.customer_transaction"):
        txn_current = (
            spark.sql(f"DESCRIBE HISTORY {oltp}.customer_transaction").select(F.max("version").alias("v")).collect()[0]["v"]
            or 0
        )
        txn_last = _watermark(spark, oltp, "customer_transaction")
        if txn_current > txn_last:
            txn_changes = spark.sql(
                f"SELECT * FROM table_changes('{oltp}.customer_transaction', {int(txn_last)}, {int(txn_current)}) "
                "WHERE _change_type IN ('insert', 'update_postimage')"
            )
            txn_rows = txn_changes.count()
            if txn_rows:
                types = spark.table(f"{star}.dim_transaction_type").select("type_key", "type_code")
                cps = spark.table(f"{star}.dim_counterparty").select("counterparty_key", "counterparty_id")
                txn_facts = (
                    txn_changes.join(types, "type_code", "left")
                    .join(cps, "counterparty_id", "left")
                    .withColumn("date_key", F.date_format("txn_ts", "yyyyMMdd").cast("int"))
                    .withColumn("customer_key", F.regexp_replace("customer_id", "C", "").cast("int"))
                    .withColumn("acct_n", F.regexp_extract("account_id", r"ACCT(\d+)$", 1).cast("int"))
                    .withColumn("account_key", F.col("customer_key") * 4 + F.col("acct_n"))
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
                txn_facts.write.mode("append").saveAsTable(f"{star}.fact_transaction")
            marks.append(("customer_transaction", int(txn_current), datetime.utcnow()))

    if marks:
        existing = spark.table(f"{oltp}._cdc_watermark").filter(
            ~F.col("table_name").isin([item[0] for item in marks])
        )
        spark.createDataFrame(
            marks,
            "table_name string, version bigint, updated_at timestamp",
        ).unionByName(existing).write.mode("overwrite").saveAsTable(f"{oltp}._cdc_watermark")
    return {"new_versions": len(marks), "rows": count + txn_rows}
