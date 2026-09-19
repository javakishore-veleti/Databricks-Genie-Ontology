from __future__ import annotations

from pydantic import BaseModel, Field


class WorkflowSummary(BaseModel):
    name: str
    job_name: str
    description: str
    tasks: list[str] = Field(default_factory=list)


class WorkflowRunBody(BaseModel):
    question: str = ""
    confirm: str = ""
    as_job: bool = False


class WorkflowRunResponse(BaseModel):
    workflow: str
    status: str
    message: str = ""
    job_ids: dict[str, int] = Field(default_factory=dict)


class DeployResponse(BaseModel):
    status: str
    job_ids: dict[str, int]
