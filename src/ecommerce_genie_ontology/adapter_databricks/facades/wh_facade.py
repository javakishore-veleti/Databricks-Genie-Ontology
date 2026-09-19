from __future__ import annotations

from datetime import timedelta

from databricks.sdk.errors import DatabricksError
from databricks.sdk.service.sql import CreateWarehouseRequestWarehouseType

from ecommerce_genie_ontology.adapter_databricks.daos.account_dao import AccountDao
from ecommerce_genie_ontology.common.dtos.ontology import WhCtx
from ecommerce_genie_ontology.common.interfaces.wh import WhFacade


class WhFacadeImpl:
    def __init__(self, account_dao: AccountDao) -> None:
        self._account = account_dao

    def provision(self, ctx: WhCtx) -> None:
        workspace = self._account.find_by_name(ctx.req.workspace_name)
        if workspace is None or not workspace.workspace_id:
            raise RuntimeError(
                f"Workspace {ctx.req.workspace_name!r} not found. "
                "Run npm run ecommerce:workspace:databricks-setup first."
            )
        self._account.assign_workspace_admins(workspace, [])
        client = self._account.workspace_client(workspace)
        host = (
            f"https://{workspace.deployment_name}.cloud.databricks.com"
            if workspace.deployment_name
            else ""
        )
        existing = self._find_warehouse(client, ctx.req.warehouse_name)
        created = False
        try:
            if existing is not None and existing.id:
                warehouse = existing
            else:
                created = True
                warehouse = client.warehouses.create_and_wait(
                    name=ctx.req.warehouse_name,
                    cluster_size=ctx.req.cluster_size,
                    auto_stop_mins=ctx.req.auto_stop_mins,
                    min_num_clusters=max(ctx.req.min_num_clusters, 1),
                    max_num_clusters=max(ctx.req.max_num_clusters, 1),
                    enable_serverless_compute=True,
                    warehouse_type=CreateWarehouseRequestWarehouseType.PRO,
                    timeout=timedelta(minutes=20),
                )
            if warehouse.id:
                warehouse = client.warehouses.wait_get_warehouse_running(warehouse.id)
        except DatabricksError as exc:
            raise RuntimeError(str(exc)) from exc
        ctx.resp.warehouse_id = warehouse.id or ""
        ctx.resp.warehouse_name = warehouse.name or ctx.req.warehouse_name
        ctx.resp.host = host
        ctx.resp.state = warehouse.state.value if getattr(warehouse, "state", None) else ""
        ctx.resp.created = created
        ctx.resp.message = "created" if created else "already existed"
        print(f"warehouse {ctx.resp.warehouse_id} status={ctx.resp.state} {ctx.resp.message}")

    def _find_warehouse(self, client, name: str):
        for warehouse in client.warehouses.list():
            if warehouse.name == name:
                return warehouse
        return None


def _assert_protocol() -> None:
    _: type[WhFacade] = WhFacadeImpl
