from __future__ import annotations

from typing import Protocol

from ecommerce_genie_ontology.common.dtos.ontology import PwCtx


class PwFacade(Protocol):
    def provision(self, ctx: PwCtx) -> None: ...
