from __future__ import annotations

from ecommerce_genie_ontology.common.constants import (
    ASSET_DOMAINS,
    DISCOVER_DOMAINS,
    DOMAIN_NAMES,
    METRIC_VIEWS,
)
from ecommerce_genie_ontology.common.interfaces.provision import ProvisionWorkspaceFacade


class ApplyCertificationAndDomainsTask:
    key = "04_apply_certification_and_domains"

    def __init__(self, facade: ProvisionWorkspaceFacade) -> None:
        self._facade = facade

    def run(self) -> None:
        self._facade.ensure_domain_tag_policies(DOMAIN_NAMES)
        published = self._facade.ensure_discover_domains(DISCOVER_DOMAINS)
        drafts = [item.get("tag_key") for item in published if item.get("effective_draft")]
        print(f"OK    Discover domains upserted: {len(published)}")
        if drafts:
            print(f"NOTE  still draft: {', '.join(str(name) for name in drafts if name)}")
        fq = self._facade.fq_schema
        for asset_name, domains in ASSET_DOMAINS.items():
            kind = "VIEW" if asset_name in METRIC_VIEWS else "TABLE"
            fq_asset = f"{fq}.{asset_name}"
            self._facade.sql_ok(
                f"ALTER {kind} {fq_asset} SET TAGS ('system.certification_status' = 'certified')"
            )
            for domain in DOMAIN_NAMES:
                verb = "SET" if domain in domains else "UNSET"
                self._facade.sql_ok(f"{verb} TAG ON {kind} {fq_asset} `{domain}`")
        print("Done. Tables and metric views are certified and domain-tagged.")


def run(facade: ProvisionWorkspaceFacade) -> None:
    ApplyCertificationAndDomainsTask(facade).run()
