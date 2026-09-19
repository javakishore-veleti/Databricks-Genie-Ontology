from __future__ import annotations

from dataclasses import dataclass, field

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OhReq(BaseModel):
    model_config = ConfigDict(title="OhReq")
    customer_count: int = Field(default=200, ge=1, le=10_000)
    orders_per_year: int = Field(default=25000, ge=1, le=100_000)
    year_count: int = Field(default=3, ge=1, le=3)
    as_job: bool = True


@dataclass
class OhResp:
    customers: int = 0
    addresses: int = 0
    orders: int = 0
    lines: int = 0
    status: str = ""
    message: str = ""


class OhRespResult(BaseModel):
    model_config = ConfigDict(title="OhRespResult")
    customers: int = 0
    addresses: int = 0
    orders: int = 0
    lines: int = 0
    status: str = ""
    message: str = ""

    @classmethod
    def of(cls, resp: OhResp) -> OhRespResult:
        return cls(**resp.__dict__)


class OhCtx:
    def __init__(self, req: OhReq, resp: OhResp) -> None:
        self.req = req
        self.resp = resp


class OdReq(BaseModel):
    model_config = ConfigDict(title="OdReq")
    count: int = Field(default=1000, ge=100, le=10_000)
    year_window: Literal["latest", "last_2", "last_3", "all"] = Field(default="latest")
    as_job: bool = True


@dataclass
class OdResp:
    orders: int = 0
    lines: int = 0
    year_window: str = ""
    status: str = ""
    message: str = ""


class OdRespResult(BaseModel):
    model_config = ConfigDict(title="OdRespResult")
    orders: int = 0
    lines: int = 0
    year_window: str = ""
    status: str = ""
    message: str = ""

    @classmethod
    def of(cls, resp: OdResp) -> OdRespResult:
        return cls(**resp.__dict__)


class OdCtx:
    def __init__(self, req: OdReq, resp: OdResp) -> None:
        self.req = req
        self.resp = resp


class EhReq(BaseModel):
    model_config = ConfigDict(title="EhReq")
    as_job: bool = True


@dataclass
class EhResp:
    status: str = ""
    message: str = ""


class EhRespResult(BaseModel):
    model_config = ConfigDict(title="EhRespResult")
    status: str = ""
    message: str = ""

    @classmethod
    def of(cls, resp: EhResp) -> EhRespResult:
        return cls(status=resp.status, message=resp.message)


class EhCtx:
    def __init__(self, req: EhReq, resp: EhResp) -> None:
        self.req = req
        self.resp = resp


class EcReq(BaseModel):
    model_config = ConfigDict(title="EcReq")
    as_job: bool = True


@dataclass
class EcResp:
    rows: int = 0
    status: str = ""
    message: str = ""


class EcRespResult(BaseModel):
    model_config = ConfigDict(title="EcRespResult")
    rows: int = 0
    status: str = ""
    message: str = ""

    @classmethod
    def of(cls, resp: EcResp) -> EcRespResult:
        return cls(rows=resp.rows, status=resp.status, message=resp.message)


class EcCtx:
    def __init__(self, req: EcReq, resp: EcResp) -> None:
        self.req = req
        self.resp = resp


class FcReq(BaseModel):
    model_config = ConfigDict(title="FcReq")
    case_id: str = Field(default="01")


@dataclass
class FcResp:
    case_id: str = ""
    name: str = ""
    rows: list[dict] = field(default_factory=list)
    message: str = ""


class FcRespResult(BaseModel):
    model_config = ConfigDict(title="FcRespResult")
    case_id: str = ""
    name: str = ""
    rows: list[dict] = Field(default_factory=list)
    message: str = ""

    @classmethod
    def of(cls, resp: FcResp) -> FcRespResult:
        return cls(case_id=resp.case_id, name=resp.name, rows=list(resp.rows), message=resp.message)


class FcCtx:
    def __init__(self, req: FcReq, resp: FcResp) -> None:
        self.req = req
        self.resp = resp


class NxReq(BaseModel):
    model_config = ConfigDict(title="NxReq")
    row_count: int = Field(default=100_000, ge=1, le=100_000)
    as_job: bool = True


@dataclass
class NxResp:
    rows: int = 0
    orders: int = 0
    postings: int = 0
    start_date: str = ""
    end_date: str = ""
    year: int = 0
    status: str = ""
    message: str = ""


class NxRespResult(BaseModel):
    model_config = ConfigDict(title="NxRespResult")
    rows: int = 0
    orders: int = 0
    postings: int = 0
    start_date: str = ""
    end_date: str = ""
    year: int = 0
    status: str = ""
    message: str = ""

    @classmethod
    def of(cls, resp: NxResp) -> NxRespResult:
        return cls(**resp.__dict__)


class NxCtx:
    def __init__(self, req: NxReq, resp: NxResp) -> None:
        self.req = req
        self.resp = resp


class EmReq(BaseModel):
    model_config = ConfigDict(title="EmReq")
    months: int = Field(default=3, ge=1, le=12)
    as_job: bool = True


@dataclass
class EmResp:
    rows: int = 0
    months: int = 0
    start_date: str = ""
    end_date: str = ""
    year: int = 0
    status: str = ""
    message: str = ""


class EmRespResult(BaseModel):
    model_config = ConfigDict(title="EmRespResult")
    rows: int = 0
    months: int = 0
    start_date: str = ""
    end_date: str = ""
    year: int = 0
    status: str = ""
    message: str = ""

    @classmethod
    def of(cls, resp: EmResp) -> EmRespResult:
        return cls(**resp.__dict__)


class EmCtx:
    def __init__(self, req: EmReq, resp: EmResp) -> None:
        self.req = req
        self.resp = resp
