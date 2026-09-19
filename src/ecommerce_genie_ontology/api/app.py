from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ecommerce_genie_ontology.api.objects_factory import ApiObjectsFactory
from ecommerce_genie_ontology.api.routers import HealthRouter, OntologyRouter


class ApiApp:
    def __init__(self, health: HealthRouter, ontology: OntologyRouter) -> None:
        self._app = FastAPI(
            title="Ecommerce Genie Ontology",
            description=(
                "HTTP entry for provisioning the ecommerce Genie Ontology demo, "
                "generating OLTP/CDC data, running star-schema ETL, and fraud chat "
                "(LangGraph, Google ADK, or Databricks Genie facades)."
            ),
        )
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._app.include_router(health.router)
        self._app.include_router(ontology.router)

    def asgi(self) -> FastAPI:
        return self._app


def create_app() -> FastAPI:
    return ApiObjectsFactory.instance().api_app().asgi()


app = create_app()
