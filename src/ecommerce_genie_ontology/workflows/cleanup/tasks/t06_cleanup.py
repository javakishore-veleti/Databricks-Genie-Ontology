from __future__ import annotations

from ecommerce_genie_ontology.common.interfaces.cleanup import CleanupWorkspaceFacade


class CleanupAssetsTask:
    key = "06_cleanup_delete_all_assets"

    def __init__(self, facade: CleanupWorkspaceFacade) -> None:
        self._facade = facade

    def run(self) -> None:
        if self._facade.confirm != "DELETE":
            raise SystemExit(
                f"Aborted: confirm was '{self._facade.confirm}', expected 'DELETE'. Nothing was deleted."
            )
        self._facade.trash_agent()
        self._facade.drop_catalog()


def run(facade: CleanupWorkspaceFacade) -> None:
    CleanupAssetsTask(facade).run()
