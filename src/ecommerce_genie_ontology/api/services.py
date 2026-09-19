from __future__ import annotations

from ecommerce_genie_ontology.common.dtos.ontology import (
    DpCtx,
    HlCtx,
    LsCtx,
    PwCtx,
    DyCtx,
    TcCtx,
    WfCtx,
    WhCtx,
)
from ecommerce_genie_ontology.common.constants.fraud_agents import agent_by_id, route_agent_id
from ecommerce_genie_ontology.common.dtos.chat import ChCtx
from ecommerce_genie_ontology.common.dtos.pipeline import EcCtx, EhCtx, FcCtx, OdCtx, OhCtx
from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory


class WorkflowsApiService:
    def __init__(self, factory: WorkflowsObjectsFactory) -> None:
        self._factory = factory
        self._runner = factory.orchestrator()

    def health(self, ctx: HlCtx) -> None:
        ctx.resp.status = "ok"

    def list_workflows(self, ctx: LsCtx) -> None:
        self._runner.list_workflows(ctx)

    def run_workflow(self, ctx: WfCtx) -> None:
        if ctx.req.as_job:
            self._runner.trigger(ctx)
            return
        self._runner.run(ctx)

    def deploy(self, ctx: DpCtx) -> None:
        self._runner.deploy(ctx)

    def provision_workspace(self, ctx: PwCtx) -> None:
        self._runner.provision_workspace(ctx)

    def provision_warehouse(self, ctx: WhCtx) -> None:
        self._runner.provision_warehouse(ctx)

    def truncate(self, ctx: TcCtx) -> None:
        self._runner.truncate(ctx)

    def destroy(self, ctx: DyCtx) -> None:
        self._runner.destroy(ctx)

    def generate_historical(self, ctx: OhCtx) -> None:
        self._runner.generate_historical(ctx)

    def generate_realtime(self, ctx: OdCtx) -> None:
        self._runner.generate_realtime(ctx)

    def etl_historical(self, ctx: EhCtx) -> None:
        self._runner.etl_historical(ctx)

    def etl_cdc(self, ctx: EcCtx) -> None:
        self._runner.etl_cdc(ctx)

    def run_fraud_case(self, ctx: FcCtx) -> None:
        self._runner.run_fraud_case(ctx)

    def chat(self, ctx: ChCtx) -> None:
        if ctx.req.backend == "langgraph":
            self._factory.lg_facade().chat(ctx)
            return
        if ctx.req.backend == "google_adk":
            self._factory.ga_facade().chat(ctx)
            return
        if ctx.req.backend == "genie":
            self._chat_genie(ctx)
            return
        raise SystemExit(f"Unknown chat backend {ctx.req.backend!r}")

    def _chat_genie(self, ctx: ChCtx) -> None:
        agent_id = ctx.req.agent_id or route_agent_id(ctx.req.prompt)
        agent = agent_by_id(agent_id)
        title = str(agent["title"]) if agent else None
        result = self._factory.adapter_factory().genie_facade().ask_reply(ctx.req.prompt, title=title)
        ctx.resp.backend = "genie"
        ctx.resp.agent_id = agent_id
        ctx.resp.agent_title = title or ""
        ctx.resp.reply = result.get("content") or result.get("rendered") or ""
        ctx.resp.message = result.get("status") or "genie"
        ctx.resp.steps = [f"databricks genie {ctx.resp.agent_title}"]
