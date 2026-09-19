from __future__ import annotations

from pydantic import BaseModel, Field


class HlReq(BaseModel):
    pass


class HlResp(BaseModel):
    status: str = "ok"


class HlCtx:
    def __init__(self, req: HlReq, resp: HlResp) -> None:
        self.req = req
        self.resp = resp


class LsReq(BaseModel):
    pass


class WfItem(BaseModel):
    name: str
    job_name: str
    description: str = ""
    tasks: list[str] = Field(default_factory=list)


class LsResp(BaseModel):
    workflows: list[WfItem] = Field(default_factory=list)


class LsCtx:
    def __init__(self, req: LsReq, resp: LsResp) -> None:
        self.req = req
        self.resp = resp


class WfReq(BaseModel):
    workflow: str = "provision"
    question: str = ""
    confirm: str = ""
    as_job: bool = False


class WfResp(BaseModel):
    workflow: str = ""
    status: str = ""
    message: str = ""


class WfCtx:
    def __init__(self, req: WfReq, resp: WfResp) -> None:
        self.req = req
        self.resp = resp


class DpReq(BaseModel):
    pass


class DpResp(BaseModel):
    status: str = ""
    job_ids: dict[str, int] = Field(default_factory=dict)
    message: str = ""


class DpCtx:
    def __init__(self, req: DpReq, resp: DpResp) -> None:
        self.req = req
        self.resp = resp


class PwReq(BaseModel):
    workspace_name: str = "ecommerce-genie-ontology"
    aws_region: str = "us-east-1"
    pricing_tier: str = "PREMIUM"
    compute_mode: str = "SERVERLESS"


class PwResp(BaseModel):
    workspace_id: int | None = None
    workspace_name: str = ""
    host: str = ""
    aws_region: str = ""
    workspace_status: str = ""
    created: bool = False
    message: str = ""


class PwCtx:
    def __init__(self, req: PwReq, resp: PwResp) -> None:
        self.req = req
        self.resp = resp
