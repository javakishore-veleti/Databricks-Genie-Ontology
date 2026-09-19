from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.facades.pipeline_facade import PipelineFacadeImpl


class GenerateRealtimeTask:
    key = "generate_realtime"

    def __init__(self, facade: PipelineFacadeImpl) -> None:
        self._facade = facade

    def run(self) -> None:
        self._facade.run_generate_realtime()


def run(facade: PipelineFacadeImpl) -> None:
    GenerateRealtimeTask(facade).run()
