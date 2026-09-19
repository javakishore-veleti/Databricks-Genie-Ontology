"""LgFacade implementation. FastAPI calls this; this module invokes LangGraph."""

from __future__ import annotations

from ecommerce_genie_ontology.common.dtos.chat import ChCtx
from ecommerce_genie_ontology.common.interfaces.lg import LgFacade


class LangGraphFraudAgentFacadeImpl:
    def chat(self, ctx: ChCtx) -> None:
        from ecommerce_genie_ontology.agents_langgraph.graph import invoke_graph

        result = invoke_graph(ctx.req.prompt, ctx.req.agent_id)
        ctx.resp.backend = "langgraph"
        ctx.resp.agent_id = result.get("agent_id") or ctx.req.agent_id
        ctx.resp.agent_title = result.get("agent_title") or ""
        ctx.resp.steps = list(result.get("steps") or [])
        ctx.resp.evidence = list(result.get("evidence") or [])
        ctx.resp.reply = result.get("reply") or ""
        ctx.resp.message = "langgraph"


def _assert_protocol() -> None:
    _: type[LgFacade] = LangGraphFraudAgentFacadeImpl
