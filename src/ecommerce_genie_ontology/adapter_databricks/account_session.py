from __future__ import annotations

from databricks.sdk import AccountClient

from ecommerce_genie_ontology.common.dtos.account import AccountSettings


class AccountSession:
    def __init__(self, settings: AccountSettings, account: AccountClient) -> None:
        self.settings = settings
        self.account = account

    @classmethod
    def from_settings(cls, settings: AccountSettings) -> AccountSession:
        kwargs: dict[str, str] = {"host": settings.account_host, "account_id": settings.account_id}
        if settings.token:
            kwargs["token"] = settings.token
        if settings.client_id and settings.client_secret:
            kwargs["client_id"] = settings.client_id
            kwargs["client_secret"] = settings.client_secret
        return cls(settings=settings, account=AccountClient(**kwargs))
