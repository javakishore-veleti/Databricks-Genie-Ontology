from __future__ import annotations

from typing import Protocol

from ecommerce_genie_ontology.common.dtos.ontology import TcCtx


class TcFacade(Protocol):
    def truncate(self, ctx: TcCtx) -> None: ...
