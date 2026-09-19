"""Google ADK root agent plus 10 specialist sub-agents on the same MCP tools."""

from __future__ import annotations

from ecommerce_genie_ontology.common.constants.fraud_agents import FRAUD_AGENTS, case_names
from ecommerce_genie_ontology.mcp.tools import (
    list_fraud_agents,
    list_fraud_cases,
    query_dataset,
    run_fraud_agent_cases,
    run_fraud_case,
)

TOOLS = [
    list_fraud_agents,
    list_fraud_cases,
    run_fraud_case,
    run_fraud_agent_cases,
    query_dataset,
]


def build_root_agent():
    try:
        from google.adk.agents import Agent
    except ImportError as exc:
        raise SystemExit("Install the Google ADK extra: uv sync --extra google-adk") from exc

    specialists = []
    for item in FRAUD_AGENTS:
        names = ", ".join(case_names(item["case_ids"]))  # type: ignore[arg-type]
        specialists.append(
            Agent(
                name=str(item["id"]),
                description=str(item["description"]),
                instruction=(
                    f"You are {item['title']}. You only investigate: {names}. "
                    "Call run_fraud_agent_cases with your agent id, or run_fraud_case for a single pack. "
                    "Use query_dataset for extra SELECT ... LIMIT 50 against OLTP or star tables. "
                    "Never load full tables into context."
                ),
                tools=TOOLS,
            )
        )
    return Agent(
        name="fraud_orchestrator",
        model="gemini-2.5-flash",
        description="Routes ecommerce fraud questions to 10 specialists on shared dims, facts, and OLTP.",
        instruction=(
            "You coordinate 10 fraud specialists that share ecommerce_genie_ontology.retail_oltp "
            "and retail_demo dims/facts. Delegate to the matching sub-agent. "
            "Use MCP tools for bounded evidence packs. Do not dump tables."
        ),
        tools=TOOLS,
        sub_agents=specialists,
    )


root_agent = None


def get_root_agent():
    global root_agent
    if root_agent is None:
        root_agent = build_root_agent()
    return root_agent
