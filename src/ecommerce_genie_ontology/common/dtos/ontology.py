from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field


class HlReq(BaseModel):
    """OpenAPI request model for `GET /health`."""

    model_config = ConfigDict(title="HlReq")


@dataclass
class HlResp:
    status: str = "ok"


class HlRespResult(BaseModel):
    """OpenAPI result for `GET /health`."""

    model_config = ConfigDict(title="HlRespResult")
    status: str = Field(default="ok", description="Liveness status.")

    @classmethod
    def of(cls, resp: HlResp) -> HlRespResult:
        return cls(status=resp.status)


class HlCtx:
    def __init__(self, req: HlReq, resp: HlResp) -> None:
        self.req = req
        self.resp = resp


class LsReq(BaseModel):
    """OpenAPI request model for `GET /api/v1/ontology/workflows`."""

    model_config = ConfigDict(title="LsReq")


@dataclass
class WfItem:
    name: str
    job_name: str
    description: str = ""
    tasks: list[str] = field(default_factory=list)


@dataclass
class LsResp:
    workflows: list[WfItem] = field(default_factory=list)


class WfItemResult(BaseModel):
    model_config = ConfigDict(title="WfItemResult")
    name: str
    job_name: str
    description: str = ""
    tasks: list[str] = Field(default_factory=list)


class LsRespResult(BaseModel):
    """OpenAPI result for listing workflows."""

    model_config = ConfigDict(title="LsRespResult")
    workflows: list[WfItemResult] = Field(default_factory=list)

    @classmethod
    def of(cls, resp: LsResp) -> LsRespResult:
        return cls(
            workflows=[
                WfItemResult(
                    name=item.name,
                    job_name=item.job_name,
                    description=item.description,
                    tasks=list(item.tasks),
                )
                for item in resp.workflows
            ]
        )


class LsCtx:
    def __init__(self, req: LsReq, resp: LsResp) -> None:
        self.req = req
        self.resp = resp


class WfReq(BaseModel):
    """OpenAPI request body for running a Genie Ontology workflow."""

    model_config = ConfigDict(
        title="WfReq",
        json_schema_extra={
            "examples": [
                {
                    "workflow": "provision",
                    "question": "",
                    "confirm": "",
                    "as_job": False,
                }
            ]
        },
    )
    workflow: str = Field(
        default="provision",
        description="Workflow to run: provision, create_agents, invoke_agents, cleanup, or all.",
        examples=["provision"],
    )
    question: str = Field(default="", description="Optional single question for invoke_agents.")
    confirm: str = Field(default="", description="Must be DELETE for cleanup.")
    as_job: bool = Field(default=False, description="If true, trigger the deployed Databricks job.")


@dataclass
class WfResp:
    workflow: str = ""
    status: str = ""
    message: str = ""


class WfRespResult(BaseModel):
    """OpenAPI result for running a workflow."""

    model_config = ConfigDict(title="WfRespResult")
    workflow: str = ""
    status: str = ""
    message: str = ""

    @classmethod
    def of(cls, resp: WfResp) -> WfRespResult:
        return cls(workflow=resp.workflow, status=resp.status, message=resp.message)


class WfCtx:
    def __init__(self, req: WfReq, resp: WfResp) -> None:
        self.req = req
        self.resp = resp


class DpReq(BaseModel):
    """OpenAPI request body for deploying Databricks jobs."""

    model_config = ConfigDict(title="DpReq")


@dataclass
class DpResp:
    status: str = ""
    job_ids: dict[str, int] = field(default_factory=dict)
    message: str = ""


class DpRespResult(BaseModel):
    """OpenAPI result for deploying jobs."""

    model_config = ConfigDict(title="DpRespResult")
    status: str = ""
    job_ids: dict[str, int] = Field(default_factory=dict)
    message: str = ""

    @classmethod
    def of(cls, resp: DpResp) -> DpRespResult:
        return cls(status=resp.status, job_ids=dict(resp.job_ids), message=resp.message)


