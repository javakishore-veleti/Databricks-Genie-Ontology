from __future__ import annotations

import time
from datetime import timedelta

from databricks.sdk.errors import DatabricksError, NotFound
from databricks.sdk.service.iam import WorkspacePermission
try:
    from databricks.sdk.service.iamv2 import Entitlement, FieldMask, WorkspaceAssignment
except ImportError:  # Databricks job runtime SDK can be older than uv
    Entitlement = None
    FieldMask = None
    WorkspaceAssignment = None
try:
    from databricks.sdk.service.provisioning import CustomerFacingComputeMode, PricingTier, Workspace
except ImportError:  # Databricks job runtime SDK can be older than uv
    CustomerFacingComputeMode = None
    PricingTier = None
    Workspace = None

from ecommerce_genie_ontology.adapter_databricks.account_session import AccountSession

_ADMIN_ENTITLEMENTS = (
    [
        Entitlement.WORKSPACE_ACCESS,
        Entitlement.DATABRICKS_SQL_ACCESS,
        Entitlement.WORKSPACE_ADMIN,
        Entitlement.ALLOW_CLUSTER_CREATE,
    ]
    if Entitlement is not None
    else [
        "WORKSPACE_ACCESS",
        "DATABRICKS_SQL_ACCESS",
        "WORKSPACE_ADMIN",
        "ALLOW_CLUSTER_CREATE",
    ]
)


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

    def workspace_client(self, workspace: Workspace):
        return self._session.account.get_workspace_client(workspace)

    @property
    def settings(self):
        return self._session.settings

    def assign_workspace_admins(self, workspace: Workspace, emails: list[str]) -> list[str]:
        assigned: list[str] = []
        if not workspace.workspace_id:
            return assigned
        workspace_id = workspace.workspace_id
        sp_id = self._service_principal_id()
        if sp_id is not None:
            if self._assign_admin(workspace_id, sp_id):
                assigned.append(f"sp:{sp_id}")
        for raw in emails:
            email = raw.strip()
            if not email:
                continue
            user_id = self._user_id_by_email(email)
            if user_id is None:
                print(f"SKIP  account user not found")
                continue
            if self._assign_admin(workspace_id, user_id):
                assigned.append(f"user:{user_id}")
        return assigned

    def _assign_admin(self, workspace_id: int, principal_id: int) -> bool:
        legacy_ok = False
        try:
            self._session.account.workspace_assignment.update(
                workspace_id,
                principal_id,
                permissions=[WorkspacePermission.ADMIN],
            )
            print(f"OK    assigned workspace ADMIN to principal {principal_id}")
            legacy_ok = True
        except DatabricksError as exc:
            print(f"SKIP  workspace assignment {principal_id} -> {exc}")
        iam_ok = self._assign_iam_v2_entitlements(workspace_id, principal_id)
        return legacy_ok or iam_ok

    def _assign_iam_v2_entitlements(self, workspace_id: int, principal_id: int) -> bool:
        if WorkspaceAssignment is None or FieldMask is None:
            print("SKIP  iam_v2 entitlements (runtime SDK has no Entitlement)")
            return False
        assignment = WorkspaceAssignment(
            principal_id=principal_id,
            workspace_id=workspace_id,
            entitlements=list(_ADMIN_ENTITLEMENTS),
        )
        iam = self._session.account.iam_v2
        try:
            existing = iam.get_workspace_assignment(workspace_id, principal_id)
        except DatabricksError:
            existing = None
        try:
            if existing is None:
                result = iam.create_workspace_assignment(workspace_id, assignment)
            else:
                result = iam.update_workspace_assignment(
                    workspace_id,
                    principal_id,
                    assignment,
                    FieldMask(["entitlements"]),
                )
            entitlements = [item.value for item in (result.entitlements or [])]
            print(f"OK    iam_v2 entitlements principal {principal_id} -> {entitlements}")
            return True
        except DatabricksError as exc:
            print(f"SKIP  iam_v2 entitlements {principal_id} -> {exc}")
            return False

    def _service_principal_id(self) -> int | None:
        client_id = self._session.settings.client_id
        if not client_id:
            return None
        try:
            principals = self._session.account.service_principals.list()
        except DatabricksError as exc:
            print(f"SKIP  list service principals -> {exc}")
            return None
        for principal in principals:
            application_id = getattr(principal, "application_id", None)
            identifier = str(getattr(principal, "id", "") or "")
            if application_id == client_id or identifier == client_id:
                try:
                    return int(identifier)
                except ValueError:
                    return None
        return None

    def _user_id_by_email(self, email: str) -> int | None:
        wanted = email.lower()
        try:
            users = list(self._session.account.users.list(filter=f'userName eq "{email}"'))
        except DatabricksError:
            users = []
        if not users:
            try:
                users = list(self._session.account.users.list())
            except DatabricksError as exc:
                print(f"SKIP  list account users -> {exc}")
                return None
        for user in users:
            if (user.user_name or "").lower() == wanted:
                return _int_id(user.id)
            for item in user.emails or []:
                if (item.value or "").lower() == wanted:
                    return _int_id(user.id)
        return None

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

    def delete(self, workspace_id: int) -> None:
        self._session.account.workspaces.delete(workspace_id)
        print(f"OK    requested delete workspace {workspace_id}")

    def wait_deleted(self, workspace_id: int, timeout_s: int = 1200) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                workspace = self.get(workspace_id)
            except NotFound:
                print(f"workspace {workspace_id} deleted")
                return
            except DatabricksError as exc:
                text = str(exc).lower()
                if "404" in text or "not found" in text or "does not exist" in text:
                    print(f"workspace {workspace_id} deleted")
                    return
                raise
            status = workspace.workspace_status.value if workspace.workspace_status else ""
            message = workspace.workspace_status_message or ""
            print(f"workspace {workspace_id} status={status} {message}")
            if status in {"CANCELLED", "BANNED"}:
                print(f"workspace {workspace_id} deleted")
                return
            time.sleep(10)
        raise TimeoutError(f"Workspace {workspace_id} did not finish deleting within {timeout_s}s")


def _int_id(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
