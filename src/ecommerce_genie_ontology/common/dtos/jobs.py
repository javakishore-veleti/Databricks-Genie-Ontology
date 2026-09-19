from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class JobTaskSpec:
    key: str
    notebook: str
    task_module: str
    facade_module: str
    facade_class: str
    depends_on: tuple[str, ...] = ()
    extra_params: dict[str, str] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class JobSpec:
    workflow_name: str
    job_name: str
    description: str
    tasks: tuple[JobTaskSpec, ...]
