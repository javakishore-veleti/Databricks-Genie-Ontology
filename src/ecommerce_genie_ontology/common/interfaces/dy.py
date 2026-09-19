from __future__ import annotations

from typing import Protocol

from ecommerce_genie_ontology.common.dtos.ontology import DyCtx


class DyFacade(Protocol):
    def destroy(self, ctx: DyCtx) -> None: ...
