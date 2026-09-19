from __future__ import annotations

from ecommerce_genie_ontology.common.interfaces.workflow import Workflow, WorkflowTask


class SingleTaskWorkflow:
    def __init__(self, name: str, tasks: list[WorkflowTask]) -> None:
        self.name = name
        self._tasks = tasks

    def run(self) -> None:
        print(f"=== workflow {self.name} ===")
        for task in self._tasks:
            print(f"--- task {task.key} ---")
            task.run()
            print(f"--- task {task.key}: done ---")


def _assert_protocol() -> None:
    _: type[Workflow] = SingleTaskWorkflow
