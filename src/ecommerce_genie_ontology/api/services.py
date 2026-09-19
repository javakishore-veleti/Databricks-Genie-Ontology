from __future__ import annotations

from ecommerce_genie_ontology.common.dtos.workflow import WorkflowRunRequest, WorkflowRunResult
from ecommerce_genie_ontology.common.interfaces.workflow import WorkflowRunner
from ecommerce_genie_ontology.workflows.job_specs import JOB_DESCRIPTIONS, JOB_NAMES


class WorkflowsApiService:
    def __init__(self, runner: WorkflowRunner) -> None:
        self._runner = runner

    def list_workflows(self) -> list[dict]:
        summaries = []
        for spec in self._runner.job_specs():
            summaries.append(
                {
                    "name": spec.workflow_name,
                    "job_name": spec.job_name,
                    "description": spec.description or JOB_DESCRIPTIONS.get(spec.workflow_name, ""),
                    "tasks": [task.key for task in spec.tasks],
                }
            )
        return summaries

    def run(self, request: WorkflowRunRequest) -> WorkflowRunResult:
        if request.as_job:
            self._runner.trigger(request.workflow, confirm=request.confirm)
            return WorkflowRunResult(
                workflow=request.workflow,
                status="triggered",
                message=f"Triggered Databricks job {JOB_NAMES.get(request.workflow, request.workflow)}",
            )
        self._runner.run(request.workflow, question=request.question, confirm=request.confirm)
        return WorkflowRunResult(workflow=request.workflow, status="ok")

    def deploy(self) -> dict[str, int]:
        return self._runner.deploy()
