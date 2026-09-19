from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.facades.pipeline_facade import PipelineFacadeImpl


class GenerateNextOltpTask:
    key = "generate_next_oltp"

    def __init__(self, facade: PipelineFacadeImpl) -> None:
        self._facade = facade

    def run(self) -> None:
        self._facade.run_generate_next_oltp()


def run(facade: PipelineFacadeImpl) -> None:
    GenerateNextOltpTask(facade).run()
