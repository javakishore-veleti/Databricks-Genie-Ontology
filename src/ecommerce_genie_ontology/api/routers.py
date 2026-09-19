from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ecommerce_genie_ontology.api.schemas import (
    DeployResponse,
    WorkflowRunBody,
    WorkflowRunResponse,
    WorkflowSummary,
)
from ecommerce_genie_ontology.api.services import WorkflowsApiService
from ecommerce_genie_ontology.common.dtos.workflow import WorkflowRunRequest


class HealthRouter:
    def __init__(self) -> None:
        self.router = APIRouter(tags=["health"])
        self.router.add_api_route("/health", self.health, methods=["GET"])

    def health(self) -> dict[str, str]:
        return {"status": "ok"}


class WorkflowsRouter:
    def __init__(self, service: WorkflowsApiService) -> None:
        self._service = service
        self.router = APIRouter(prefix="/workflows", tags=["workflows"])
        self.router.add_api_route("", self.list_workflows, methods=["GET"])
        self.router.add_api_route("/deploy", self.deploy, methods=["POST"])
        self.router.add_api_route("/{name}/run", self.run_workflow, methods=["POST"])

    def list_workflows(self) -> list[WorkflowSummary]:
        return [WorkflowSummary.model_validate(item) for item in self._service.list_workflows()]

    def run_workflow(self, name: str, body: WorkflowRunBody | None = None) -> WorkflowRunResponse:
        payload = body or WorkflowRunBody()
        try:
            result = self._service.run(
                WorkflowRunRequest(
                    workflow=name,
                    question=payload.question,
                    confirm=payload.confirm,
                    as_job=payload.as_job,
                )
            )
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return WorkflowRunResponse(
            workflow=result.workflow,
            status=result.status,
            message=result.message,
        )

    def deploy(self) -> DeployResponse:
        job_ids = self._service.deploy()
        return DeployResponse(status="ok", job_ids=job_ids)
