from __future__ import annotations

from databricks.sdk.service.provisioning import Workspace

from ecommerce_genie_ontology.adapter_databricks.daos.account_dao import AccountDao
from ecommerce_genie_ontology.common.dtos.ontology import PwCtx
from ecommerce_genie_ontology.common.interfaces.pw import PwFacade


class PwFacadeImpl:
    def __init__(self, account_dao: AccountDao) -> None:
        self._account = account_dao

    def provision(self, ctx: PwCtx) -> None:
        name = ctx.req.workspace_name
        existing = self._account.find_by_name(name)
        created = False
        if existing and existing.workspace_id:
            workspace = self._account.wait_running(existing.workspace_id)
        else:
            created = True
            workspace = self._account.create_serverless(
                name=name,
                region=ctx.req.aws_region,
                pricing_tier=ctx.req.pricing_tier,
            )
            if workspace.workspace_id:
                workspace = self._account.wait_running(workspace.workspace_id)
        _fill(ctx, workspace, created)


def _fill(ctx: PwCtx, workspace: Workspace, created: bool) -> None:
    status = workspace.workspace_status.value if workspace.workspace_status else ""
    deployment = workspace.deployment_name or ""
    host = f"https://{deployment}.cloud.databricks.com" if deployment else ""
    ctx.resp.workspace_id = workspace.workspace_id
    ctx.resp.workspace_name = workspace.workspace_name or ctx.req.workspace_name
    ctx.resp.host = host
    ctx.resp.aws_region = workspace.aws_region or ctx.req.aws_region
    ctx.resp.workspace_status = status
    ctx.resp.created = created
    ctx.resp.message = workspace.workspace_status_message or (
        "created" if created else "already existed"
    )


def _assert_protocol() -> None:
    _: type[PwFacade] = PwFacadeImpl
