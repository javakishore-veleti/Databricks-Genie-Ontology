from __future__ import annotations

from typing import TYPE_CHECKING

from ecommerce_genie_ontology.common.dtos.jobs import JobSpec
from ecommerce_genie_ontology.common.interfaces.workflow import WorkflowRunner
from ecommerce_genie_ontology.workflows.job_specs import WORKFLOW_ORDER

if TYPE_CHECKING:
    from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory


class WorkflowOrchestrator:
    def __init__(self, factory: WorkflowsObjectsFactory) -> None:
        self._factory = factory

    def run(self, name: str, question: str = "", confirm: str = "") -> None:
        names = list(WORKFLOW_ORDER) if name == "all" else [name]
        if "cleanup" in names and confirm != "DELETE":
            raise SystemExit("Cleanup requires --confirm DELETE")
        for workflow_name in names:
            workflow = self._factory.workflow(workflow_name)
            if workflow_name == "invoke_agents":
                self._factory.invoke_agents_workspace_facade().question = question
            if workflow_name == "cleanup":
                self._factory.cleanup_workspace_facade().confirm = confirm
            workflow.run()

    def deploy(self) -> dict[str, int]:
        return self._factory.jobs_facade().deploy(self.job_specs())

    def trigger(self, name: str, confirm: str = "") -> None:
        names = list(WORKFLOW_ORDER) if name == "all" else [name]
        settings = self._factory.settings()
        parameters = {
            "catalog_name": settings.catalog,
            "schema_name": settings.schema,
            "warehouse_id": settings.warehouse_id,
            "agent_title": settings.agent_title,
            "space_id": settings.genie_space_id,
            "package_path": settings.package_workspace_path,
            "confirm": confirm,
        }
        specs = {spec.workflow_name: spec for spec in self.job_specs()}
        for workflow_name in names:
            spec = specs.get(workflow_name)
            if spec is None:
                raise SystemExit(f"Unknown workflow {workflow_name!r}")
            self._factory.jobs_facade().trigger(spec.job_name, parameters)

    def job_specs(self) -> list[JobSpec]:
        return self._factory.job_specs()


def _assert_protocol() -> None:
    _: type[WorkflowRunner] = WorkflowOrchestrator
