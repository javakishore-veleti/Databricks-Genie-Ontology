from __future__ import annotations

from typing import Protocol

from ecommerce_genie_ontology.common.dtos.pipeline import EcCtx, EhCtx, FcCtx, OdCtx, OhCtx


class PipelineFacade(Protocol):
    def generate_historical(self, ctx: OhCtx) -> None: ...

    def generate_realtime(self, ctx: OdCtx) -> None: ...

    def etl_historical(self, ctx: EhCtx) -> None: ...

    def etl_cdc(self, ctx: EcCtx) -> None: ...

    def run_fraud_case(self, ctx: FcCtx) -> None: ...
