from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession

DISCOVER_DOMAIN_COLLECTIONS = (
    "/api/discover/v1/domains",
    "/api/2.0/discover/v1/domains",
)

DISCOVER_PAGE_ENDPOINTS = (
    "/api/discover/v1/pages",
    "/api/discover/v1/glossary/pages",
    "/api/2.0/discover/v1/pages",
    "/api/2.0/data-discovery/pages",
    "/api/2.0/unity-catalog/pages",
    "/api/2.1/unity-catalog/pages",
)


class TagsDao:
    def __init__(self, session: WorkspaceSession) -> None:
        self._session = session
        self._domain_collection: str | None = None

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

    def list_discover_domains(self) -> list[dict]:
        items: list[dict] = []
        token = None
        while True:
            query: dict[str, str | int] = {"page_size": 100}
            if token:
                query["page_token"] = token
            payload = self._domains_do("GET", "", query=query)
            items.extend(payload.get("domains") or [])
            token = payload.get("next_page_token")
            if not token:
                break
        return items

    def ensure_discover_domains(self, domains: list[dict]) -> list[dict]:
        try:
            existing = {
                str(item.get("tag_key") or "").lower(): item for item in self.list_discover_domains()
            }
        except Exception as exc:
            print(f"SKIP  list Discover domains -> {exc}")
            existing = {}
        published: list[dict] = []
        for spec in domains:
            key = str(spec["tag_key"]).lower()
            current = existing.get(key)
            if current is None:
                current = self._create_discover_domain(spec)
            else:
                print(f"OK    Discover domain '{spec['tag_key']}' already exists")
                current = self._update_discover_domain(current, spec)
            if current is None:
                continue
            current = self._publish_discover_domain(current)
            published.append(current)
        return published

    def try_create_page(self, page: dict) -> bool:
        body = {
            "name": page["name"],
            "title": page["name"],
            "display_name": page["name"],
            "domain": page["domain"],
            "synonyms": page["synonyms"],
            "description": page["description"],
            "body": page["body"],
            "related_assets": page["related_assets"],
            "draft": False,
        }
        if page.get("domain_id"):
            body["domain_id"] = page["domain_id"]
        if page.get("domain_name"):
            body["parent"] = page["domain_name"]
            body["domain_name"] = page["domain_name"]
        for endpoint in DISCOVER_PAGE_ENDPOINTS:
            try:
                created = self._session.workspace.api_client.do("POST", endpoint, body=body)
                print(f"OK    created Discover Page '{page['name']}' via {endpoint}")
                self._publish_page(created if isinstance(created, dict) else {}, endpoint)
                return True
            except Exception as exc:
                print(f"SKIP  {endpoint} for '{page['name']}' -> {exc}")
        return False

    def _create_discover_domain(self, spec: dict) -> dict | None:
        body = {
            "tag_key": spec["tag_key"],
            "draft": False,
            "subtitle": spec["subtitle"],
            "description": spec["description"],
            "icon": spec["icon"],
        }
        try:
            created = self._domains_do("POST", "", body=body)
        except Exception as exc:
            message = str(exc).lower()
            if "already" in message or "exists" in message or "409" in message:
                print(f"OK    Discover domain '{spec['tag_key']}' already exists")
                return self._domain_by_tag(spec["tag_key"])
            print(f"SKIP  create Discover domain '{spec['tag_key']}' -> {exc}")
            return None
        print(f"OK    created Discover domain '{spec['tag_key']}'")
        return created if isinstance(created, dict) else {"tag_key": spec["tag_key"]}

    def _update_discover_domain(self, current: dict, spec: dict) -> dict:
        domain_id = self._domain_id(current)
        if not domain_id:
            return current
        body = {
            "subtitle": spec["subtitle"],
            "description": spec["description"],
            "icon": spec["icon"],
        }
        try:
            updated = self._domains_do(
                "PATCH",
                f"/{domain_id}",
                query={"update_mask": "subtitle,description,icon"},
                body=body,
            )
            print(f"OK    updated Discover domain '{spec['tag_key']}'")
            return updated if isinstance(updated, dict) else current
        except Exception as exc:
            print(f"SKIP  update Discover domain '{spec['tag_key']}' -> {exc}")
            return current

    def _publish_discover_domain(self, current: dict) -> dict:
        if current.get("effective_draft") is False:
            print(f"OK    published Discover domain '{current.get('tag_key')}'")
            return current
        domain_id = self._domain_id(current)
        if not domain_id:
            return current
        try:
            published = self._domains_do(
                "PATCH",
                f"/{domain_id}",
                query={"update_mask": "draft"},
                body={"draft": False},
            )
            tag = current.get("tag_key")
            print(f"OK    published Discover domain '{tag}'")
            return published if isinstance(published, dict) else {**current, "effective_draft": False}
        except Exception as exc:
            print(f"SKIP  publish Discover domain '{current.get('tag_key')}' -> {exc}")
            return current

    def _publish_page(self, created: dict, create_endpoint: str) -> None:
        page_id = created.get("page_id") or created.get("id") or created.get("name")
        if not page_id or created.get("effective_draft") is False:
            return
        path = created.get("name")
        if isinstance(path, str) and path.startswith("pages/"):
            endpoint = create_endpoint.rsplit("/", 1)[0] + "/" + path.split("/", 1)[1]
        else:
            endpoint = f"{create_endpoint.rstrip('/')}/{page_id}"
        try:
            self._session.workspace.api_client.do(
                "PATCH",
                endpoint,
                query={"update_mask": "draft"},
                body={"draft": False},
            )
            print(f"OK    published Discover Page via {endpoint}")
        except Exception as exc:
            print(f"SKIP  publish page {page_id} -> {exc}")

    def _domain_by_tag(self, tag_key: str) -> dict | None:
        try:
            for item in self.list_discover_domains():
                if str(item.get("tag_key") or "").lower() == tag_key.lower():
                    return item
        except Exception as exc:
            print(f"SKIP  lookup Discover domain '{tag_key}' -> {exc}")
        return None

    @staticmethod
    def _domain_id(domain: dict) -> str:
        domain_id = str(domain.get("domain_id") or "")
        if domain_id:
            return domain_id
        name = str(domain.get("name") or "")
        if name.startswith("domains/"):
            return name.split("/", 1)[1]
        return name

    def _domains_do(self, method: str, suffix: str, **kwargs):
        prefixes = (
            [self._domain_collection]
            if self._domain_collection
            else list(DISCOVER_DOMAIN_COLLECTIONS)
        )
        last: Exception | None = None
        for prefix in prefixes:
            if not prefix:
                continue
            path = f"{prefix}{suffix}"
            try:
                result = self._session.workspace.api_client.do(method, path, **kwargs)
                self._domain_collection = prefix
                return result if isinstance(result, dict) else {}
            except Exception as exc:
                last = exc
                if self._domain_collection:
                    raise
                print(f"SKIP  {method} {path} -> {exc}")
        raise RuntimeError(f"Discover domains API unavailable: {last}")
