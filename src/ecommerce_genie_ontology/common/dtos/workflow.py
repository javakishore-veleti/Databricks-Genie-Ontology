from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class WorkflowRunRequest:
    workflow: str
    question: str = ""
    confirm: str = ""
    as_job: bool = False


@dataclass
class WorkflowRunResult:
    workflow: str
    status: str
    message: str = ""
    details: dict = field(default_factory=dict)
