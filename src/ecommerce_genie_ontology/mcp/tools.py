"""Shared MCP tool implementations used by the MCP server, LangGraph, and Google ADK."""

from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.spark import analytics as analytics_session
from ecommerce_genie_ontology.common.constants.fraud_agents import FRAUD_AGENTS, agent_by_id, case_names
from ecommerce_genie_ontology.common.constants.fraud_cases import FRAUD_CASES
from ecommerce_genie_ontology.common.dtos.pipeline import (
    EcCtx,
    EcReq,
    EcResp,
    EhCtx,
    EhReq,
    EhResp,
    EmCtx,
    EmReq,
    EmResp,
    FcCtx,
    FcReq,
    FcResp,
    NxCtx,
    NxReq,
    NxResp,
    OdCtx,
    OdReq,
    OdResp,
    OhCtx,
    OhReq,
    OhResp,
)
from ecommerce_genie_ontology.common.utils.env import load_env
from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory


def _runner():
    load_env()
    return WorkflowsObjectsFactory.instance().orchestrator()


def _sql():
    load_env()
    return WorkflowsObjectsFactory.instance().adapter_factory().sql_facade()


def _session():
    load_env()
    return WorkflowsObjectsFactory.instance().adapter_factory().session()


def list_fraud_cases() -> list[dict[str, str]]:
    """List the 15 fraud detection cases. Each case is a named SQL evidence pack."""
    return [dict(item) for item in FRAUD_CASES]


def list_fraud_agents() -> list[dict]:
    """List the 10 Databricks Genie fraud specialists that share OLTP + dims/facts."""
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "description": item["description"],
            "case_ids": list(item["case_ids"]),
            "cases": case_names(item["case_ids"]),  # type: ignore[arg-type]
        }
        for item in FRAUD_AGENTS
    ]


def run_fraud_case(case_id: str) -> dict:
    """Run one fraud case (ids 01-15). Returns at most 50 evidence rows."""
    ctx = FcCtx(FcReq(case_id=case_id), FcResp())
    _runner().run_fraud_case(ctx)
    return {
        "case_id": ctx.resp.case_id,
        "name": ctx.resp.name,
        "message": ctx.resp.message,
        "rows": ctx.resp.rows,
    }


def run_fraud_agent_cases(agent_id: str) -> dict:
    """Run every evidence pack owned by one of the 10 fraud specialists."""
    agent = agent_by_id(agent_id)
    if agent is None:
        raise SystemExit(f"Unknown fraud agent {agent_id!r}")
    packs = [run_fraud_case(case_id) for case_id in agent["case_ids"]]  # type: ignore[union-attr]
    return {
        "agent_id": agent["id"],
        "title": agent["title"],
        "packs": packs,
    }


def generate_historical_oltp(
    customer_count: int = 200,
    orders_per_year: int = 25000,
    year_count: int = 3,
    as_job: bool = True,
) -> dict:
    """Write customer, address, order, line, shipment, and entity_link tables."""
    ctx = OhCtx(
        OhReq(
            customer_count=customer_count,
            orders_per_year=orders_per_year,
            year_count=year_count,
            as_job=as_job,
        ),
        OhResp(),
    )
    _runner().generate_historical(ctx)
    return {
        "customers": ctx.resp.customers,
        "addresses": ctx.resp.addresses,
        "orders": ctx.resp.orders,
        "lines": ctx.resp.lines,
        "status": ctx.resp.status,
        "message": ctx.resp.message,
    }


def generate_realtime_orders(
    count: int = 1000,
    year_window: str = "latest",
    as_job: bool = True,
) -> dict:
    """Append 100-10000 new OLTP orders. year_window is latest | last_2 | last_3 | all."""
    ctx = OdCtx(OdReq(count=count, year_window=year_window, as_job=as_job), OdResp())  # type: ignore[arg-type]
    _runner().generate_realtime(ctx)
    return {
        "orders": ctx.resp.orders,
        "lines": ctx.resp.lines,
        "year_window": ctx.resp.year_window,
        "status": ctx.resp.status,
        "message": ctx.resp.message,
    }


def etl_star_historical(as_job: bool = True) -> dict:
    """Rebuild star-schema dims and fact_sales from OLTP (overwrite)."""
    ctx = EhCtx(EhReq(as_job=as_job), EhResp())
    _runner().etl_historical(ctx)
    return {"status": ctx.resp.status, "message": ctx.resp.message}


def generate_next_oltp(row_count: int = 100000, as_job: bool = True) -> dict:
    """Append the next 100000 OLTP rows. Updates ingestion_tracker and ingestion_log."""
    ctx = NxCtx(NxReq(row_count=row_count, as_job=as_job), NxResp())
    _runner().generate_next_oltp(ctx)
    return {
        "rows": ctx.resp.rows,
        "orders": ctx.resp.orders,
        "postings": ctx.resp.postings,
        "start_date": ctx.resp.start_date,
        "end_date": ctx.resp.end_date,
        "year": ctx.resp.year,
        "status": ctx.resp.status,
        "message": ctx.resp.message,
    }


