from __future__ import annotations

import time

from databricks.sdk.service.workspace import ImportFormat

from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.paths import PROJECT_ROOT

MCP_APP_NAME = "mcp-ecommerce-oltp"


class AppsDao:
    def __init__(self, session: WorkspaceSession) -> None:
        self._session = session

    @property
    def source_path(self) -> str:
        return f"{self._session.context.package_path.rsplit('/src', 1)[0]}/mcp-app"

    def upload_bundle(self) -> str:
        dest = self.source_path.rstrip("/")
        self._session.workspace.workspace.mkdirs(dest)
        app_root = PROJECT_ROOT / "apps" / MCP_APP_NAME
        uploads: list[tuple[bytes, str]] = [
            (self._rendered_app_yaml(), f"{dest}/app.yaml"),
            ((app_root / "app.py").read_bytes(), f"{dest}/app.py"),
            ((app_root / "requirements.txt").read_bytes(), f"{dest}/requirements.txt"),
            ((PROJECT_ROOT / "pyproject.toml").read_bytes(), f"{dest}/pyproject.toml"),
        ]
        src_root = PROJECT_ROOT / "src"
        for path in sorted(src_root.rglob("*")):
            if not path.is_file() or path.suffix != ".py" or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(src_root).as_posix()
            uploads.append((path.read_bytes(), f"{dest}/src/{rel}"))
        for payload, remote in uploads:
            parent = remote.rsplit("/", 1)[0]
            self._session.workspace.workspace.mkdirs(parent)
            self._session.workspace.workspace.upload(
                remote, payload, overwrite=True, format=ImportFormat.AUTO
            )
            print(f"uploaded {remote}")
        return dest

    def _rendered_app_yaml(self) -> bytes:
        ctx = self._session.context
        return (
            "command:\n"
            "  - python\n"
            "  - app.py\n"
            "env:\n"
            "  - name: MCP_TRANSPORT\n"
            "    value: http\n"
            f"  - name: DATABRICKS_CATALOG\n"
            f"    value: {ctx.catalog}\n"
            f"  - name: DATABRICKS_SCHEMA\n"
            f"    value: {ctx.schema_name}\n"
            f"  - name: DATABRICKS_OLTP_SCHEMA\n"
            f"    value: {ctx.oltp_schema}\n"
            f"  - name: DATABRICKS_WAREHOUSE_ID\n"
            f"    value: {self._session.warehouse_id}\n"
        ).encode()

    def create_or_get(self) -> dict:
        existing = self.get()
        if existing:
            print(f"OK    app {MCP_APP_NAME} exists")
            self._grant_app_principal(existing)
            return existing
        body = {
            "name": MCP_APP_NAME,
            "description": (
                "Custom MCP for fraud analytics sessions on retail_oltp / retail_star. "
                "Tools: initiate_fraud_analytics, record_customer_outcome, close_analytics."
            ),
        }
        self._session.workspace.api_client.do("POST", "/api/2.0/apps", body=body)
        print(f"OK    created app {MCP_APP_NAME}")
        payload = self.get() or {"name": MCP_APP_NAME}
        self._grant_app_principal(payload)
        return payload

    def start(self) -> None:
        app = self.get() or {}
        compute = app.get("compute_status")
        state = str(compute.get("state") if isinstance(compute, dict) else compute or "")
        app_status = app.get("app_status")
        app_state = str(app_status.get("state") if isinstance(app_status, dict) else app_status or "")
        if state.upper() in {"ACTIVE", "RUNNING", "STARTING"} or app_state.upper() in {
            "RUNNING",
            "APP_STARTED",
            "STARTING",
        }:
            print(f"OK    app {MCP_APP_NAME} already {state or app_state}")
            return
        try:
            self._session.workspace.api_client.do("POST", f"/api/2.0/apps/{MCP_APP_NAME}/start")
            print(f"OK    start {MCP_APP_NAME}")
        except Exception as exc:
            text = str(exc).lower()
            if "starting" in text or "already" in text or "running" in text:
                print(f"OK    start skipped ({exc})")
                return
            raise

    def deploy(self, source_code_path: str) -> dict:
        body = {"source_code_path": source_code_path}
        deployment = self._session.workspace.api_client.do(
            "POST", f"/api/2.0/apps/{MCP_APP_NAME}/deployments", body=body
        )
        deployment_id = ""
        if isinstance(deployment, dict):
            deployment_id = str(deployment.get("deployment_id") or deployment.get("id") or "")
        print(f"OK    started deploy {MCP_APP_NAME} {deployment_id}")
        return self.wait_ready(deployment_id)

    def wait_ready(self, deployment_id: str, timeout_s: int = 900) -> dict:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            app = self.get() or {}
            status = str(app.get("compute_status", {}) or "")
            if isinstance(app.get("compute_status"), dict):
                status = str(app["compute_status"].get("state") or "")
            app_status = str(app.get("app_status", {}) or "")
            if isinstance(app.get("app_status"), dict):
                app_status = str(app["app_status"].get("state") or "")
            print(f"app {MCP_APP_NAME} compute={status} app={app_status}")
            if status.upper() in {"ERROR", "CRASHED"} or app_status.upper() in {"ERROR", "FAILED"}:
                raise RuntimeError(f"App {MCP_APP_NAME} failed compute={status} app={app_status}")
            if status.upper() in {"ACTIVE", "RUNNING"} or app_status.upper() in {
                "RUNNING",
                "SUCCEEDED",
                "APP_STARTED",
            }:
                return app
            if deployment_id:
                try:
                    dep = self._session.workspace.api_client.do(
                        "GET", f"/api/2.0/apps/{MCP_APP_NAME}/deployments/{deployment_id}"
                    )
                    dep_state = ""
                    if isinstance(dep, dict):
                        dep_state = str(dep.get("status", {}).get("state") or dep.get("state") or "")
                    print(f"deploy {deployment_id} state={dep_state}")
                    if dep_state.upper() in {"FAILED", "CANCELLED"}:
                        raise RuntimeError(f"App deploy {dep_state}: {dep}")
                except RuntimeError:
                    raise
                except Exception as exc:
                    print(f"SKIP  deploy status -> {exc}")
            time.sleep(10)
        return self.get() or {"name": MCP_APP_NAME}

    def get(self) -> dict | None:
        try:
            result = self._session.workspace.api_client.do("GET", f"/api/2.0/apps/{MCP_APP_NAME}")
        except Exception as exc:
            text = str(exc).lower()
            if "404" in text or "not found" in text or "does not exist" in text:
                return None
            raise
        return result if isinstance(result, dict) else None

    def url(self, app: dict | None = None) -> str:
        payload = app or self.get() or {}
        host = str(payload.get("url") or payload.get("app_url") or "").rstrip("/")
        if host:
            return f"{host}/mcp"
        return ""

    def _grant_app_principal(self, app: dict) -> None:
        principal = str(
            app.get("service_principal_name")
            or app.get("service_principal_client_id")
            or ""
        ).strip()
        if not principal:
            print("SKIP  app principal not on create response")
            return
        warehouse_id = self._session.warehouse_id
        try:
            self._session.workspace.api_client.do(
                "PATCH",
                f"/api/2.0/permissions/sql/warehouses/{warehouse_id}",
                body={
                    "access_control_list": [
                        {
                            "service_principal_name": principal,
                            "permission_level": "CAN_USE",
                        }
                    ]
                },
            )
            print(f"OK    warehouse CAN_USE for {principal}")
        except Exception as exc:
            print(f"SKIP  warehouse grant -> {exc}")
        catalog = self._session.catalog
        for statement in (
            f"GRANT USE CATALOG ON CATALOG {catalog} TO `{principal}`",
            f"GRANT USE SCHEMA ON CATALOG {catalog} TO `{principal}`",
            f"GRANT SELECT ON CATALOG {catalog} TO `{principal}`",
        ):
            try:
                self._session.workspace.statement_execution.execute_statement(
                    warehouse_id=warehouse_id,
                    statement=statement,
                    wait_timeout="50s",
                )
                print(f"OK    {statement}")
            except Exception as exc:
                print(f"SKIP  {statement} -> {exc}")

    def delete(self) -> None:
        try:
            self._session.workspace.api_client.do("DELETE", f"/api/2.0/apps/{MCP_APP_NAME}")
            print(f"OK    deleted app {MCP_APP_NAME}")
        except Exception as exc:
            print(f"SKIP  delete app {MCP_APP_NAME} -> {exc}")
