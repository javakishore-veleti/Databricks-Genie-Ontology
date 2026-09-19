from __future__ import annotations

from typing import Protocol

from ecommerce_genie_ontology.common.dtos.chat import ChCtx


class LgFacade(Protocol):
    """Facade over the LangGraph fraud package. FastAPI never imports LangGraph."""

    def chat(self, ctx: ChCtx) -> None: ...
