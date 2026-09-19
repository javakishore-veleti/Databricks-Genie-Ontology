"""Unity Catalog DDL for OLTP and funds-movement star tables."""

from __future__ import annotations

from ecommerce_genie_ontology.common.constants.transaction_types import (
    COUNTERPARTY_KINDS,
    TRANSACTION_TYPES,
)


def oltp_statements(fq: str) -> list[str]:
    return [
        f"CREATE SCHEMA IF NOT EXISTS {fq}",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.customer (
  customer_id STRING NOT NULL,
  customer_name STRING,
  segment STRING,
  region STRING,
  signup_date DATE,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
) USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true)
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.customer_address (
  address_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  address_type STRING,
  line1 STRING,
  city STRING,
  region STRING,
  postal_code STRING,
  is_primary BOOLEAN
) USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true)
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.customer_account (
  account_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  product STRING,
  opened_date DATE,
  status STRING
) USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true)
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.customer_order (
  order_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  order_ts TIMESTAMP,
  status STRING,
  store_id INT,
  billing_address_id STRING,
  shipping_address_id STRING,
  order_amount DECIMAL(12,2)
) USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true)
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.customer_order_line (
  order_line_id STRING NOT NULL,
  order_id STRING NOT NULL,
  sku STRING,
  quantity INT,
  unit_price DECIMAL(10,2),
  line_amount DECIMAL(12,2)
) USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true)
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.customer_order_shipment (
  shipment_id STRING NOT NULL,
  order_id STRING NOT NULL,
  ship_ts TIMESTAMP,
  carrier STRING,
  tracking_number STRING,
  status STRING,
  ship_address_id STRING
) USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true)
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.customer_transaction (
  transaction_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  account_id STRING NOT NULL,
  counterparty_id STRING,
  type_code STRING,
  txn_ts TIMESTAMP,
  txn_date DATE,
  amount DECIMAL(12,2),
  balance_before DECIMAL(14,2),
  balance_after DECIMAL(14,2),
  status STRING
) USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true)
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.entity_link (
  src_type STRING,
  src_id STRING,
  rel STRING,
  dst_type STRING,
  dst_id STRING,
  weight DOUBLE
) USING DELTA
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}._cdc_watermark (
  table_name STRING,
  version BIGINT,
  updated_at TIMESTAMP
) USING DELTA
""",
        *ingest_statements(fq),
        *analytics_statements(fq),
    ]


def ingest_statements(fq: str) -> list[str]:
    return [
        f"""
CREATE TABLE IF NOT EXISTS {fq}.ingestion_tracker (
  tracker_id STRING NOT NULL,
  table_name STRING NOT NULL,
  rows_inserted BIGINT,
  start_date DATE,
  end_date DATE,
  year INT,
  updated_at TIMESTAMP
) USING DELTA
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.ingestion_log (
  log_id STRING NOT NULL,
  tracker_id STRING NOT NULL,
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  starting_count BIGINT,
  ending_count BIGINT,
  start_date DATE,
  end_date DATE,
  year INT,
  months INT,
  pipeline STRING,
  status STRING
) USING DELTA
""",
    ]


def sales_star_statements(fq: str) -> list[str]:
    return [
        f"""
CREATE TABLE IF NOT EXISTS {fq}.dim_date (
  date_key      INT     NOT NULL COMMENT 'Surrogate key, YYYYMMDD integer',
  calendar_date DATE    NOT NULL COMMENT 'Calendar date',
  year          INT              COMMENT 'Calendar year',
  quarter       INT              COMMENT 'Calendar quarter (1-4)',
  month         INT              COMMENT 'Calendar month number (1-12)',
  month_name    STRING           COMMENT 'Month name, e.g. January',
  day_of_week   STRING           COMMENT 'Day of week name, e.g. Monday',
  is_weekend    BOOLEAN          COMMENT 'True if the date falls on Saturday or Sunday'
)
COMMENT 'Date dimension, one row per calendar day. Used to conform all fact tables to a shared calendar.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.dim_product (
  product_key  INT            NOT NULL COMMENT 'Surrogate key for product',
  sku          STRING         NOT NULL COMMENT 'Business key / stock keeping unit',
  product_name STRING                  COMMENT 'Product display name',
  category     STRING                  COMMENT 'Merchandising category, e.g. Electronics, Apparel',
  brand        STRING                  COMMENT 'Brand name',
  unit_cost    DECIMAL(10,2)           COMMENT 'Wholesale unit cost in USD'
)
COMMENT 'Product dimension.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.dim_customer (
  customer_key  INT    NOT NULL COMMENT 'Surrogate key for customer',
  customer_name STRING          COMMENT 'Customer display name',
  segment       STRING          COMMENT 'Customer segment: Consumer, Small Business, or Enterprise',
  region        STRING          COMMENT 'Sales region the customer belongs to',
  signup_date   DATE            COMMENT 'Date the customer first registered'
)
COMMENT 'Customer dimension.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.dim_store (
  store_key  INT    NOT NULL COMMENT 'Surrogate key for store / sales channel',
  store_name STRING          COMMENT 'Store or channel display name',
  region     STRING          COMMENT 'Region the store operates in',
  channel    STRING          COMMENT 'Sales channel: Online or In-Store'
)
COMMENT 'Store / sales channel dimension.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.fact_sales (
  order_id     BIGINT        NOT NULL COMMENT 'Order line surrogate key',
  date_key     INT           NOT NULL COMMENT 'FK to dim_date.date_key, date the order was placed',
  product_key  INT           NOT NULL COMMENT 'FK to dim_product.product_key',
  customer_key INT           NOT NULL COMMENT 'FK to dim_customer.customer_key',
  store_key    INT           NOT NULL COMMENT 'FK to dim_store.store_key',
  quantity     INT                    COMMENT 'Units sold on this order line',
  unit_price   DECIMAL(10,2)          COMMENT 'Realized selling price per unit, in USD',
  revenue      DECIMAL(12,2)          COMMENT 'quantity * unit_price - gross revenue in USD for this line'
)
COMMENT 'Sales fact table, one row per order line item. Grain: one order line.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.fact_returns (
  return_id     BIGINT        NOT NULL COMMENT 'Return line surrogate key',
  order_id      BIGINT        NOT NULL COMMENT 'FK to fact_sales.order_id, the original order line being returned',
  date_key      INT           NOT NULL COMMENT 'FK to dim_date.date_key, date of the return',
  product_key   INT           NOT NULL COMMENT 'FK to dim_product.product_key',
  customer_key  INT           NOT NULL COMMENT 'FK to dim_customer.customer_key',
  quantity      INT                    COMMENT 'Units returned',
  return_amount DECIMAL(12,2)          COMMENT 'Refunded amount in USD',
  return_reason STRING                 COMMENT 'Reason code for the return, e.g. Defective, Wrong Item'
)
COMMENT 'Returns fact table, one row per returned order line. Grain: one return line.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.fact_inventory (
  snapshot_date_key INT NOT NULL COMMENT 'FK to dim_date.date_key, inventory snapshot date (first of month)',
  product_key       INT NOT NULL COMMENT 'FK to dim_product.product_key',
  store_key         INT NOT NULL COMMENT 'FK to dim_store.store_key',
  stock_on_hand     INT          COMMENT 'Units on hand at the snapshot date',
  stock_received    INT          COMMENT 'Units received into stock since the prior snapshot'
)
COMMENT 'Monthly inventory snapshot fact table. Grain: one product/store/month.'
""",
    ]


def analytics_statements(fq: str) -> list[str]:
    return [
        f"""