def etl_next_months(months: int = 3, as_job: bool = True) -> dict:
    """Append star dims/facts for the next N months (1-12). No error if less data remains."""
    ctx = EmCtx(EmReq(months=months, as_job=as_job), EmResp())
    _runner().etl_next_months(ctx)
    return {
        "rows": ctx.resp.rows,
        "months": ctx.resp.months,
        "start_date": ctx.resp.start_date,
        "end_date": ctx.resp.end_date,
        "year": ctx.resp.year,
        "status": ctx.resp.status,
        "message": ctx.resp.message,
    }


def etl_star_cdc(as_job: bool = True) -> dict:
    """Apply Delta change feed from OLTP customer_order into fact_sales (append)."""
    ctx = EcCtx(EcReq(as_job=as_job), EcResp())
    _runner().etl_cdc(ctx)
    return {"rows": ctx.resp.rows, "status": ctx.resp.status, "message": ctx.resp.message}


def _analytics_args() -> dict:
    session = _session()
    return {
        "catalog": session.catalog,
        "oltp_schema": session.context.oltp_schema,
        "star_schema": session.schema_name,
    }


def initiate_fraud_analytics(from_date: str, to_date: str, requesting_user: str = "mcp") -> dict:
    """Open a fraud session. Server finds customer IDs and writes counts. Does not return the ID list."""
    return analytics_session.initiate(
        _sql().execute,
        **_analytics_args(),
        from_date=from_date,
        to_date=to_date,
        requesting_user=requesting_user,
    )


def get_analytics(analytics_id: str) -> dict:
    """Return the analytics_log header and how many customers are still pending."""
    return analytics_session.get_analytics(_sql().execute, **_analytics_args(), analytics_id=analytics_id)


def list_analytics_customers(
    analytics_id: str,
    limit: int = 20,
    offset: int = 0,
    outcome: str = "",
) -> dict:
    """Page customers in a session (max 50). Includes counts and outcome, not a raw ID dump."""
    return analytics_session.list_analytics_customers(
        _sql().execute,
        **_analytics_args(),
        analytics_id=analytics_id,
        limit=limit,
        offset=offset,
        outcome=outcome,
    )


def get_customer_oltp(analytics_id: str, customer_id: str) -> dict:
    """At most 25 orders and 25 postings for one customer in the session date range."""
    return analytics_session.get_customer_oltp(
        _sql().execute,
        **_analytics_args(),
        analytics_id=analytics_id,
        customer_id=customer_id,
    )


def get_customer_star(analytics_id: str, customer_id: str) -> dict:
    """At most 25 order-event facts and 25 posting facts for one customer in the session window."""
    return analytics_session.get_customer_star(
        _sql().execute,
        **_analytics_args(),
        analytics_id=analytics_id,
        customer_id=customer_id,
    )


def get_customer_analytics(analytics_id: str, customer_id: str) -> dict:
    """One customer row: counts plus at most 50 evidence rows. Then record_customer_outcome."""
    return analytics_session.get_customer_analytics(
        _sql().execute,
        **_analytics_args(),
        analytics_id=analytics_id,
        customer_id=customer_id,
    )


def record_customer_outcome(
    analytics_id: str,
    customer_id: str,
    analytics_outcome: str,
    analytics_log_info: str = "{}",
) -> dict:
    """Write fraud_found or not_found plus JSON why for one customer."""
    return analytics_session.record_customer_outcome(
        _sql().execute,
        **_analytics_args(),
        analytics_id=analytics_id,
        customer_id=customer_id,
        analytics_outcome=analytics_outcome,
        analytics_log_info=analytics_log_info,
    )


def close_analytics(analytics_id: str) -> dict:
    """Mark the analytics session Completed."""
    return analytics_session.close_analytics(
        _sql().execute,
        **_analytics_args(),
        analytics_id=analytics_id,
    )


def query_dataset(sql: str) -> dict:
    """Run a SELECT against dims, facts, or OLTP. LIMIT 50. Never dumps full tables."""
    statement = sql.strip().rstrip(";")
    head = statement.lower().lstrip()
    if not (head.startswith("select") or head.startswith("with")):
        raise SystemExit("query_dataset only allows SELECT or WITH statements")
    if ";" in statement:
        raise SystemExit("query_dataset allows a single statement")
    if "limit" not in head:
        statement = f"{statement} LIMIT 50"
    session = _session()
    result = _sql().execute(statement)
    rows = _rows(result)
    return {
        "sql": statement,
        "catalog": session.catalog,
        "star": session.fq_schema,
        "oltp": session.context.fq_oltp,
        "rows": rows[:50],
        "row_count": min(len(rows), 50),
    }


def _rows(result) -> list[dict]:
    if hasattr(result, "collect"):
        collected = result.take(50) if hasattr(result, "take") else result.limit(50).collect()
        return [row.asDict(recursive=True) for row in collected]
    data = getattr(getattr(result, "result", None), "data_array", None) or []
    cols: list[str] = []
    manifest = getattr(result, "manifest", None)
    schema = getattr(manifest, "schema", None) if manifest else None
    columns = getattr(schema, "columns", None) if schema else None
    if columns:
        cols = [getattr(col, "name", f"c{i}") for i, col in enumerate(columns)]
    rows: list[dict] = []
    for row in data[:50]:
        if cols:
            rows.append({cols[i]: row[i] if i < len(row) else None for i in range(len(cols))})
        else:
            rows.append({"cols": list(row)})
    return rows
