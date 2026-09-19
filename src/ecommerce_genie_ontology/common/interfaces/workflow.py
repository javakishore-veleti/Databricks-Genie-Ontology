from __future__ import annotations

from typing import Protocol

from ecommerce_genie_ontology.common.dtos.jobs import JobSpec
from ecommerce_genie_ontology.common.dtos.ontology import DpCtx, LsCtx, PwCtx, DyCtx, TcCtx, WfCtx, WhCtx


class WorkflowTask(Protocol):
    key: str

    def run(self, ctx: WfCtx) -> None: ...


class Workflow(Protocol):
    name: str

    def run(self, ctx: WfCtx) -> None: ...


class WorkflowRunner(Protocol):
    def run(self, ctx: WfCtx) -> None: ...

    def deploy(self, ctx: DpCtx) -> None: ...

    def trigger(self, ctx: WfCtx) -> None: ...

    def list_workflows(self, ctx: LsCtx) -> None: ...

    def provision_workspace(self, ctx: PwCtx) -> None: ...

    def provision_warehouse(self, ctx: WhCtx) -> None: ...

    def truncate(self, ctx: TcCtx) -> None: ...

    def destroy(self, ctx: DyCtx) -> None: ...

    def job_specs(self) -> list[JobSpec]: ...
