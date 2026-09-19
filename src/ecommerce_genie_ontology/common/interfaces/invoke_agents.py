from __future__ import annotations

from typing import Protocol


class InvokeAgentsWorkspaceFacade(Protocol):
    question: str
    agent_title: str

    def ask(self, question: str) -> None: ...
