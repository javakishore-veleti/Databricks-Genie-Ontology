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
        "and 15 fraud evidence packs / 10 fraud specialists. Do not load full tables. "
        "Analytics NL questions belong on Databricks Genie MCP."
    ),
)

mcp.tool()(mcp_tools.list_fraud_cases)
mcp.tool()(mcp_tools.list_fraud_agents)
mcp.tool()(mcp_tools.run_fraud_case)
mcp.tool()(mcp_tools.run_fraud_agent_cases)
mcp.tool()(mcp_tools.generate_historical_oltp)
mcp.tool()(mcp_tools.generate_realtime_orders)
mcp.tool()(mcp_tools.etl_star_historical)
mcp.tool()(mcp_tools.generate_next_oltp)
mcp.tool()(mcp_tools.etl_next_months)
mcp.tool()(mcp_tools.etl_star_cdc)
mcp.tool()(mcp_tools.query_dataset)


def main() -> None:
    load_env()
    mcp.run(transport="stdio")
