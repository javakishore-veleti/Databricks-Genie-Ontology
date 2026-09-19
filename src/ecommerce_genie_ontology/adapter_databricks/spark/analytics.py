"""Fraud analytics sessions: IDs stay on the server; the agent writes per-customer outcomes."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from ecommerce_genie_ontology.common.constants.schema_ddl import analytics_statements, sales_star_statements
from ecommerce_genie_ontology.common.utils.sql_text import sql_string


def _as_rows(result, limit: int = 50) -> list[dict]:
    if hasattr(result, "collect"):
        collected = result.take(limit) if hasattr(result, "take") else result.limit(limit).collect()
        return [row.asDict(recursive=True) for row in collected]
    data = getattr(getattr(result, "result", None), "data_array", None) or []
    cols: list[str] = []
    manifest = getattr(result, "manifest", None)
    schema = getattr(manifest, "schema", None) if manifest else None
    columns = getattr(schema, "columns", None) if schema else None
    if columns:
        cols = [getattr(col, "name", f"c{i}") for i, col in enumerate(columns)]
    rows: list[dict] = []
    for row in data[:limit]:
        if cols:
            rows.append({cols[i]: row[i] if i < len(row) else None for i in range(len(cols))})
        else:
            rows.append({"cols": list(row)})
    return rows


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError as exc:
        raise SystemExit(f"Date must be YYYY-MM-DD, got {value!r}") from exc


def _keys(execute, oltp: str, star: str) -> tuple[str, str]:
    for sql in analytics_statements(oltp):
        execute(sql)
    for sql in sales_star_statements(star):
        execute(sql)
    return oltp, star


def _session_row(execute, oltp: str, analytics_id: str) -> dict:
    rows = _as_rows(
        execute(
            f"SELECT * FROM {oltp}.analytics_log WHERE analytics_id = {sql_string(analytics_id)} LIMIT 1"
        ),
        1,
    )
    if not rows:
        raise SystemExit(f"Unknown analytics_id {analytics_id!r}")
    return rows[0]


def _customer_ids_sql(oltp: str, start: date, end: date) -> str:
    return f"""
SELECT DISTINCT customer_id FROM (
  SELECT customer_id FROM {oltp}.customer_order
  WHERE CAST(order_ts AS DATE) BETWEEN DATE '{start}' AND DATE '{end}'
  UNION
  SELECT customer_id FROM {oltp}.customer_transaction
  WHERE txn_date BETWEEN DATE '{start}' AND DATE '{end}'
)
"""


def initiate(
    execute,
    *,
    catalog: str,
    oltp_schema: str,
    star_schema: str,
    from_date: str,
    to_date: str,
    requesting_user: str = "mcp",
) -> dict:
    start = _parse_date(from_date)
    end = _parse_date(to_date)
    if start > end:
        raise SystemExit("from_date must be on or before to_date")
    oltp, star = _keys(execute, f"{catalog}.{oltp_schema}", f"{catalog}.{star_schema}")
    analytics_id = "A" + uuid4().hex[:16]
    lo = int(start.strftime("%Y%m%d"))
    hi = int(end.strftime("%Y%m%d"))
    execute(
        f"""
INSERT INTO {oltp}.analytics_log (
  analytics_id, requesting_user, customer_count, start_date, end_date,
  requested_at, analytics_start_at, analytics_end_at, status
) VALUES (
  {sql_string(analytics_id)}, {sql_string(requesting_user or "mcp")}, 0,
  DATE '{start}', DATE '{end}', current_timestamp(), current_timestamp(), NULL, 'In Progress'
)
"""
    )
    execute(
        f"""
