from __future__ import annotations

from typing import Protocol


class CleanupWorkspaceFacade(Protocol):
    confirm: str
    catalog: str
    agent_title: str

    def trash_agent(self) -> None: ...

    def drop_catalog(self) -> None: ...
