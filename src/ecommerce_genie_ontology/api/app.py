from __future__ import annotations

from fastapi import FastAPI

from ecommerce_genie_ontology.api.objects_factory import ApiObjectsFactory
from ecommerce_genie_ontology.api.routers import HealthRouter, WorkflowsRouter


class ApiApp:
    def __init__(self, health: HealthRouter, workflows: WorkflowsRouter) -> None:
        self._app = FastAPI(
            title="Ecommerce Genie Ontology",
            description=(
                "HTTP entry for provisioning the ecommerce Genie Ontology demo, "
                "creating Genie agents, and invoking them."
            ),
        )
        self._app.include_router(health.router)
        self._app.include_router(workflows.router)

    def asgi(self) -> FastAPI:
        return self._app


def create_app() -> FastAPI:
    return ApiObjectsFactory.instance().api_app().asgi()


app = create_app()
