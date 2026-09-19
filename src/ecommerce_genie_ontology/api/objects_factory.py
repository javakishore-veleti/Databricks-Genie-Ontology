"""Singleton lookup for FastAPI app, routers, and API services."""

from __future__ import annotations

from ecommerce_genie_ontology.api.routers import HealthRouter, WorkflowsRouter
from ecommerce_genie_ontology.api.services import WorkflowsApiService
from ecommerce_genie_ontology.common.interfaces.workflow import WorkflowRunner
from ecommerce_genie_ontology.common.utils.objects_factory import ObjectsFactory
from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory


class ApiObjectsFactory(ObjectsFactory):
    @classmethod
    def instance(cls) -> ApiObjectsFactory:
        return super().instance()  # type: ignore[return-value]

    def workflows_factory(self) -> WorkflowsObjectsFactory:
        return WorkflowsObjectsFactory.instance()

    def workflow_runner(self) -> WorkflowRunner:
        return self.workflows_factory().orchestrator()

    def workflows_service(self) -> WorkflowsApiService:
        return self.singleton("workflows_service", lambda: WorkflowsApiService(self.workflow_runner()))

    def health_router(self) -> HealthRouter:
        return self.singleton("health_router", HealthRouter)

    def workflows_router(self) -> WorkflowsRouter:
        return self.singleton("workflows_router", lambda: WorkflowsRouter(self.workflows_service()))

    def api_app(self):
        from ecommerce_genie_ontology.api.app import ApiApp

        return self.singleton(
            "api_app",
            lambda: ApiApp(self.health_router(), self.workflows_router()),
        )
