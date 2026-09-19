from __future__ import annotations

from typing import Protocol

from ecommerce_genie_ontology.common.dtos.jobs import JobSpec


class JobsFacade(Protocol):
    def deploy(self, jobs: list[JobSpec]) -> dict[str, int]: ...

    def trigger(self, job_name: str, job_parameters: dict[str, str] | None = None) -> object: ...
