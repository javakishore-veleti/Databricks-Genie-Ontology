"""GaFacade implementation. FastAPI calls this; this module invokes Google ADK."""

from __future__ import annotations

from ecommerce_genie_ontology.common.dtos.chat import ChCtx
from ecommerce_genie_ontology.common.interfaces.ga import GaFacade


class GoogleAdkFraudAgentFacadeImpl:
    def chat(self, ctx: ChCtx) -> None:
        from ecommerce_genie_ontology.agents_google_adk.runtime import invoke_adk

        result = invoke_adk(ctx.req.prompt, ctx.req.agent_id)
        ctx.resp.backend = "google_adk"
        ctx.resp.agent_id = result.get("agent_id") or ctx.req.agent_id
        ctx.resp.agent_title = result.get("agent_title") or ""
        ctx.resp.steps = list(result.get("steps") or [])
        ctx.resp.evidence = list(result.get("evidence") or [])
        ctx.resp.reply = result.get("reply") or ""
        ctx.resp.message = result.get("message") or "google_adk"


def _assert_protocol() -> None:
    _: type[GaFacade] = GoogleAdkFraudAgentFacadeImpl
