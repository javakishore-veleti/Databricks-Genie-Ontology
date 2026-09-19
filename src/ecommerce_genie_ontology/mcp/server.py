"""Operational MCP server: OLTP generate, star-schema ETL, and fraud evidence packs.

Genie already has a Databricks-managed MCP at /api/2.0/mcp/genie/{space_id} for
analytics questions. This server is separate: it never dumps fact tables into
the model. Tools trigger Spark jobs or return at most 50 evidence rows.
"""

from __future__ import annotations

from ecommerce_genie_ontology.common.utils.env import load_env
from ecommerce_genie_ontology.mcp import tools as mcp_tools

try:
    from mcp.server.mcpserver import MCPServer
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install the MCP extra: uv sync --extra mcp") from exc

mcp = MCPServer(
    "ecommerce-oltp-mcp",
    instructions=(
        "Operational tools for ecommerce OLTP generation, CDC star-schema ETL, "
        "fraud analytics sessions, and 15 evidence packs / 10 specialists. "
        "Use initiate_fraud_analytics, then page customers, hydrate one customer, "
        "record_customer_outcome, and close_analytics. Do not load full tables. "
        "Analytics NL questions belong on Databricks Genie MCP."
    ),
)

mcp.tool()(mcp_tools.list_fraud_cases)
mcp.tool()(mcp_tools.list_fraud_agents)
mcp.tool()(mcp_tools.run_fraud_case)
mcp.tool()(mcp_tools.run_fraud_agent_cases)
mcp.tool()(mcp_tools.initiate_fraud_analytics)
mcp.tool()(mcp_tools.get_analytics)
mcp.tool()(mcp_tools.list_analytics_customers)
mcp.tool()(mcp_tools.get_customer_analytics)
mcp.tool()(mcp_tools.get_customer_oltp)
mcp.tool()(mcp_tools.get_customer_star)
mcp.tool()(mcp_tools.record_customer_outcome)
mcp.tool()(mcp_tools.close_analytics)
mcp.tool()(mcp_tools.generate_historical_oltp)
mcp.tool()(mcp_tools.generate_realtime_orders)
mcp.tool()(mcp_tools.etl_star_historical)
mcp.tool()(mcp_tools.generate_next_oltp)
mcp.tool()(mcp_tools.etl_next_months)
mcp.tool()(mcp_tools.etl_star_cdc)
mcp.tool()(mcp_tools.query_dataset)


def _http_app(host: str, port: int):
    """FastAPI host: Pyctuator (/actuator) + MCP streamable HTTP (/mcp)."""
    import os
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.responses import RedirectResponse
    from pyctuator.endpoints import Endpoints
    from pyctuator.pyctuator import Pyctuator

    mcp_asgi = mcp.streamable_http_app(host=host, streamable_http_path="/mcp")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        manager = getattr(mcp, "session_manager", None)
        if manager is not None:
            async with manager.run():
                yield
            return
        async with mcp_asgi.router.lifespan_context(mcp_asgi):
            yield

    app = FastAPI(
        title="mcp-ecommerce-oltp",
        description="Custom MCP for fraud analytics sessions on retail_oltp / retail_star.",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/")
    async def root() -> RedirectResponse:
        return RedirectResponse("/actuator/health")

    @app.get("/health")
    async def health_alias() -> RedirectResponse:
        return RedirectResponse("/actuator/health")

    public = os.getenv("DATABRICKS_APP_URL", "").rstrip("/") or f"http://{host}:{port}"
    Pyctuator(
        app,
        "mcp-ecommerce-oltp",
        app_url=public,
        pyctuator_endpoint_url=f"{public}/actuator",
        registration_url=None,
        app_description="Custom MCP for fraud analytics sessions on retail_oltp / retail_star.",
        additional_app_info={"mcp": "/mcp"},
        disabled_endpoints=(
            Endpoints.ENV | Endpoints.LOGFILE | Endpoints.HTTP_TRACE | Endpoints.LOGGERS
        ),
    )
    app.mount("/", mcp_asgi)
    return app


def main(argv: list[str] | None = None) -> None:
    import argparse
    import os

    load_env()
    parser = argparse.ArgumentParser(prog="genie-ontology mcp")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve streamable HTTP at /mcp (Databricks App). Default is stdio.",
    )
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    args = parser.parse_args(argv)
    if args.http or os.getenv("MCP_TRANSPORT", "").lower() == "http":
        try:
            import uvicorn
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("Install uvicorn to serve MCP over HTTP") from exc
        try:
            app = _http_app(args.host, args.port)
        except ImportError as exc:  # pragma: no cover
            raise SystemExit("Install pyctuator for HTTP actuator + MCP") from exc
        uvicorn.run(app, host=args.host, port=args.port)
        return
    mcp.run(transport="stdio")
