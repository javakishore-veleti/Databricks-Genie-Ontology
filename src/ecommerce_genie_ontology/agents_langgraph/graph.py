"""LangGraph graph: route a prompt to one of 10 specialists, run MCP evidence tools."""

from __future__ import annotations

from typing import Any, TypedDict

from ecommerce_genie_ontology.common.constants.fraud_agents import agent_by_id, route_agent_id
from ecommerce_genie_ontology.mcp import tools as mcp_tools


class FraudState(TypedDict):
    prompt: str
    agent_id: str
    agent_title: str
    steps: list[str]
    evidence: list[dict]
    reply: str


def _build_graph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise SystemExit("Install the LangGraph extra: uv sync --extra langgraph") from exc

    graph = StateGraph(FraudState)
    graph.add_node("route", _route)
    graph.add_node("act", _act)
    graph.add_node("respond", _respond)
    graph.add_edge(START, "route")
    graph.add_edge("route", "act")
    graph.add_edge("act", "respond")
    graph.add_edge("respond", END)
    return graph.compile()


def _route(state: FraudState) -> dict[str, Any]:
    agent_id = state.get("agent_id") or route_agent_id(state["prompt"])
    agent = agent_by_id(agent_id)
    if agent is None:
        agent_id = route_agent_id(state["prompt"])
        agent = agent_by_id(agent_id)
    assert agent is not None
    return {
        "agent_id": str(agent["id"]),
        "agent_title": str(agent["title"]),
        "steps": list(state.get("steps") or []) + [f"routed to {agent['title']}"],
    }


def _act(state: FraudState) -> dict[str, Any]:
    result = mcp_tools.run_fraud_agent_cases(state["agent_id"])
    packs = result.get("packs") or []
    evidence: list[dict] = []
    for pack in packs:
        evidence.append(
            {
                "case_id": pack.get("case_id"),
                "name": pack.get("name"),
                "message": pack.get("message"),
                "rows": pack.get("rows") or [],
            }
        )
    return {
        "evidence": evidence,
        "steps": list(state.get("steps") or []) + [f"ran {len(packs)} MCP fraud evidence packs"],
    }


def _respond(state: FraudState) -> dict[str, Any]:
    lines = [
        f"{state['agent_title']} reviewed: {state['prompt']}",
        "Evidence packs (max 50 rows each) from OLTP / dims / facts via MCP tools:",
    ]
    for pack in state.get("evidence") or []:
        lines.append(f"- {pack.get('case_id')} {pack.get('name')}: {pack.get('message')}")
    return {"reply": "\n".join(lines)}


def invoke_graph(prompt: str, agent_id: str = "") -> FraudState:
    compiled = _build_graph()
    return compiled.invoke(
        {
            "prompt": prompt,
            "agent_id": agent_id,
            "agent_title": "",
            "steps": [],
            "evidence": [],
            "reply": "",
        }
    )
