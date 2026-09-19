from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.daos.tags_dao import TagsDao
from ecommerce_genie_ontology.common.interfaces.governance import GovernanceFacade


class GovernanceFacadeImpl:
    def __init__(self, tags_dao: TagsDao) -> None:
        self._tags = tags_dao

    def ensure_domain_tag_policies(self, domain_names: list[str]) -> None:
        self._tags.ensure_tag_policies(domain_names)

    def ensure_discover_domains(self, domains: list[dict]) -> list[dict]:
        return self._tags.ensure_discover_domains(domains)

    def try_create_page(self, page: dict) -> bool:
        return self._tags.try_create_page(page)


def _assert_protocol() -> None:
    _: type[GovernanceFacade] = GovernanceFacadeImpl