class DpCtx:
    def __init__(self, req: DpReq, resp: DpResp) -> None:
        self.req = req
        self.resp = resp


class PwReq(BaseModel):
    """OpenAPI request body for `POST /api/v1/ontology/provision-workspace`."""

    model_config = ConfigDict(
        title="PwReq",
        json_schema_extra={
            "examples": [
                {
                    "workspace_name": "ecommerce-genie-ontology",
                    "aws_region": "us-east-1",
                    "pricing_tier": "PREMIUM",
                    "compute_mode": "SERVERLESS",
                    "admin_emails": ["you@example.com"],
                }
            ]
        },
    )
    workspace_name: str = Field(
        default="ecommerce-genie-ontology",
        description="Databricks workspace display name.",
        examples=["ecommerce-genie-ontology"],
    )
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region that supports serverless compute.",
        examples=["us-east-1"],
    )
    pricing_tier: str = Field(default="PREMIUM", description="Databricks pricing tier.")
    compute_mode: str = Field(
        default="SERVERLESS",
        description="SERVERLESS uses default storage; HYBRID needs your cloud account.",
        examples=["SERVERLESS"],
    )
    admin_emails: list[str] = Field(
        default_factory=list,
        description="Account users to assign as workspace ADMIN so they can open the workspace UI.",
        examples=[["you@example.com"]],
    )


@dataclass
class PwResp:
    workspace_id: int | None = None
    workspace_name: str = ""
    host: str = ""
    aws_region: str = ""
    workspace_status: str = ""
    created: bool = False
    message: str = ""


class PwRespResult(BaseModel):
    """OpenAPI result for provisioning a Databricks workspace."""

    model_config = ConfigDict(title="PwRespResult")
    workspace_id: int | None = None
    workspace_name: str = ""
    host: str = ""
    status: str = ""
    created: bool = False
    message: str = ""

    @classmethod
    def of(cls, resp: PwResp) -> PwRespResult:
        return cls(
            workspace_id=resp.workspace_id,
            workspace_name=resp.workspace_name,
            host=resp.host,
            status=resp.workspace_status,
            created=resp.created,
            message=resp.message,
        )


class PwCtx:
    def __init__(self, req: PwReq, resp: PwResp) -> None:
        self.req = req
        self.resp = resp


class WhReq(BaseModel):
    """OpenAPI request body for `POST /api/v1/ontology/provision-warehouse`."""

    model_config = ConfigDict(
        title="WhReq",
        json_schema_extra={
            "examples": [
                {
                    "workspace_name": "ecommerce-genie-ontology",
                    "warehouse_name": "ecommerce-genie-ontology",
                    "cluster_size": "2X-Small",
                    "auto_stop_mins": 10,
                    "min_num_clusters": 1,
                    "max_num_clusters": 1,
                }
            ]
        },
    )
    workspace_name: str = Field(
        default="ecommerce-genie-ontology",
        description="Existing Databricks workspace name.",
        examples=["ecommerce-genie-ontology"],
    )
    warehouse_name: str = Field(
        default="ecommerce-genie-ontology",
        description="Serverless SQL warehouse name.",
        examples=["ecommerce-genie-ontology"],
    )
    cluster_size: str = Field(default="2X-Small", description="Warehouse cluster size.")
    auto_stop_mins: int = Field(default=10, description="Idle minutes before autostop. 0 disables autostop.")
    min_num_clusters: int = Field(default=1, description="Minimum clusters for the warehouse.")
    max_num_clusters: int = Field(default=1, description="Maximum clusters for the warehouse.")


@dataclass
class WhResp:
    warehouse_id: str = ""
    warehouse_name: str = ""
    host: str = ""
    state: str = ""
    created: bool = False
    message: str = ""


class WhRespResult(BaseModel):
    """OpenAPI result for provisioning a SQL warehouse."""

    model_config = ConfigDict(title="WhRespResult")
    warehouse_id: str = ""
    warehouse_name: str = ""
    host: str = ""
    status: str = ""
    created: bool = False
    message: str = ""

    @classmethod
    def of(cls, resp: WhResp) -> WhRespResult:
        return cls(
            warehouse_id=resp.warehouse_id,
            warehouse_name=resp.warehouse_name,
            host=resp.host,
            status=resp.state,
            created=resp.created,
            message=resp.message,
        )


