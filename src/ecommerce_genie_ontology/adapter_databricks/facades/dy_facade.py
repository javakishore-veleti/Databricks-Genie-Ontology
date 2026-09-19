from __future__ import annotations

import time

from databricks.sdk.errors import DatabricksError
from databricks.sdk.service.sql import StatementState

from ecommerce_genie_ontology.adapter_databricks.daos.account_dao import AccountDao
from ecommerce_genie_ontology.adapter_databricks.facades.tc_facade import _assert_droppable
from ecommerce_genie_ontology.common.dtos.ontology import DyCtx
from ecommerce_genie_ontology.common.dtos.settings import Settings
from ecommerce_genie_ontology.common.interfaces.dy import DyFacade

_PENDING = {
    getattr(StatementState, name)
    for name in ("PENDING", "RUNNING")
    if hasattr(StatementState, name)
}
_SUCCESS = {
    getattr(StatementState, name)
    for name in ("SUCCEEDED", "SUCCESS")
    if hasattr(StatementState, name)
}


class DyFacadeImpl:
    def __init__(self, account_dao: AccountDao, settings: Settings) -> None:
        self._account = account_dao
        self._settings = settings

    def destroy(self, ctx: DyCtx) -> None:
        if ctx.req.confirm != "DELETE":
            raise SystemExit("Destroy requires confirm=DELETE")
        workspace_name = (ctx.req.workspace_name or self._account.settings.workspace_name).strip()
        warehouse_name = (ctx.req.warehouse_name or self._settings.warehouse_name).strip()
        catalog = (ctx.req.catalog or self._settings.catalog).strip()
        if workspace_name != self._account.settings.workspace_name:
            raise SystemExit(f"Refusing to delete workspace {workspace_name!r}")
        if warehouse_name != self._settings.warehouse_name:
            raise SystemExit(f"Refusing to delete warehouse {warehouse_name!r}")
        _assert_droppable(catalog)
        if catalog != self._settings.catalog:
            raise SystemExit(f"Refusing to drop catalog {catalog!r}")

        ctx.resp.workspace_name = workspace_name
        ctx.resp.warehouse_name = warehouse_name
        ctx.resp.catalog = catalog
        notes: list[str] = []

        workspace = self._account.find_by_name(workspace_name)
        if workspace is None or not workspace.workspace_id:
            notes.append("workspace already gone")
            ctx.resp.workspace_deleted = True
            ctx.resp.warehouse_deleted = True
            ctx.resp.catalog_dropped = True
            ctx.resp.message = "; ".join(notes)
            print(ctx.resp.message)
            return

        client = self._account.workspace_client(workspace)
        _delete_mcp_app(client, notes)
        warehouse = _find_warehouse(client, warehouse_name)
        if warehouse is not None and warehouse.id:
            try:
                _ensure_warehouse_running(client, warehouse.id)
                _drop_catalog(client, warehouse.id, catalog)
                ctx.resp.catalog_dropped = True
                notes.append(f"dropped catalog {catalog}")
            except Exception as exc:
                notes.append(f"catalog drop skipped: {exc}")
            try:
                client.warehouses.delete(id=warehouse.id)
                ctx.resp.warehouse_deleted = True
                notes.append(f"deleted warehouse {warehouse_name}")
                print(f"OK    deleted warehouse {warehouse.id}")
            except DatabricksError as exc:
                notes.append(f"warehouse delete skipped: {exc}")
        else:
            ctx.resp.warehouse_deleted = True
            notes.append("warehouse already gone")
            try:
                _drop_catalog_without_warehouse(client, catalog)
                ctx.resp.catalog_dropped = True
                notes.append(f"dropped catalog {catalog}")
            except Exception as exc:
                notes.append(f"catalog drop skipped: {exc}")

        self._account.delete(workspace.workspace_id)
        self._account.wait_deleted(workspace.workspace_id)
        ctx.resp.workspace_deleted = True
        notes.append(f"deleted workspace {workspace_name}")
        ctx.resp.message = "; ".join(notes)
        print(ctx.resp.message)


def _delete_mcp_app(client, notes: list[str]) -> None:
    from ecommerce_genie_ontology.adapter_databricks.daos.apps_dao import MCP_APP_NAME

    try:
        client.api_client.do("DELETE", f"/api/2.0/apps/{MCP_APP_NAME}")
        notes.append(f"deleted app {MCP_APP_NAME}")
        print(f"OK    deleted app {MCP_APP_NAME}")
    except Exception as exc:
        notes.append(f"app delete skipped: {exc}")
        print(f"SKIP  delete app {MCP_APP_NAME} -> {exc}")


def _find_warehouse(client, name: str):
    for warehouse in client.warehouses.list():
        if warehouse.name == name:
            return warehouse
    return None


def _ensure_warehouse_running(client, warehouse_id: str) -> None:
    warehouse = client.warehouses.get(warehouse_id)
    state = warehouse.state.value if getattr(warehouse, "state", None) else ""
    if state in {"RUNNING", "STARTING"}:
        if state == "STARTING":
            client.warehouses.wait_get_warehouse_running(warehouse_id)
        return
    if hasattr(client.warehouses, "start_and_wait"):
        client.warehouses.start_and_wait(warehouse_id)
        return
    client.warehouses.start(warehouse_id)
    client.warehouses.wait_get_warehouse_running(warehouse_id)


def _drop_catalog(client, warehouse_id: str, catalog: str) -> None:
    statement = f"DROP CATALOG IF EXISTS {catalog} CASCADE"
    result = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=statement,
        wait_timeout="50s",
    )
    deadline = time.time() + 600
    while result.status and result.status.state in _PENDING:
        if time.time() > deadline:
            raise TimeoutError(f"SQL timed out: {statement}")
        time.sleep(2)
        if not result.statement_id:
            break
        result = client.statement_execution.get_statement(result.statement_id)
    state = result.status.state if result.status else None
    if state is None or state in _SUCCESS:
        print(f"OK    {statement}")
        return
    message = ""
    if result.status and result.status.error:
        message = result.status.error.message or str(result.status.error)
    raise RuntimeError(message or statement)


def _drop_catalog_without_warehouse(client, catalog: str) -> None:
    client.catalogs.delete(catalog, force=True)
    print(f"OK    deleted catalog {catalog}")


def _assert_protocol() -> None:
    _: type[DyFacade] = DyFacadeImpl