INSERT INTO {oltp}.analytics_log_customer (
  analytics_id, customer_id, order_count, order_line_count, shipment_count, posting_count,
  address_count, account_count, fact_sales_count, fact_returns_count, fact_inventory_count,
  fact_transaction_count, fact_order_event_count, analytics_outcome, analytics_log_info, updated_at
)
WITH ids AS ({_customer_ids_sql(oltp, start, end)}),
orders AS (
  SELECT customer_id, COUNT(*) AS n FROM {oltp}.customer_order
  WHERE CAST(order_ts AS DATE) BETWEEN DATE '{start}' AND DATE '{end}'
  GROUP BY customer_id
),
lines AS (
  SELECT o.customer_id, COUNT(*) AS n
  FROM {oltp}.customer_order_line l
  JOIN {oltp}.customer_order o ON o.order_id = l.order_id
  WHERE CAST(o.order_ts AS DATE) BETWEEN DATE '{start}' AND DATE '{end}'
  GROUP BY o.customer_id
),
ships AS (
  SELECT o.customer_id, COUNT(*) AS n
  FROM {oltp}.customer_order_shipment s
  JOIN {oltp}.customer_order o ON o.order_id = s.order_id
  WHERE CAST(o.order_ts AS DATE) BETWEEN DATE '{start}' AND DATE '{end}'
  GROUP BY o.customer_id
),
postings AS (
  SELECT customer_id, COUNT(*) AS n FROM {oltp}.customer_transaction
  WHERE txn_date BETWEEN DATE '{start}' AND DATE '{end}'
  GROUP BY customer_id
),
addresses AS (
  SELECT customer_id, COUNT(*) AS n FROM {oltp}.customer_address GROUP BY customer_id
),
accounts AS (
  SELECT customer_id, COUNT(*) AS n FROM {oltp}.customer_account GROUP BY customer_id
),
sales AS (
  SELECT CONCAT('C', LPAD(CAST(customer_key AS STRING), 6, '0')) AS customer_id, COUNT(*) AS n
  FROM {star}.fact_sales
  WHERE date_key BETWEEN {lo} AND {hi}
  GROUP BY customer_key
),
returns AS (
  SELECT CONCAT('C', LPAD(CAST(customer_key AS STRING), 6, '0')) AS customer_id, COUNT(*) AS n
  FROM {star}.fact_returns
  WHERE date_key BETWEEN {lo} AND {hi}
  GROUP BY customer_key
),
txns AS (
  SELECT CONCAT('C', LPAD(CAST(customer_key AS STRING), 6, '0')) AS customer_id, COUNT(*) AS n
  FROM {star}.fact_transaction
  WHERE date_key BETWEEN {lo} AND {hi}
  GROUP BY customer_key
),
events AS (
  SELECT CONCAT('C', LPAD(CAST(customer_key AS STRING), 6, '0')) AS customer_id, COUNT(*) AS n
  FROM {star}.fact_order_event
  WHERE date_key BETWEEN {lo} AND {hi}
  GROUP BY customer_key
)
SELECT
  {sql_string(analytics_id)},
  ids.customer_id,
  COALESCE(orders.n, 0),
  COALESCE(lines.n, 0),
  COALESCE(ships.n, 0),
  COALESCE(postings.n, 0),
  COALESCE(addresses.n, 0),
  COALESCE(accounts.n, 0),
  COALESCE(sales.n, 0),
  COALESCE(returns.n, 0),
  0,
  COALESCE(txns.n, 0),
  COALESCE(events.n, 0),
  'pending',
  '{{}}',
  current_timestamp()
FROM ids
LEFT JOIN orders ON orders.customer_id = ids.customer_id
LEFT JOIN lines ON lines.customer_id = ids.customer_id
LEFT JOIN ships ON ships.customer_id = ids.customer_id
LEFT JOIN postings ON postings.customer_id = ids.customer_id
LEFT JOIN addresses ON addresses.customer_id = ids.customer_id
LEFT JOIN accounts ON accounts.customer_id = ids.customer_id
LEFT JOIN sales ON sales.customer_id = ids.customer_id
LEFT JOIN returns ON returns.customer_id = ids.customer_id
LEFT JOIN txns ON txns.customer_id = ids.customer_id
LEFT JOIN events ON events.customer_id = ids.customer_id
"""
    )
    count_row = _as_rows(
        execute(
            f"SELECT COUNT(*) AS n FROM {oltp}.analytics_log_customer "
            f"WHERE analytics_id = {sql_string(analytics_id)}"
        ),
        1,
    )
    customer_count = int((count_row[0].get("n") if count_row else 0) or 0)
    execute(
        f"""
UPDATE {oltp}.analytics_log
SET customer_count = {customer_count}
WHERE analytics_id = {sql_string(analytics_id)}
"""
    )
    return {
        "analytics_id": analytics_id,
        "requesting_user": requesting_user or "mcp",
        "customer_count": customer_count,
        "start_date": str(start),
        "end_date": str(end),
        "status": "In Progress",
        "message": f"session opened for {customer_count} customers; IDs stay on the server",
    }


def get_analytics(execute, *, catalog: str, oltp_schema: str, star_schema: str, analytics_id: str) -> dict:
    oltp, _star = _keys(execute, f"{catalog}.{oltp_schema}", f"{catalog}.{star_schema}")
    session = _session_row(execute, oltp, analytics_id)
    pending = _as_rows(
        execute(
            f"""
