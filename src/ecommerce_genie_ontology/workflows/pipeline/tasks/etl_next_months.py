from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.facades.pipeline_facade import PipelineFacadeImpl


class EtlNextMonthsTask:
    key = "etl_next_months"

    def __init__(self, facade: PipelineFacadeImpl) -> None:
        self._facade = facade

    def run(self) -> None:
        self._facade.run_etl_next_months()


def run(facade: PipelineFacadeImpl) -> None:
    EtlNextMonthsTask(facade).run()
