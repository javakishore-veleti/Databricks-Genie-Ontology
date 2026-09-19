from __future__ import annotations

import time
from datetime import timedelta

from databricks.sdk.service.provisioning import CustomerFacingComputeMode, PricingTier, Workspace

from ecommerce_genie_ontology.adapter_databricks.account_session import AccountSession


class AccountDao:
    def __init__(self, session: AccountSession) -> None:
        self._session = session

    def find_by_name(self, name: str) -> Workspace | None:
        for workspace in self._session.account.workspaces.list():
            if workspace.workspace_name == name:
                return workspace
        return None

    def create_serverless(self, name: str, region: str, pricing_tier: str) -> Workspace:
        tier = PricingTier[pricing_tier] if pricing_tier in PricingTier.__members__ else PricingTier.PREMIUM
        waiter = self._session.account.workspaces.create(
            workspace_name=name,
            aws_region=region,
            pricing_tier=tier,
            compute_mode=CustomerFacingComputeMode.SERVERLESS,
        )
        workspace = waiter.result(timeout=timedelta(minutes=20)) if hasattr(waiter, "result") else waiter
        return workspace

    def get(self, workspace_id: int) -> Workspace:
        return self._session.account.workspaces.get(workspace_id)

    def wait_running(self, workspace_id: int, timeout_s: int = 1200) -> Workspace:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            workspace = self.get(workspace_id)
            status = workspace.workspace_status.value if workspace.workspace_status else ""
            message = workspace.workspace_status_message or ""
            print(f"workspace {workspace_id} status={status} {message}")
            if status == "RUNNING":
                return workspace
            if status in {"FAILED", "BANNED", "CANCELLING"}:
                raise RuntimeError(f"Workspace {workspace_id} ended in {status}: {message}")
            time.sleep(10)
        raise TimeoutError(f"Workspace {workspace_id} did not reach RUNNING within {timeout_s}s")
