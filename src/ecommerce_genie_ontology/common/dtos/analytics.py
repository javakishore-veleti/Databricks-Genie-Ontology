from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AnInitReq(BaseModel):
    model_config = ConfigDict(title="AnInitReq")
    from_date: str = Field(description="YYYY-MM-DD")
    to_date: str = Field(description="YYYY-MM-DD")
    requesting_user: str = "mcp"


class AnIdReq(BaseModel):
    model_config = ConfigDict(title="AnIdReq")
    analytics_id: str


class AnListReq(BaseModel):
    model_config = ConfigDict(title="AnListReq")
    analytics_id: str
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
    outcome: str = ""


class AnCustomerReq(BaseModel):
    model_config = ConfigDict(title="AnCustomerReq")
    analytics_id: str
    customer_id: str


class AnOutcomeReq(BaseModel):
    model_config = ConfigDict(title="AnOutcomeReq")
    analytics_id: str
    customer_id: str
    analytics_outcome: str = Field(description="fraud_found or not_found")
    analytics_log_info: str = "{}"
