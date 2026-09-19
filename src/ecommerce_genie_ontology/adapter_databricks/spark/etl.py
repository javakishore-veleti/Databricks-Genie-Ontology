from __future__ import annotations

from datetime import datetime


def etl_historical(spark, catalog: str, star_schema: str, oltp_schema: str) -> None:
    from pyspark.sql import functions as F

    oltp = f"{catalog}.{oltp_schema}"
    star = f"{catalog}.{star_schema}"
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {star}")
    customers = spark.table(f"{oltp}.customer").select(
        F.regexp_replace("customer_id", "C", "").cast("int").alias("customer_key"),
        "customer_name",
        "segment",
        "region",
        "signup_date",
    )
    customers.write.mode("overwrite").saveAsTable(f"{star}.dim_customer")

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
    inventory = products.select("product_key", F.lit(1000).cast("int").alias("stock_on_hand"))
    inventory.write.mode("overwrite").saveAsTable(f"{star}.fact_inventory")
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


def etl_cdc(spark, catalog: str, star_schema: str, oltp_schema: str) -> dict[str, int]:
    from pyspark.sql import functions as F

    oltp = f"{catalog}.{oltp_schema}"
    star = f"{catalog}.{star_schema}"
    spark.sql(f"CREATE TABLE IF NOT EXISTS {oltp}._cdc_watermark (table_name STRING, version BIGINT, updated_at TIMESTAMP) USING DELTA")
    current = spark.sql(f"DESCRIBE HISTORY {oltp}.customer_order").select(F.max("version").alias("v")).collect()[0]["v"] or 0
    rows = spark.sql(
        f"SELECT COALESCE(MAX(version), 0) AS v FROM {oltp}._cdc_watermark WHERE table_name = 'customer_order'"
    ).collect()
    last = int(rows[0]["v"] or 0) if rows else 0
    if current <= last:
        return {"new_versions": 0, "rows": 0}
    changes = spark.sql(
        f"SELECT * FROM table_changes('{oltp}.customer_order', {int(last)}, {int(current)}) "
        "WHERE _change_type IN ('insert', 'update_postimage')"
    )
    count = changes.count()
    if count:
        lines = spark.table(f"{oltp}.customer_order_line")
        facts = (
            lines.join(changes.select("order_id", "customer_id", "order_ts", "store_id").dropDuplicates(["order_id"]), "order_id")
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
    spark.createDataFrame(
        [("customer_order", int(current), datetime.utcnow())],
        "table_name string, version bigint, updated_at timestamp",
    ).write.mode("overwrite").saveAsTable(f"{oltp}._cdc_watermark")
    return {"new_versions": int(current - last), "rows": count}
