from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession


class TagsDao:
    def __init__(self, session: WorkspaceSession) -> None:
        self._session = session

    def ensure_tag_policies(self, domain_names: list[str]) -> None:
        try:
            from databricks.sdk.service.tags import TagPolicy
        except ImportError:
            print("SKIP  databricks-sdk TagPolicy not available; domain tagging will still use SET TAG")
            return
        for domain in domain_names:
            try:
                self._session.workspace.tag_policies.create_tag_policy(
                    tag_policy=TagPolicy(
                        tag_key=domain,
                        description=f"Genie Ontology domain: {domain}",
                    )
                )
                print(f"OK    created governed tag / domain '{domain}'")
            except Exception as exc:
                message = str(exc).lower()
                if "already" in message or "exists" in message or "409" in message:
                    print(f"OK    governed tag / domain '{domain}' already exists")
                else:
                    print(f"SKIP  create tag policy '{domain}' -> {exc}")

    def try_create_page(self, page: dict) -> bool:
        body = {
            "name": page["name"],
            "title": page["name"],
            "domain": page["domain"],
            "synonyms": page["synonyms"],
            "description": page["description"],
            "body": page["body"],
            "related_assets": page["related_assets"],
        }
        for endpoint in (
            "/api/2.0/data-discovery/pages",
            "/api/2.0/unity-catalog/pages",
            "/api/2.1/unity-catalog/pages",
        ):
            try:
                self._session.workspace.api_client.do("POST", endpoint, body=body)
                print(f"OK    created Discover Page '{page['name']}' via {endpoint}")
                return True
            except Exception as exc:
                print(f"SKIP  {endpoint} for '{page['name']}' -> {exc}")
        return False