SELECT COUNT(*) AS n FROM {oltp}.analytics_log_customer
WHERE analytics_id = {sql_string(analytics_id)} AND analytics_outcome = 'pending'
"""
        ),
        1,
    )
    session["pending_customers"] = int((pending[0].get("n") if pending else 0) or 0)
    return session


def list_analytics_customers(
    execute,
    *,
    catalog: str,
    oltp_schema: str,
    star_schema: str,
    analytics_id: str,
    limit: int = 20,
    offset: int = 0,
    outcome: str = "",
) -> dict:
    oltp, _star = _keys(execute, f"{catalog}.{oltp_schema}", f"{catalog}.{star_schema}")
    session = _session_row(execute, oltp, analytics_id)
    n = max(1, min(int(limit or 20), 50))
    skip = max(0, int(offset or 0))
    where = f"analytics_id = {sql_string(analytics_id)}"
    if outcome:
        where += f" AND analytics_outcome = {sql_string(outcome)}"
    rows = _as_rows(
        execute(
            f"""
SELECT customer_id, order_count, order_line_count, shipment_count, posting_count,
       address_count, account_count, fact_sales_count, fact_returns_count,
       fact_transaction_count, analytics_outcome
FROM {oltp}.analytics_log_customer
WHERE {where}
ORDER BY customer_id
LIMIT {n} OFFSET {skip}
"""
        ),
        n,
    )
    return {
        "analytics_id": analytics_id,
        "status": session.get("status"),
        "start_date": str(session.get("start_date") or ""),
        "end_date": str(session.get("end_date") or ""),
        "customer_count": int(session.get("customer_count") or 0),
        "offset": skip,
        "limit": n,
        "customers": rows,
        "message": f"{len(rows)} customers on this page; hydrate one customer next",
    }


def get_customer_oltp(
    execute,
    *,
    catalog: str,
    oltp_schema: str,
    star_schema: str,
    analytics_id: str,
    customer_id: str,
) -> dict:
    oltp, _star = _keys(execute, f"{catalog}.{oltp_schema}", f"{catalog}.{star_schema}")
    session = _session_row(execute, oltp, analytics_id)
    start = _parse_date(str(session.get("start_date")))
    end = _parse_date(str(session.get("end_date")))
    cid = sql_string(customer_id)
    orders = _as_rows(
        execute(
            f"""
SELECT order_id, customer_id, order_ts, status, store_id, billing_address_id,
       shipping_address_id, order_amount
FROM {oltp}.customer_order
WHERE customer_id = {cid}
  AND CAST(order_ts AS DATE) BETWEEN DATE '{start}' AND DATE '{end}'
ORDER BY order_ts DESC
LIMIT 25
"""
        ),
        25,
    )
    postings = _as_rows(
        execute(
            f"""
SELECT transaction_id, customer_id, account_id, counterparty_id, type_code, txn_ts,
       amount, balance_before, balance_after, status
FROM {oltp}.customer_transaction
WHERE customer_id = {cid}
  AND txn_date BETWEEN DATE '{start}' AND DATE '{end}'
ORDER BY txn_ts DESC
LIMIT 25
"""
        ),
        25,
    )
    return {"orders": orders, "postings": postings}


def get_customer_star(
    execute,
    *,
    catalog: str,
    oltp_schema: str,
    star_schema: str,
    analytics_id: str,
    customer_id: str,
) -> dict:
    oltp, star = _keys(execute, f"{catalog}.{oltp_schema}", f"{catalog}.{star_schema}")
    session = _session_row(execute, oltp, analytics_id)
    start = _parse_date(str(session.get("start_date")))
    end = _parse_date(str(session.get("end_date")))
    lo = int(start.strftime("%Y%m%d"))
    hi = int(end.strftime("%Y%m%d"))
    key = int("".join(ch for ch in customer_id if ch.isdigit()) or "0")
    sales = _as_rows(
        execute(
            f"""
SELECT order_id, date_key, product_key, customer_key, store_key, quantity, unit_price, revenue
FROM {star}.fact_sales
WHERE customer_key = {key} AND date_key BETWEEN {lo} AND {hi}
ORDER BY date_key DESC
LIMIT 25
"""
        ),
        25,
    )
    events = _as_rows(
        execute(
            f"""
