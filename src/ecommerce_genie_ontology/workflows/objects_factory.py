"""Singleton lookup for workflow facades, tasks, and workflow classes."""

from __future__ import annotations

from typing import Any

from ecommerce_genie_ontology.adapter_databricks.objects_factory import AdapterDatabricksObjectsFactory
from ecommerce_genie_ontology.common.dtos.jobs import JobSpec
from ecommerce_genie_ontology.common.dtos.settings import Settings
from ecommerce_genie_ontology.common.interfaces.cleanup import CleanupWorkspaceFacade
from ecommerce_genie_ontology.common.interfaces.create_agents import CreateAgentsWorkspaceFacade
from ecommerce_genie_ontology.common.interfaces.invoke_agents import InvokeAgentsWorkspaceFacade
from ecommerce_genie_ontology.common.interfaces.jobs import JobsFacade
from ecommerce_genie_ontology.common.interfaces.provision import ProvisionWorkspaceFacade
from ecommerce_genie_ontology.common.interfaces.workflow import Workflow, WorkflowRunner, WorkflowTask
from ecommerce_genie_ontology.common.utils.objects_factory import ObjectsFactory
from ecommerce_genie_ontology.workflows.cleanup.tasks.t06_cleanup import CleanupAssetsTask
from ecommerce_genie_ontology.workflows.cleanup.workflow import CleanupWorkflow
from ecommerce_genie_ontology.workflows.cleanup.workspace_facade.impl import CleanupWorkspaceFacadeImpl
from ecommerce_genie_ontology.workflows.create_agents.tasks.t03_create_genie_agent import (
    CreateGenieAgentTask,
)
from ecommerce_genie_ontology.workflows.create_agents.workflow import CreateAgentsWorkflow
from ecommerce_genie_ontology.workflows.create_agents.workspace_facade.impl import (
    CreateAgentsWorkspaceFacadeImpl,
)
from ecommerce_genie_ontology.workflows.invoke_agents.tasks.t07_invoke_genie_agent import (
    InvokeGenieAgentTask,
)
from ecommerce_genie_ontology.workflows.invoke_agents.workflow import InvokeAgentsWorkflow
from ecommerce_genie_ontology.workflows.invoke_agents.workspace_facade.impl import (
    InvokeAgentsWorkspaceFacadeImpl,
)
from ecommerce_genie_ontology.workflows.job_specs import job_specs as build_job_specs
from ecommerce_genie_ontology.workflows.orchestrator import WorkflowOrchestrator
from ecommerce_genie_ontology.workflows.provision.tasks.t00_config import PrintConfigTask
from ecommerce_genie_ontology.workflows.provision.tasks.t01_create_catalog_schema_tables import (
    CreateCatalogSchemaTablesTask,
)
from ecommerce_genie_ontology.workflows.provision.tasks.t02_create_metric_views import (
    CreateMetricViewsTask,
)
from ecommerce_genie_ontology.workflows.provision.tasks.t04_apply_certification_and_domains import (
    ApplyCertificationAndDomainsTask,
)
from ecommerce_genie_ontology.workflows.provision.tasks.t05_create_pages import CreatePagesTask
from ecommerce_genie_ontology.workflows.provision.workflow import ProvisionWorkflow
from ecommerce_genie_ontology.workflows.provision.workspace_facade.impl import (
    ProvisionWorkspaceFacadeImpl,
)


