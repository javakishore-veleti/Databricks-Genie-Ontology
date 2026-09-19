from __future__ import annotations

from ecommerce_genie_ontology.common.interfaces.invoke_agents import InvokeAgentsWorkspaceFacade
from ecommerce_genie_ontology.common.interfaces.workflow import Workflow, WorkflowTask
from ecommerce_genie_ontology.workflows.job_specs import JOB_NAMES


class InvokeAgentsWorkflow:
    name = "invoke_agents"

    def __init__(self, facade: InvokeAgentsWorkspaceFacade, tasks: list[WorkflowTask]) -> None:
        self._facade = facade
        self._tasks = tasks

    def run(self) -> None:
        print(f"=== workflow {self.name} ({JOB_NAMES[self.name]}) ===")
        for task in self._tasks:
            print(f"--- task {task.key} ---")
            task.run()
            print(f"--- task {task.key}: done ---")


def _assert_protocol() -> None:
    _: type[Workflow] = InvokeAgentsWorkflow
