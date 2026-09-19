from __future__ import annotations

from typing import TYPE_CHECKING

from ecommerce_genie_ontology.common.dtos.jobs import JobSpec
from ecommerce_genie_ontology.common.dtos.ontology import DpCtx, LsCtx, PwCtx, DyCtx, TcCtx, WfCtx, WfItem, WhCtx
from ecommerce_genie_ontology.common.interfaces.workflow import WorkflowRunner
from ecommerce_genie_ontology.workflows.job_specs import JOB_DESCRIPTIONS, WORKFLOW_ORDER

if TYPE_CHECKING:
    from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory


class WorkflowOrchestrator:
    def __init__(self, factory: WorkflowsObjectsFactory) -> None:
        self._factory = factory

    def run(self, ctx: WfCtx) -> None:
        name = ctx.req.workflow
        names = list(WORKFLOW_ORDER) if name == "all" else [name]
        if "cleanup" in names and ctx.req.confirm != "DELETE":
            raise SystemExit("Cleanup requires --confirm DELETE")
        for workflow_name in names:
            workflow = self._factory.workflow(workflow_name)
            if workflow_name == "invoke_agents":
                self._factory.invoke_agents_workspace_facade().question = ctx.req.question
            if workflow_name == "cleanup":
                self._factory.cleanup_workspace_facade().confirm = ctx.req.confirm
            workflow.run()
        ctx.resp.workflow = name
        ctx.resp.status = "ok"

    def deploy(self, ctx: DpCtx) -> None:
        ctx.resp.job_ids = self._factory.jobs_facade().deploy(self.job_specs())
        ctx.resp.status = "ok"

    def trigger(self, ctx: WfCtx) -> None:
        name = ctx.req.workflow
        names = list(WORKFLOW_ORDER) if name == "all" else [name]
        settings = self._factory.settings()
        parameters = {
            "catalog_name": settings.catalog,
            "schema_name": settings.schema,
            "warehouse_id": self._factory.adapter_factory().session().warehouse_id,
            "agent_title": settings.agent_title,
            "space_id": settings.genie_space_id,
            "package_path": settings.package_workspace_path,
            "confirm": ctx.req.confirm,
        }
        specs = {spec.workflow_name: spec for spec in self.job_specs()}
        for workflow_name in names:
            spec = specs.get(workflow_name)
            if spec is None:
                raise SystemExit(f"Unknown workflow {workflow_name!r}")
            self._factory.jobs_facade().trigger(spec.job_name, parameters)
        ctx.resp.workflow = name
        ctx.resp.status = "triggered"
        ctx.resp.message = "Triggered Databricks job"

    def list_workflows(self, ctx: LsCtx) -> None:
        ctx.resp.workflows = [
            WfItem(
                name=spec.workflow_name,
                job_name=spec.job_name,
                description=spec.description or JOB_DESCRIPTIONS.get(spec.workflow_name, ""),
                tasks=[task.key for task in spec.tasks],
            )
            for spec in self.job_specs()
        ]

    def provision_workspace(self, ctx: PwCtx) -> None:
        self._factory.pw_facade().provision(ctx)

    def provision_warehouse(self, ctx: WhCtx) -> None:
        self._factory.wh_facade().provision(ctx)

    def truncate(self, ctx: TcCtx) -> None:
        self._factory.tc_facade().truncate(ctx)

    def destroy(self, ctx: DyCtx) -> None:
        self._factory.dy_facade().destroy(ctx)

    def job_specs(self) -> list[JobSpec]:
        return self._factory.job_specs()


def _assert_protocol() -> None:
    _: type[WorkflowRunner] = WorkflowOrchestrator
