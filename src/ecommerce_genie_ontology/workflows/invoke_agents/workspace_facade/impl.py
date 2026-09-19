from __future__ import annotations

from typing import Any

from ecommerce_genie_ontology.adapter_databricks.objects_factory import AdapterDatabricksObjectsFactory
from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.interfaces.genie import GenieFacade
from ecommerce_genie_ontology.common.interfaces.invoke_agents import InvokeAgentsWorkspaceFacade


class InvokeAgentsWorkspaceFacadeImpl:
    def __init__(self, session: WorkspaceSession, genie_facade: GenieFacade) -> None:
        self._session = session
        self._genie = genie_facade

    @classmethod
    def from_factory(cls, factory: AdapterDatabricksObjectsFactory) -> InvokeAgentsWorkspaceFacadeImpl:
        return cls(factory.session(), factory.genie_facade())

    @classmethod
    def from_databricks(cls, dbutils: Any, spark: Any) -> InvokeAgentsWorkspaceFacadeImpl:
        return cls.from_factory(AdapterDatabricksObjectsFactory.from_databricks(dbutils, spark))

    @property
    def question(self) -> str:
        return self._session.context.question

    @question.setter
    def question(self, value: str) -> None:
        self._session.context.question = value

    @property
    def agent_title(self) -> str:
        return self._session.agent_title

    def ask(self, question: str) -> None:
        self._genie.ask(question)


def _assert_protocol() -> None:
    _: type[InvokeAgentsWorkspaceFacade] = InvokeAgentsWorkspaceFacadeImpl
