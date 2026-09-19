from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from ecommerce_genie_ontology.common.constants.schema_ddl import (
    dim_counterparty_seed,
    dim_region_seed,
    dim_transaction_type_seed,
    fraud_star_statements,
    funds_star_statements,
    oltp_statements,
    sales_star_statements,
)
from ecommerce_genie_ontology.common.interfaces.provision import ProvisionWorkspaceFacade


def _grant_catalog(facade: ProvisionWorkspaceFacade) -> None:
    catalog = facade.catalog
    facade.sql_ok(f"GRANT USE CATALOG ON CATALOG {catalog} TO `account users`")
    facade.sql_ok(f"GRANT USE SCHEMA ON CATALOG {catalog} TO `account users`")
    facade.sql_ok(f"GRANT SELECT ON CATALOG {catalog} TO `account users`")
    facade.sql_ok(f"GRANT BROWSE ON CATALOG {catalog} TO `account users`")
    for email in facade.admin_emails:
        principal = email.replace("`", "")
        facade.sql_ok(f"GRANT ALL PRIVILEGES ON CATALOG {catalog} TO `{principal}`")


def _create_tables(facade: ProvisionWorkspaceFacade) -> None:
    fq = facade.fq_schema
    facade.sql(
        f"""
CREATE CATALOG IF NOT EXISTS {facade.catalog}
COMMENT 'Genie One + Genie Ontology demo catalog (Northwind Retail sales analytics)'
"""
    )
    _grant_catalog(facade)
    facade.share_catalog()
    facade.sql(
        f"""
CREATE SCHEMA IF NOT EXISTS {fq}
COMMENT 'Star schema: fraud-current order events plus STALE sales/inventory merchandising facts'
"""
    )
    for statement in oltp_statements(facade.fq_oltp):
        facade.sql(statement)
    for statement in sales_star_statements(fq):
        facade.sql(statement)
    for statement in fraud_star_statements(fq):
        facade.sql(statement)
    for statement in funds_star_statements(fq):
        facade.sql(statement)
    facade.sql(dim_transaction_type_seed(fq))
    facade.sql(dim_counterparty_seed(fq))
    facade.sql(dim_region_seed(fq))
    facade.sql(f"USE CATALOG {facade.catalog}")
    facade.sql(f"USE SCHEMA {facade.schema_name}")
    print("Tables created.")


