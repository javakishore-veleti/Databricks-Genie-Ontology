from __future__ import annotations

from typing import Protocol

from ecommerce_genie_ontology.common.dtos.chat import ChCtx


class GaFacade(Protocol):
    """Facade over the Google ADK fraud package. FastAPI never imports google.adk."""

    def chat(self, ctx: ChCtx) -> None: ...
