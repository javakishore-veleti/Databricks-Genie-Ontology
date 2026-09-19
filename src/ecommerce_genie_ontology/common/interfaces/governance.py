from __future__ import annotations

from typing import Protocol


class GovernanceFacade(Protocol):
    def ensure_domain_tag_policies(self, domain_names: list[str]) -> None: ...

    def ensure_discover_domains(self, domains: list[dict]) -> list[dict]: ...

    def try_create_page(self, page: dict) -> bool: ...