SELECT order_id, date_key, order_hour, order_ts, customer_key, shipping_region_key,
       billing_region_key, order_amount, status, ship_ne_bill, cross_region
FROM {star}.fact_order_event
WHERE customer_key = {key} AND date_key BETWEEN {lo} AND {hi}
ORDER BY order_ts DESC
LIMIT 25
"""
        ),
        25,
    )
    txns = _as_rows(
        execute(
            f"""
SELECT transaction_id, date_key, customer_key, account_key, type_key, counterparty_key,
       amount, balance_before, balance_after
FROM {star}.fact_transaction
WHERE customer_key = {key} AND date_key BETWEEN {lo} AND {hi}
ORDER BY date_key DESC
LIMIT 25
"""
        ),
        25,
    )
    return {"fact_order_event": events, "fact_sales": sales, "fact_transaction": txns}


def get_customer_analytics(
    execute,
    *,
    catalog: str,
    oltp_schema: str,
    star_schema: str,
    analytics_id: str,
    customer_id: str,
) -> dict:
    oltp, _star = _keys(execute, f"{catalog}.{oltp_schema}", f"{catalog}.{star_schema}")
    rows = _as_rows(
        execute(
            f"""
SELECT * FROM {oltp}.analytics_log_customer
WHERE analytics_id = {sql_string(analytics_id)} AND customer_id = {sql_string(customer_id)}
LIMIT 1
"""
        ),
        1,
    )
    if not rows:
        raise SystemExit(f"Customer {customer_id!r} is not in analytics {analytics_id!r}")
    oltp_rows = get_customer_oltp(
        execute,
        catalog=catalog,
        oltp_schema=oltp_schema,
        star_schema=star_schema,
        analytics_id=analytics_id,
        customer_id=customer_id,
    )
    star_rows = get_customer_star(
        execute,
        catalog=catalog,
        oltp_schema=oltp_schema,
        star_schema=star_schema,
        analytics_id=analytics_id,
        customer_id=customer_id,
    )
    evidence = (
        oltp_rows["orders"]
        + oltp_rows["postings"]
        + star_rows["fact_order_event"]
        + star_rows["fact_transaction"]
    )[:50]
    return {
        "customer": rows[0],
        "oltp": oltp_rows,
        "star": star_rows,
        "evidence_row_count": len(evidence),
        "message": "counts plus at most 50 evidence rows; write record_customer_outcome next",
    }


def record_customer_outcome(
    execute,
    *,
    catalog: str,
    oltp_schema: str,
    star_schema: str,
    analytics_id: str,
    customer_id: str,
    analytics_outcome: str,
    analytics_log_info: str = "{}",
) -> dict:
    outcome = (analytics_outcome or "").strip().lower()
    if outcome not in {"fraud_found", "not_found"}:
        raise SystemExit("analytics_outcome must be fraud_found or not_found")
    info = analytics_log_info if analytics_log_info and analytics_log_info.strip() else "{}"
    oltp, _star = _keys(execute, f"{catalog}.{oltp_schema}", f"{catalog}.{star_schema}")
    _session_row(execute, oltp, analytics_id)
    execute(
        f"""
UPDATE {oltp}.analytics_log_customer
SET analytics_outcome = {sql_string(outcome)},
    analytics_log_info = {sql_string(info)},
    updated_at = current_timestamp()
WHERE analytics_id = {sql_string(analytics_id)} AND customer_id = {sql_string(customer_id)}
"""
    )
    return {
        "analytics_id": analytics_id,
        "customer_id": customer_id,
        "analytics_outcome": outcome,
        "analytics_log_info": info,
        "status": "ok",
        "message": f"recorded {outcome} for {customer_id}",
    }


def close_analytics(
    execute,
    *,
    catalog: str,
    oltp_schema: str,
    star_schema: str,
    analytics_id: str,
) -> dict:
    oltp, _star = _keys(execute, f"{catalog}.{oltp_schema}", f"{catalog}.{star_schema}")
    session = _session_row(execute, oltp, analytics_id)
    execute(
        f"""
UPDATE {oltp}.analytics_log
SET status = 'Completed', analytics_end_at = current_timestamp()
WHERE analytics_id = {sql_string(analytics_id)}
"""
    )
    return {
        "analytics_id": analytics_id,
        "status": "Completed",
        "customer_count": int(session.get("customer_count") or 0),
        "message": "analytics session closed",
    }
