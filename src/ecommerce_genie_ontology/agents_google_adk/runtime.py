"""Run Google ADK when GOOGLE_API_KEY is set; otherwise specialist MCP dispatch in this package."""

from __future__ import annotations

import os
from typing import Any

from ecommerce_genie_ontology.common.constants.fraud_agents import agent_by_id, route_agent_id
from ecommerce_genie_ontology.mcp import tools as mcp_tools


def invoke_adk(prompt: str, agent_id: str = "") -> dict[str, Any]:
    if os.getenv("GOOGLE_API_KEY", "").strip():
        try:
            return _invoke_runner(prompt, agent_id)
        except Exception as exc:
            fallback = _invoke_specialists(prompt, agent_id)
            fallback["message"] = f"google-adk runner failed ({exc}); used specialist MCP dispatch"
            return fallback
    result = _invoke_specialists(prompt, agent_id)
    result["message"] = "google-adk package invoked; GOOGLE_API_KEY unset, used specialist MCP dispatch"
    return result


def _invoke_specialists(prompt: str, agent_id: str) -> dict[str, Any]:
    chosen = agent_id or route_agent_id(prompt)
    agent = agent_by_id(chosen) or agent_by_id(route_agent_id(prompt))
    assert agent is not None
    packs_result = mcp_tools.run_fraud_agent_cases(str(agent["id"]))
    packs = packs_result.get("packs") or []
    evidence = [
        {
            "case_id": pack.get("case_id"),
            "name": pack.get("name"),
            "message": pack.get("message"),
            "rows": pack.get("rows") or [],
        }
        for pack in packs
    ]
    lines = [
        f"{agent['title']} reviewed: {prompt}",
        "Evidence packs (max 50 rows each) from OLTP / dims / facts via MCP tools:",
    ]
    for pack in evidence:
        lines.append(f"- {pack.get('case_id')} {pack.get('name')}: {pack.get('message')}")
    return {
        "agent_id": str(agent["id"]),
        "agent_title": str(agent["title"]),
        "steps": [f"google-adk specialist {agent['title']}", f"ran {len(packs)} MCP fraud evidence packs"],
        "evidence": evidence,
        "reply": "\n".join(lines),
        "message": "google_adk",
    }


def _invoke_runner(prompt: str, agent_id: str) -> dict[str, Any]:
    import asyncio

    from google.adk.runners import InMemoryRunner
    from google.genai import types

    from ecommerce_genie_ontology.agents_google_adk.agent import get_root_agent

    agent = get_root_agent()
    content = prompt if not agent_id else f"[specialist={agent_id}] {prompt}"
    runner = InMemoryRunner(agent=agent)

    async def _run() -> str:
        parts: list[str] = []
        message = types.Content(role="user", parts=[types.Part(text=content)])
        async for event in runner.run_async(
            user_id="sales-analyzer",
            session_id="fraud",
            new_message=message,
        ):
            text = getattr(event, "content", None)
            if text is None:
                continue
            event_parts = getattr(text, "parts", None) or []
            for part in event_parts:
                value = getattr(part, "text", None)
                if value:
                    parts.append(value)
        return "\n".join(parts) or "Google ADK completed with no text reply."

    reply = asyncio.run(_run())
    routed = agent_id or route_agent_id(prompt)
    spec = agent_by_id(routed)
    return {
        "agent_id": routed,
        "agent_title": str(spec["title"]) if spec else "fraud_orchestrator",
        "steps": ["google-adk InMemoryRunner"],
        "evidence": [],
        "reply": reply,
        "message": "google_adk",
    }
