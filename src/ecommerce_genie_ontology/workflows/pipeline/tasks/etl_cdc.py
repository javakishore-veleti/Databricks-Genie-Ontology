from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.facades.pipeline_facade import PipelineFacadeImpl


class EtlCdcTask:
    key = "etl_cdc"

    def __init__(self, facade: PipelineFacadeImpl) -> None:
        self._facade = facade

    def run(self) -> None:
        self._facade.run_etl_cdc()


def run(facade: PipelineFacadeImpl) -> None:
    EtlCdcTask(facade).run()
