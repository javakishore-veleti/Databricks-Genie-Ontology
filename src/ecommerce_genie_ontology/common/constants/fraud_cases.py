from __future__ import annotations

FRAUD_CASES: tuple[dict[str, str], ...] = (
    {"id": "01", "name": "Order velocity burst", "store": "OLTP orders"},
    {"id": "02", "name": "Shared address, unrelated customers", "store": "entity_link"},
    {"id": "03", "name": "Ship-to not equal bill-to", "store": "OLTP + address"},
    {"id": "04", "name": "High return rate vs peers", "store": "facts"},
    {"id": "05", "name": "First-order high value", "store": "OLTP"},
    {"id": "06", "name": "Duplicate name and address accounts", "store": "OLTP customer"},
    {"id": "07", "name": "Split orders under a threshold", "store": "OLTP"},
    {"id": "08", "name": "New address plus expedited ship", "store": "shipment"},
    {"id": "09", "name": "Address change then surge", "store": "CDF + orders"},
    {"id": "10", "name": "Promo discount abuse", "store": "order lines"},
    {"id": "11", "name": "Orders vs inventory mismatch", "store": "facts"},
    {"id": "12", "name": "Rapid return after delivery", "store": "returns + shipment"},
    {"id": "13", "name": "Burst of new customers, one address", "store": "entity_link"},
    {"id": "14", "name": "Order then cancel or ship abort", "store": "OLTP status"},
    {"id": "15", "name": "Impossible geo two regions one hour", "store": "orders + address"},
)


def fraud_sql(case_id: str, oltp: str, star: str) -> str:
    queries = {
        "01": f"""
SELECT customer_id, DATE(order_ts) d, COUNT(*) orders
FROM {oltp}.customer_order
GROUP BY customer_id, DATE(order_ts)
HAVING COUNT(*) > 20
ORDER BY orders DESC
LIMIT 50
""",
        "02": f"""
SELECT src_id, dst_id, COUNT(*) links
FROM {oltp}.entity_link
WHERE rel = 'shared_address'
GROUP BY src_id, dst_id
LIMIT 50
""",
        "03": f"""
SELECT order_id, customer_id, billing_address_id, shipping_address_id
FROM {oltp}.customer_order
WHERE billing_address_id <> shipping_address_id
LIMIT 50
""",
        "04": f"""
SELECT customer_key, COUNT(*) returns
FROM {star}.fact_returns
GROUP BY customer_key
ORDER BY returns DESC
LIMIT 50
""",
        "05": f"""
SELECT o.customer_id, o.order_id, o.order_amount
FROM {oltp}.customer_order o
JOIN (
  SELECT customer_id, MIN(order_ts) first_ts
  FROM {oltp}.customer_order GROUP BY customer_id
) f ON o.customer_id = f.customer_id AND o.order_ts = f.first_ts
WHERE o.order_amount > 200
LIMIT 50
""",
        "06": f"""
SELECT a.line1, a.postal_code, COUNT(DISTINCT a.customer_id) customers
FROM {oltp}.customer_address a
GROUP BY a.line1, a.postal_code
HAVING COUNT(DISTINCT a.customer_id) > 1
LIMIT 50
""",
        "07": f"""
SELECT customer_id, DATE(order_ts) d, COUNT(*) orders, SUM(order_amount) amt
FROM {oltp}.customer_order
GROUP BY customer_id, DATE(order_ts)
HAVING COUNT(*) >= 3 AND SUM(order_amount) BETWEEN 80 AND 120
LIMIT 50
""",
        "08": f"""
SELECT s.shipment_id, s.order_id, s.carrier, s.ship_address_id
FROM {oltp}.customer_order_shipment s
LIMIT 50
""",
        "09": f"""
SELECT customer_id, COUNT(*) orders
FROM {oltp}.customer_order
WHERE order_ts > current_timestamp() - INTERVAL 7 DAYS
GROUP BY customer_id
HAVING COUNT(*) > 10
LIMIT 50
""",
        "10": f"""
SELECT sku, AVG(unit_price) avg_price, COUNT(*) lines
FROM {oltp}.customer_order_line
GROUP BY sku
LIMIT 50
""",
        "11": f"""
SELECT f.product_key, SUM(f.quantity) sold, MAX(i.stock_on_hand) stock
FROM {star}.fact_sales f
LEFT JOIN {star}.fact_inventory i ON f.product_key = i.product_key
GROUP BY f.product_key
LIMIT 50
""",
        "12": f"""
SELECT r.return_id, r.order_id, r.return_amount
FROM {star}.fact_returns r
LIMIT 50
""",
        "13": f"""
SELECT dst_id address_id, COUNT(DISTINCT src_id) customers
FROM {oltp}.entity_link
WHERE rel = 'has_address'
GROUP BY dst_id
HAVING COUNT(DISTINCT src_id) > 1
LIMIT 50
""",
        "14": f"""
SELECT status, COUNT(*) n
FROM {oltp}.customer_order
WHERE status IN ('cancelled')
GROUP BY status
""",
        "15": f"""
SELECT customer_id, COUNT(DISTINCT region) regions
FROM {oltp}.customer_address
GROUP BY customer_id
HAVING COUNT(DISTINCT region) > 1
LIMIT 50
""",
    }
    if case_id not in queries:
        raise SystemExit(f"Unknown fraud case {case_id!r}")
    return queries[case_id]
