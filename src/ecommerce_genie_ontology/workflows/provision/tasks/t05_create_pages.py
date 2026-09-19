from __future__ import annotations

from ecommerce_genie_ontology.common.constants import PAGES
from ecommerce_genie_ontology.common.interfaces.provision import ProvisionWorkspaceFacade
from ecommerce_genie_ontology.common.utils.sql_text import sql_string


class CreatePagesTask:
    key = "05_create_pages"

    def __init__(self, facade: ProvisionWorkspaceFacade) -> None:
        self._facade = facade

    def run(self) -> None:
        fq = self._facade.fq_schema
        self._facade.sql(
            f"""
CREATE OR REPLACE TABLE {fq}._ontology_pages (
  page_name STRING,
  domain STRING,
  synonyms STRING,
  description STRING,
  body STRING,
  related_assets STRING
)
COMMENT 'Authoritative Page definitions for the Genie Ontology demo (Discover Pages have no public create API)'
"""
        )
        values = []
        for page in PAGES:
            values.append(
                "("
                + ", ".join(
                    [
                        sql_string(page["name"]),
                        sql_string(page["domain"]),
                        sql_string(", ".join(page["synonyms"])),
                        sql_string(page["description"]),
                        sql_string(page["body"]),
                        sql_string(", ".join(page["related_assets"])),
                    ]
                )
                + ")"
            )
        self._facade.sql(
            f"""
INSERT INTO {fq}._ontology_pages
  (page_name, domain, synonyms, description, body, related_assets)
VALUES {", ".join(values)}
"""
        )
        print(f"Wrote {len(PAGES)} page definitions to {fq}._ontology_pages")
        for page in PAGES:
            if not self._facade.try_create_page(page):
                print(
                    f"NOTE  '{page['name']}' is stored in Unity Catalog. "
                    "Create the Discover Page in the UI if your workspace has no Pages API."
                )
        print("Done. Page content is available for Genie and for manual Discover publishing.")


def run(facade: ProvisionWorkspaceFacade) -> None:
    CreatePagesTask(facade).run()
