from __future__ import annotations

from ecommerce_genie_ontology.common.constants import SAMPLE_QUESTIONS
from ecommerce_genie_ontology.common.interfaces.invoke_agents import InvokeAgentsWorkspaceFacade


class InvokeGenieAgentTask:
    key = "07_invoke_genie_agent"

    def __init__(self, facade: InvokeAgentsWorkspaceFacade) -> None:
        self._facade = facade

    def run(self) -> None:
        question = self._facade.question.strip() if self._facade.question else ""
        questions = [question] if question else list(SAMPLE_QUESTIONS)
        for item in questions:
            print("=" * 80)
            self._facade.ask(item)


def run(facade: InvokeAgentsWorkspaceFacade) -> None:
    InvokeGenieAgentTask(facade).run()
