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
from ecommerce_genie_ontology.common.interfaces.workflow import WorkflowRunner


class WorkflowsApiService:
    def __init__(self, runner: WorkflowRunner) -> None:
        self._runner = runner

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
