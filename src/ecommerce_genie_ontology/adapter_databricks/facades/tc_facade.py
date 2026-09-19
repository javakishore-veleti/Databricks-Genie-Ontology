from __future__ import annotations

import re

from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.dtos.ontology import TcCtx
from ecommerce_genie_ontology.common.interfaces.genie import GenieFacade
from ecommerce_genie_ontology.common.interfaces.sql import SqlFacade
from ecommerce_genie_ontology.common.interfaces.tc import TcFacade

_CATALOG_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PROTECTED = frozenset(
    {"hive_metastore", "system", "samples", "information_schema", "main", "spark_catalog"}
)


class TcFacadeImpl:
    def __init__(self, session: WorkspaceSession, sql: SqlFacade, genie: GenieFacade) -> None:
        self._session = session
        self._sql = sql
        self._genie = genie

    def truncate(self, ctx: TcCtx) -> None:
        if ctx.req.confirm != "DELETE":
            raise SystemExit("Truncate requires confirm=DELETE")
        catalog = (ctx.req.catalog or self._session.catalog).strip()
        _assert_droppable(catalog)
        agent_trashed = False
        try:
            self._genie.trash_agent()
            agent_trashed = True
        except Exception as exc:
            print(f"SKIP  trash agent -> {exc}")
        self._sql.execute(f"DROP CATALOG IF EXISTS {catalog} CASCADE")
        print(f"Dropped catalog {catalog} (schema, tables, and metric views removed).")
        ctx.resp.catalog = catalog
        ctx.resp.dropped = True
        ctx.resp.agent_trashed = agent_trashed
        ctx.resp.message = f"Dropped catalog {catalog}"


def _assert_droppable(catalog: str) -> None:
    if not _CATALOG_NAME.fullmatch(catalog):
        raise SystemExit(f"Invalid catalog name {catalog!r}")
    if catalog.lower() in _PROTECTED:
        raise SystemExit(f"Refusing to drop protected catalog {catalog!r}")


def _assert_protocol() -> None:
    _: type[TcFacade] = TcFacadeImpl
