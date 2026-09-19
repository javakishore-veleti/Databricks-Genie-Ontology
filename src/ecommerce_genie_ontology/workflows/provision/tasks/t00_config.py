from __future__ import annotations

from ecommerce_genie_ontology.common.interfaces.provision import ProvisionWorkspaceFacade


class PrintConfigTask:
    key = "00_config"

    def __init__(self, facade: ProvisionWorkspaceFacade) -> None:
        self._facade = facade

    def run(self) -> None:
        print(f"CATALOG       = {self._facade.catalog}")
        print(f"SCHEMA        = {self._facade.schema_name}")
        print(f"FQ_SCHEMA     = {self._facade.fq_schema}")
        print(f"WAREHOUSE_ID  = {self._facade.warehouse_id}")
        print(f"AGENT_TITLE   = {self._facade.agent_title}")


def run(facade: ProvisionWorkspaceFacade) -> None:
    PrintConfigTask(facade).run()