class WorkflowsObjectsFactory(ObjectsFactory):
    @classmethod
    def instance(cls) -> WorkflowsObjectsFactory:
        return super().instance()  # type: ignore[return-value]

    @classmethod
    def from_databricks(cls, dbutils: Any, spark: Any) -> WorkflowsObjectsFactory:
        AdapterDatabricksObjectsFactory.from_databricks(dbutils, spark)
        factory = cls()
        ObjectsFactory._factories[cls] = factory
        return factory

    def adapter_factory(self) -> AdapterDatabricksObjectsFactory:
        return AdapterDatabricksObjectsFactory.instance()

    def settings(self) -> Settings:
        return self.adapter_factory().settings()

    def jobs_facade(self) -> JobsFacade:
        return self.adapter_factory().jobs_facade()

    def provision_workspace_facade(self) -> ProvisionWorkspaceFacade:
        return self.singleton(
            "provision_workspace_facade",
            lambda: ProvisionWorkspaceFacadeImpl.from_factory(self.adapter_factory()),
        )

    def create_agents_workspace_facade(self) -> CreateAgentsWorkspaceFacade:
        return self.singleton(
            "create_agents_workspace_facade",
            lambda: CreateAgentsWorkspaceFacadeImpl.from_factory(self.adapter_factory()),
        )

    def invoke_agents_workspace_facade(self) -> InvokeAgentsWorkspaceFacade:
        return self.singleton(
            "invoke_agents_workspace_facade",
            lambda: InvokeAgentsWorkspaceFacadeImpl.from_factory(self.adapter_factory()),
        )

    def cleanup_workspace_facade(self) -> CleanupWorkspaceFacade:
        return self.singleton(
            "cleanup_workspace_facade",
            lambda: CleanupWorkspaceFacadeImpl.from_factory(self.adapter_factory()),
        )

    def provision_tasks(self) -> list[WorkflowTask]:
        facade = self.provision_workspace_facade()
        return self.singleton(
            "provision_tasks",
            lambda: [
                PrintConfigTask(facade),
                CreateCatalogSchemaTablesTask(facade),
                CreateMetricViewsTask(facade),
                ApplyCertificationAndDomainsTask(facade),
                CreatePagesTask(facade),
            ],
        )

    def create_agents_tasks(self) -> list[WorkflowTask]:
        facade = self.create_agents_workspace_facade()
        return self.singleton("create_agents_tasks", lambda: [CreateGenieAgentTask(facade)])

    def invoke_agents_tasks(self) -> list[WorkflowTask]:
        facade = self.invoke_agents_workspace_facade()
        return self.singleton("invoke_agents_tasks", lambda: [InvokeGenieAgentTask(facade)])

    def cleanup_tasks(self) -> list[WorkflowTask]:
        facade = self.cleanup_workspace_facade()
        return self.singleton("cleanup_tasks", lambda: [CleanupAssetsTask(facade)])

    def provision_workflow(self) -> Workflow:
        return self.singleton(
            "provision_workflow",
            lambda: ProvisionWorkflow(self.provision_workspace_facade(), self.provision_tasks()),
        )

    def create_agents_workflow(self) -> Workflow:
        return self.singleton(
            "create_agents_workflow",
            lambda: CreateAgentsWorkflow(
                self.create_agents_workspace_facade(), self.create_agents_tasks()
            ),
        )

    def invoke_agents_workflow(self) -> Workflow:
        return self.singleton(
            "invoke_agents_workflow",
            lambda: InvokeAgentsWorkflow(
                self.invoke_agents_workspace_facade(), self.invoke_agents_tasks()
            ),
        )

    def cleanup_workflow(self) -> Workflow:
        return self.singleton(
            "cleanup_workflow",
            lambda: CleanupWorkflow(self.cleanup_workspace_facade(), self.cleanup_tasks()),
        )

    def workflow(self, name: str) -> Workflow:
        workflows = {
            "provision": self.provision_workflow,
            "create_agents": self.create_agents_workflow,
            "invoke_agents": self.invoke_agents_workflow,
            "cleanup": self.cleanup_workflow,
        }
        provider = workflows.get(name)
        if provider is None:
            raise SystemExit(f"Unknown workflow {name!r}. Choose from: {', '.join(workflows)}")
        return provider()

    def orchestrator(self) -> WorkflowRunner:
        return self.singleton("orchestrator", lambda: WorkflowOrchestrator(self))

    def job_specs(self) -> list[JobSpec]:
        return self.singleton("job_specs", build_job_specs)