def _add_constraints(facade: ProvisionWorkspaceFacade) -> None:
    fq = facade.fq_schema
    oltp = facade.fq_oltp
    pk_statements = [
        f"ALTER TABLE {fq}.dim_date     ADD CONSTRAINT pk_dim_date     PRIMARY KEY (date_key)",
        f"ALTER TABLE {fq}.dim_product  ADD CONSTRAINT pk_dim_product  PRIMARY KEY (product_key)",
        f"ALTER TABLE {fq}.dim_customer ADD CONSTRAINT pk_dim_customer PRIMARY KEY (customer_key)",
        f"ALTER TABLE {fq}.dim_store    ADD CONSTRAINT pk_dim_store    PRIMARY KEY (store_key)",
        f"ALTER TABLE {fq}.fact_sales   ADD CONSTRAINT pk_fact_sales   PRIMARY KEY (order_id)",
        f"ALTER TABLE {fq}.fact_returns ADD CONSTRAINT pk_fact_returns PRIMARY KEY (return_id)",
        (
            f"ALTER TABLE {fq}.fact_inventory ADD CONSTRAINT pk_fact_inventory "
            "PRIMARY KEY (snapshot_date_key, product_key, store_key)"
        ),
        f"ALTER TABLE {fq}.dim_transaction_type ADD CONSTRAINT pk_dim_transaction_type PRIMARY KEY (type_key)",
        f"ALTER TABLE {fq}.dim_account ADD CONSTRAINT pk_dim_account PRIMARY KEY (account_key)",
        f"ALTER TABLE {fq}.dim_counterparty ADD CONSTRAINT pk_dim_counterparty PRIMARY KEY (counterparty_key)",
        f"ALTER TABLE {fq}.fact_transaction ADD CONSTRAINT pk_fact_transaction PRIMARY KEY (transaction_id)",
        f"ALTER TABLE {fq}.dim_region ADD CONSTRAINT pk_dim_region PRIMARY KEY (region_key)",
        f"ALTER TABLE {fq}.dim_address ADD CONSTRAINT pk_dim_address PRIMARY KEY (address_key)",
        f"ALTER TABLE {fq}.fact_order_event ADD CONSTRAINT pk_fact_order_event PRIMARY KEY (order_id)",
        f"ALTER TABLE {oltp}.ingestion_tracker ADD CONSTRAINT pk_ingestion_tracker PRIMARY KEY (tracker_id)",
        f"ALTER TABLE {oltp}.ingestion_log ADD CONSTRAINT pk_ingestion_log PRIMARY KEY (log_id)",
        f"ALTER TABLE {oltp}.analytics_log ADD CONSTRAINT pk_analytics_log PRIMARY KEY (analytics_id)",
        (
            f"ALTER TABLE {oltp}.analytics_log_customer ADD CONSTRAINT pk_analytics_log_customer "
            "PRIMARY KEY (analytics_id, customer_id)"
        ),
    ]
    fk_statements = [
        f"ALTER TABLE {fq}.fact_sales ADD CONSTRAINT fk_sales_date FOREIGN KEY (date_key) REFERENCES {fq}.dim_date (date_key)",
        f"ALTER TABLE {fq}.fact_sales ADD CONSTRAINT fk_sales_product FOREIGN KEY (product_key) REFERENCES {fq}.dim_product (product_key)",
        f"ALTER TABLE {fq}.fact_sales ADD CONSTRAINT fk_sales_customer FOREIGN KEY (customer_key) REFERENCES {fq}.dim_customer (customer_key)",
        f"ALTER TABLE {fq}.fact_sales ADD CONSTRAINT fk_sales_store FOREIGN KEY (store_key) REFERENCES {fq}.dim_store (store_key)",
        f"ALTER TABLE {fq}.fact_returns ADD CONSTRAINT fk_returns_order FOREIGN KEY (order_id) REFERENCES {fq}.fact_sales (order_id)",
        f"ALTER TABLE {fq}.fact_returns ADD CONSTRAINT fk_returns_date FOREIGN KEY (date_key) REFERENCES {fq}.dim_date (date_key)",
        f"ALTER TABLE {fq}.fact_returns ADD CONSTRAINT fk_returns_product FOREIGN KEY (product_key) REFERENCES {fq}.dim_product (product_key)",
        f"ALTER TABLE {fq}.fact_returns ADD CONSTRAINT fk_returns_customer FOREIGN KEY (customer_key) REFERENCES {fq}.dim_customer (customer_key)",
        f"ALTER TABLE {fq}.fact_inventory ADD CONSTRAINT fk_inventory_date FOREIGN KEY (snapshot_date_key) REFERENCES {fq}.dim_date (date_key)",
        f"ALTER TABLE {fq}.fact_inventory ADD CONSTRAINT fk_inventory_product FOREIGN KEY (product_key) REFERENCES {fq}.dim_product (product_key)",
        f"ALTER TABLE {fq}.fact_inventory ADD CONSTRAINT fk_inventory_store FOREIGN KEY (store_key) REFERENCES {fq}.dim_store (store_key)",
        f"ALTER TABLE {fq}.fact_transaction ADD CONSTRAINT fk_txn_date FOREIGN KEY (date_key) REFERENCES {fq}.dim_date (date_key)",
        f"ALTER TABLE {fq}.fact_transaction ADD CONSTRAINT fk_txn_customer FOREIGN KEY (customer_key) REFERENCES {fq}.dim_customer (customer_key)",
        f"ALTER TABLE {fq}.fact_transaction ADD CONSTRAINT fk_txn_account FOREIGN KEY (account_key) REFERENCES {fq}.dim_account (account_key)",
        f"ALTER TABLE {fq}.fact_transaction ADD CONSTRAINT fk_txn_type FOREIGN KEY (type_key) REFERENCES {fq}.dim_transaction_type (type_key)",
        f"ALTER TABLE {fq}.fact_transaction ADD CONSTRAINT fk_txn_cp FOREIGN KEY (counterparty_key) REFERENCES {fq}.dim_counterparty (counterparty_key)",
        f"ALTER TABLE {fq}.dim_address ADD CONSTRAINT fk_address_customer FOREIGN KEY (customer_key) REFERENCES {fq}.dim_customer (customer_key)",
        f"ALTER TABLE {fq}.dim_address ADD CONSTRAINT fk_address_region FOREIGN KEY (region_key) REFERENCES {fq}.dim_region (region_key)",
        f"ALTER TABLE {fq}.fact_order_event ADD CONSTRAINT fk_order_event_date FOREIGN KEY (date_key) REFERENCES {fq}.dim_date (date_key)",
        f"ALTER TABLE {fq}.fact_order_event ADD CONSTRAINT fk_order_event_customer FOREIGN KEY (customer_key) REFERENCES {fq}.dim_customer (customer_key)",
        f"ALTER TABLE {fq}.fact_order_event ADD CONSTRAINT fk_order_event_store FOREIGN KEY (store_key) REFERENCES {fq}.dim_store (store_key)",
        f"ALTER TABLE {fq}.fact_order_event ADD CONSTRAINT fk_order_event_bill_addr FOREIGN KEY (billing_address_key) REFERENCES {fq}.dim_address (address_key)",
        f"ALTER TABLE {fq}.fact_order_event ADD CONSTRAINT fk_order_event_ship_addr FOREIGN KEY (shipping_address_key) REFERENCES {fq}.dim_address (address_key)",
        f"ALTER TABLE {fq}.fact_order_event ADD CONSTRAINT fk_order_event_bill_region FOREIGN KEY (billing_region_key) REFERENCES {fq}.dim_region (region_key)",
        f"ALTER TABLE {fq}.fact_order_event ADD CONSTRAINT fk_order_event_ship_region FOREIGN KEY (shipping_region_key) REFERENCES {fq}.dim_region (region_key)",
    ]
    for stmt in pk_statements + fk_statements:
        facade.sql_ok(stmt)


