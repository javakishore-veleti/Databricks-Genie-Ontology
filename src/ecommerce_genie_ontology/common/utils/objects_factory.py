"""Base factory: named lookup plus per-factory singletons."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class ObjectsFactory:
    _factories: dict[type, ObjectsFactory] = {}

    def __init__(self) -> None:
        self._singletons: dict[str, object] = {}

    @classmethod
    def instance(cls) -> ObjectsFactory:
        existing = ObjectsFactory._factories.get(cls)
        if existing is None:
            existing = cls()
            ObjectsFactory._factories[cls] = existing
        return existing

    def lookup(self, name: str) -> object:
        provider = getattr(self, name, None)
        if provider is None:
            raise KeyError(f"Unknown component {name!r} in {type(self).__name__}")
        return provider() if callable(provider) else provider

    def singleton(self, name: str, factory: Callable[[], T]) -> T:
        if name not in self._singletons:
            self._singletons[name] = factory()
        return self._singletons[name]  # type: ignore[return-value]
