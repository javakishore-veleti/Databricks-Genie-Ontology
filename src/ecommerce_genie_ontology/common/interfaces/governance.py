from __future__ import annotations

from typing import Protocol


class GovernanceFacade(Protocol):
    def ensure_domain_tag_policies(self, domain_names: list[str]) -> None: ...

    def try_create_page(self, page: dict) -> bool: ...