CREATE TABLE IF NOT EXISTS {fq}.analytics_log (
  analytics_id STRING NOT NULL,
  requesting_user STRING,
  customer_count BIGINT,
  start_date DATE,
  end_date DATE,
  requested_at TIMESTAMP,
  analytics_start_at TIMESTAMP,
  analytics_end_at TIMESTAMP,
  status STRING
) USING DELTA
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.analytics_log_customer (
  analytics_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  order_count BIGINT,
  order_line_count BIGINT,
  shipment_count BIGINT,
  posting_count BIGINT,
  address_count BIGINT,
  account_count BIGINT,
  fact_sales_count BIGINT,
  fact_returns_count BIGINT,
  fact_inventory_count BIGINT,
  fact_transaction_count BIGINT,
  analytics_outcome STRING,
  analytics_log_info STRING,
  updated_at TIMESTAMP
) USING DELTA
""",
    ]


def funds_star_statements(fq: str) -> list[str]:
    return [
        f"""
CREATE TABLE IF NOT EXISTS {fq}.dim_transaction_type (
  type_key INT NOT NULL,
  type_code STRING NOT NULL,
  class STRING,
  direction STRING,
  same_bank BOOLEAN,
  same_account BOOLEAN
)
COMMENT 'Funds-movement type. One row per type_code. Do not add dim_wire or dim_cash.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.dim_account (
  account_key INT NOT NULL,
  account_id STRING NOT NULL,
  customer_key INT,
  product STRING,
  opened_date DATE
)
COMMENT 'Customer account. Checking, CD, credit card, or brokerage.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.dim_counterparty (
  counterparty_key INT NOT NULL,
  counterparty_id STRING NOT NULL,
  name STRING,
  kind STRING
)
COMMENT 'Other bank, same bank, brokerage, or card issuer on a posting.'
""",
        f"""
CREATE TABLE IF NOT EXISTS {fq}.fact_transaction (
  transaction_id STRING NOT NULL,
  date_key INT NOT NULL,
  customer_key INT NOT NULL,
  account_key INT,
  type_key INT,
  counterparty_key INT,
  amount DECIMAL(12,2),
  balance_before DECIMAL(14,2),
  balance_after DECIMAL(14,2)
)
COMMENT 'Funds-movement fact. Each row is one posting.'
""",
    ]


def dim_transaction_type_seed(fq: str) -> str:
    rows = ",\n  ".join(
        f"({i}, '{code}', '{klass}', '{direction}', {str(same_bank).lower()}, {str(same_account).lower()})"
        for i, (code, klass, direction, same_bank, same_account) in enumerate(TRANSACTION_TYPES, start=1)
    )
    return f"""
CREATE OR REPLACE TABLE {fq}.dim_transaction_type AS
SELECT * FROM VALUES
  {rows}
AS t(type_key, type_code, class, direction, same_bank, same_account)
"""


def dim_counterparty_seed(fq: str) -> str:
    rows = ",\n  ".join(
        f"({i}, '{cid}', '{kind.replace('_', ' ')}', '{kind}')"
        for i, (cid, kind) in enumerate(COUNTERPARTY_KINDS, start=1)
    )
    return f"""
CREATE OR REPLACE TABLE {fq}.dim_counterparty AS
SELECT * FROM VALUES
  {rows}
AS t(counterparty_key, counterparty_id, name, kind)
"""