def _generate_data() -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(42)
    end_date = date.today()
    start_date = end_date - timedelta(days=730)
    n_days = (end_date - start_date).days + 1
    all_dates = [start_date + timedelta(days=i) for i in range(n_days)]

    pdf_date = pd.DataFrame(
        {
            "date_key": [int(d.strftime("%Y%m%d")) for d in all_dates],
            "calendar_date": all_dates,
            "year": [d.year for d in all_dates],
            "quarter": [(d.month - 1) // 3 + 1 for d in all_dates],
            "month": [d.month for d in all_dates],
            "month_name": [d.strftime("%B") for d in all_dates],
            "day_of_week": [d.strftime("%A") for d in all_dates],
            "is_weekend": [d.weekday() >= 5 for d in all_dates],
        }
    )

    categories = ["Electronics", "Apparel", "Home & Kitchen", "Sports", "Beauty"]
    brands = ["Acme", "Globex", "Initech", "Umbrella", "Stark"]
    n_products = 50
    pdf_product = pd.DataFrame(
        {
            "product_key": np.arange(1, n_products + 1),
            "sku": [f"SKU-{i:04d}" for i in range(1, n_products + 1)],
            "category": rng.choice(categories, n_products),
            "brand": rng.choice(brands, n_products),
            "unit_cost": np.round(rng.uniform(5, 500, n_products), 2),
        }
    )
    pdf_product["product_name"] = (
        pdf_product["brand"] + " " + pdf_product["category"] + " " + pdf_product["sku"]
    )
    pdf_product = pdf_product[
        ["product_key", "sku", "product_name", "category", "brand", "unit_cost"]
    ]

    segments = ["Consumer", "Small Business", "Enterprise"]
    regions = ["North America", "Europe", "APAC", "LATAM"]
    n_customers = 200
    signup_offsets = rng.integers(0, n_days, n_customers)
    pdf_customer = pd.DataFrame(
        {
            "customer_key": np.arange(1, n_customers + 1),
            "customer_name": [f"Customer {i:04d}" for i in range(1, n_customers + 1)],
            "segment": rng.choice(segments, n_customers, p=[0.6, 0.3, 0.1]),
            "region": rng.choice(regions, n_customers),
            "signup_date": [start_date + timedelta(days=int(o)) for o in signup_offsets],
        }
    )

    channels = ["Online", "In-Store"]
    n_stores = 10
    pdf_store = pd.DataFrame(
        {
            "store_key": np.arange(1, n_stores + 1),
            "store_name": [f"Store {i:02d}" for i in range(1, n_stores + 1)],
            "region": rng.choice(regions, n_stores),
            "channel": rng.choice(channels, n_stores, p=[0.5, 0.5]),
        }
    )

    n_sales = 5000
    sales_date_idx = rng.integers(0, n_days, n_sales)
    sales_product_idx = rng.integers(0, n_products, n_sales)
    sales_customer_idx = rng.integers(0, n_customers, n_sales)
    sales_store_idx = rng.integers(0, n_stores, n_sales)
    quantity = rng.integers(1, 6, n_sales)
    markup = rng.uniform(1.3, 2.0, n_sales)
    unit_cost_arr = pdf_product["unit_cost"].to_numpy()[sales_product_idx]
    unit_price = np.round(unit_cost_arr * markup, 2)
    revenue = np.round(unit_price * quantity, 2)
    pdf_sales = pd.DataFrame(
        {
            "order_id": np.arange(1, n_sales + 1),
            "date_key": pdf_date["date_key"].to_numpy()[sales_date_idx],
            "product_key": pdf_product["product_key"].to_numpy()[sales_product_idx],
            "customer_key": pdf_customer["customer_key"].to_numpy()[sales_customer_idx],
            "store_key": pdf_store["store_key"].to_numpy()[sales_store_idx],
            "quantity": quantity,
            "unit_price": unit_price,
            "revenue": revenue,
        }
    )

    return_reasons = [
        "Defective",
        "Wrong Item",
        "No Longer Needed",
        "Better Price Found",
        "Damaged in Transit",
    ]
    n_returns = int(n_sales * 0.08)
    returned = pdf_sales.sample(n=n_returns, random_state=42).reset_index(drop=True)
    return_quantity = np.minimum(returned["quantity"].to_numpy(), rng.integers(1, 4, n_returns))
    pdf_returns = pd.DataFrame(
        {
            "return_id": np.arange(1, n_returns + 1),
            "order_id": returned["order_id"],
            "date_key": returned["date_key"],
            "product_key": returned["product_key"],
            "customer_key": returned["customer_key"],
            "quantity": return_quantity,
            "return_amount": np.round(return_quantity * returned["unit_price"].to_numpy(), 2),
            "return_reason": rng.choice(return_reasons, n_returns),
        }
    )

    current_month_start = date(end_date.year, end_date.month, 1)
    month_starts = pd.date_range(end=current_month_start, periods=6, freq="MS").date
    inv_rows = [
        (int(md.strftime("%Y%m%d")), int(pk), int(sk))
        for md in month_starts
        for pk in pdf_product["product_key"]
        for sk in pdf_store["store_key"]
    ]
    pdf_inventory = pd.DataFrame(inv_rows, columns=["snapshot_date_key", "product_key", "store_key"])
    n_inv = len(pdf_inventory)
    pdf_inventory["stock_on_hand"] = rng.integers(0, 500, n_inv)
    pdf_inventory["stock_received"] = rng.integers(0, 200, n_inv)

    print(
        "Generated:",
        f"{len(pdf_date)} dates,",
        f"{len(pdf_product)} products,",
        f"{len(pdf_customer)} customers,",
        f"{len(pdf_store)} stores,",
        f"{len(pdf_sales)} sales lines,",
        f"{len(pdf_returns)} returns,",
        f"{len(pdf_inventory)} inventory snapshots",
    )
    return {
        "dim_date": pdf_date,
        "dim_product": pdf_product,
        "dim_customer": pdf_customer,
        "dim_store": pdf_store,
        "fact_sales": pdf_sales,
        "fact_returns": pdf_returns,
        "fact_inventory": pdf_inventory,
    }


class CreateCatalogSchemaTablesTask:
    key = "01_create_catalog_schema_tables"

    def __init__(self, facade: ProvisionWorkspaceFacade) -> None:
        self._facade = facade

    def run(self) -> None:
        _create_tables(self._facade)
        _add_constraints(self._facade)
        # Seed rows (including 2024 dates) are not loaded by Create / provision.
        # Load OLTP with generate_historical, dims/facts with etl_historical,
        # then realtime CDC with generate_realtime and etl_cdc.
        # _load_frames(self._facade)
        print("SKIP  star-schema seed load; use generate_historical / generate_realtime")


def _load_frames(facade: ProvisionWorkspaceFacade) -> None:
    frames = _generate_data()
    facade.insert_pandas(
        frames["dim_date"],
        "dim_date",
        {
            "date_key": "int",
            "calendar_date": "date",
            "year": "int",
            "quarter": "int",
            "month": "int",
            "month_name": "string",
            "day_of_week": "string",
            "is_weekend": "boolean",
        },
    )
    facade.insert_pandas(
        frames["dim_product"],
        "dim_product",
        {
            "product_key": "int",
            "sku": "string",
            "product_name": "string",
            "category": "string",
            "brand": "string",
            "unit_cost": "decimal(10,2)",
        },
    )
    facade.insert_pandas(
        frames["dim_customer"],
        "dim_customer",
        {
            "customer_key": "int",
            "customer_name": "string",
            "segment": "string",
            "region": "string",
            "signup_date": "date",
        },
    )
    facade.insert_pandas(
        frames["dim_store"],
        "dim_store",
        {
            "store_key": "int",
            "store_name": "string",
            "region": "string",
            "channel": "string",
        },
    )
    facade.insert_pandas(
        frames["fact_sales"],
        "fact_sales",
        {
            "order_id": "bigint",
            "date_key": "int",
            "product_key": "int",
            "customer_key": "int",
            "store_key": "int",
            "quantity": "int",
            "unit_price": "decimal(10,2)",
            "revenue": "decimal(12,2)",
        },
    )
    facade.insert_pandas(
        frames["fact_returns"],
        "fact_returns",
        {
            "return_id": "bigint",
            "order_id": "bigint",
            "date_key": "int",
            "product_key": "int",
            "customer_key": "int",
            "quantity": "int",
            "return_amount": "decimal(12,2)",
            "return_reason": "string",
        },
    )
    facade.insert_pandas(
        frames["fact_inventory"],
        "fact_inventory",
        {
            "snapshot_date_key": "int",
            "product_key": "int",
            "store_key": "int",
            "stock_on_hand": "int",
            "stock_received": "int",
        },
    )
    print("Done. Next: create metric views.")


def run(facade: ProvisionWorkspaceFacade) -> None:
    CreateCatalogSchemaTablesTask(facade).run()