class WhCtx:
    def __init__(self, req: WhReq, resp: WhResp) -> None:
        self.req = req
        self.resp = resp


class TcReq(BaseModel):
    """OpenAPI request body for `POST /api/v1/ontology/truncate`."""

    model_config = ConfigDict(
        title="TcReq",
        json_schema_extra={
            "examples": [
                {
                    "catalog": "ecommerce_genie_ontology",
                    "confirm": "DELETE",
                }
            ]
        },
    )
    catalog: str = Field(
        default="",
        description="Catalog to drop. Empty uses DATABRICKS_CATALOG.",
        examples=["ecommerce_genie_ontology"],
    )
    confirm: str = Field(default="", description="Must be DELETE.")


@dataclass
class TcResp:
    catalog: str = ""
    dropped: bool = False
    agent_trashed: bool = False
    message: str = ""


class TcRespResult(BaseModel):
    """OpenAPI result for truncating the demo catalog."""

    model_config = ConfigDict(title="TcRespResult")
    catalog: str = ""
    dropped: bool = False
    agent_trashed: bool = False
    message: str = ""

    @classmethod
    def of(cls, resp: TcResp) -> TcRespResult:
        return cls(
            catalog=resp.catalog,
            dropped=resp.dropped,
            agent_trashed=resp.agent_trashed,
            message=resp.message,
        )


class TcCtx:
    def __init__(self, req: TcReq, resp: TcResp) -> None:
        self.req = req
        self.resp = resp


class DyReq(BaseModel):
    """OpenAPI request body for `POST /api/v1/ontology/destroy`."""

    model_config = ConfigDict(
        title="DyReq",
        json_schema_extra={
            "examples": [
                {
                    "workspace_name": "ecommerce-genie-ontology",
                    "warehouse_name": "ecommerce-genie-ontology",
                    "catalog": "ecommerce_genie_ontology",
                    "confirm": "DELETE",
                }
            ]
        },
    )
    workspace_name: str = Field(
        default="",
        description="Workspace to delete. Empty uses DATABRICKS_WORKSPACE_NAME.",
        examples=["ecommerce-genie-ontology"],
    )
    warehouse_name: str = Field(
        default="",
        description="SQL warehouse to delete. Empty uses DATABRICKS_WAREHOUSE_NAME.",
        examples=["ecommerce-genie-ontology"],
    )
    catalog: str = Field(
        default="",
        description="Catalog to drop. Empty uses DATABRICKS_CATALOG.",
        examples=["ecommerce_genie_ontology"],
    )
    confirm: str = Field(default="", description="Must be DELETE.")


@dataclass
class DyResp:
    catalog: str = ""
    catalog_dropped: bool = False
    warehouse_name: str = ""
    warehouse_deleted: bool = False
    workspace_name: str = ""
    workspace_deleted: bool = False
    message: str = ""


class DyRespResult(BaseModel):
    """OpenAPI result for destroying the demo Databricks stack."""

    model_config = ConfigDict(title="DyRespResult")
    catalog: str = ""
    catalog_dropped: bool = False
    warehouse_name: str = ""
    warehouse_deleted: bool = False
    workspace_name: str = ""
    workspace_deleted: bool = False
    message: str = ""

    @classmethod
    def of(cls, resp: DyResp) -> DyRespResult:
        return cls(
            catalog=resp.catalog,
            catalog_dropped=resp.catalog_dropped,
            warehouse_name=resp.warehouse_name,
            warehouse_deleted=resp.warehouse_deleted,
            workspace_name=resp.workspace_name,
            workspace_deleted=resp.workspace_deleted,
            message=resp.message,
        )


class DyCtx:
    def __init__(self, req: DyReq, resp: DyResp) -> None:
        self.req = req
        self.resp = resp
