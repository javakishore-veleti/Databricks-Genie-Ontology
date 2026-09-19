from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChReq(BaseModel):
    model_config = ConfigDict(title="ChReq")
    prompt: str = Field(min_length=1)
    backend: Literal["langgraph", "google_adk", "genie"] = "langgraph"
    agent_id: str = Field(default="", description="Fraud specialist id, or empty for orchestrator")


@dataclass
class ChResp:
    reply: str = ""
    backend: str = ""
    agent_id: str = ""
    agent_title: str = ""
    steps: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    message: str = ""


class ChRespResult(BaseModel):
    model_config = ConfigDict(title="ChRespResult")
    reply: str = ""
    backend: str = ""
    agent_id: str = ""
    agent_title: str = ""
    steps: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    message: str = ""

    @classmethod
    def of(cls, resp: ChResp) -> ChRespResult:
        return cls(
            reply=resp.reply,
            backend=resp.backend,
            agent_id=resp.agent_id,
            agent_title=resp.agent_title,
            steps=list(resp.steps),
            evidence=list(resp.evidence),
            message=resp.message,
        )


class ChCtx:
    def __init__(self, req: ChReq, resp: ChResp) -> None:
        self.req = req
        self.resp = resp
