from __future__ import annotations

from ecommerce_genie_ontology.common.constants import SAMPLE_QUESTIONS
from ecommerce_genie_ontology.common.dtos.jobs import JobSpec, JobTaskSpec

JOB_NAMES = {
    "provision": "ecommerce-genie-ontology-provision",
    "create_agents": "ecommerce-genie-ontology-create-agents",
    "invoke_agents": "ecommerce-genie-ontology-invoke-agents",
    "cleanup": "ecommerce-genie-ontology-cleanup",
}

JOB_DESCRIPTIONS = {
    "provision": "Create catalog, schema, tables, metric views, certification, domains, and pages.",
    "create_agents": "Create or update the Retail Analytics Genie agent.",
    "invoke_agents": "Ask the sample questions against the Retail Analytics Genie agent.",
    "cleanup": "Drop the demo catalog and trash the Genie agent. Requires confirm=DELETE.",
}

WORKFLOW_ORDER = ("provision", "create_agents", "invoke_agents")


def _task(
    key: str,
    notebook: str,
    task_module: str,
    facade_module: str,
    facade_class: str,
    depends_on: tuple[str, ...] = (),
    extra_params: dict[str, str] | None = None,
    description: str = "",
) -> JobTaskSpec:
    return JobTaskSpec(
        key=key,
        notebook=notebook,
        task_module=task_module,
        facade_module=facade_module,
        facade_class=facade_class,
        depends_on=depends_on,
        extra_params=extra_params or {},
        description=description,
    )


def _provision_tasks() -> tuple[JobTaskSpec, ...]:
    facade_module = "ecommerce_genie_ontology.workflows.provision.workspace_facade.impl"
    facade_class = "ProvisionWorkspaceFacadeImpl"
    prefix = "ecommerce_genie_ontology.workflows.provision.tasks"
    return (
        _task(
            "00_config",
            "00_config",
            f"{prefix}.t00_config",
            facade_module,
            facade_class,
            description="Print shared catalog/schema settings",
        ),
        _task(
            "01_create_catalog_schema_tables",
            "01_create_catalog_schema_tables",
            f"{prefix}.t01_create_catalog_schema_tables",
            facade_module,
            facade_class,
            depends_on=("00_config",),
            description="Create catalog, schema, tables, constraints, and synthetic data",
        ),
        _task(
            "02_create_metric_views",
            "02_create_metric_views",
            f"{prefix}.t02_create_metric_views",
            facade_module,
            facade_class,
            depends_on=("01_create_catalog_schema_tables",),
            description="Create the three Unity Catalog metric views",
        ),
        _task(
            "04_apply_certification_and_domains",
            "04_apply_certification_and_domains",
            f"{prefix}.t04_apply_certification_and_domains",
            facade_module,
            facade_class,
            depends_on=("02_create_metric_views",),
            description="Create domain tags and certify tables / metric views",
        ),
        _task(
            "05_create_pages",
            "05_create_pages",
            f"{prefix}.t05_create_pages",
            facade_module,
            facade_class,
            depends_on=("04_apply_certification_and_domains",),
            description="Persist ontology Pages and create them when an API exists",
        ),
    )


def _invoke_tasks() -> tuple[JobTaskSpec, ...]:
    facade_module = "ecommerce_genie_ontology.workflows.invoke_agents.workspace_facade.impl"
    facade_class = "InvokeAgentsWorkspaceFacadeImpl"
    task_module = "ecommerce_genie_ontology.workflows.invoke_agents.tasks.t07_invoke_genie_agent"
    tasks: list[JobTaskSpec] = []
    previous: str | None = None
    for index, question in enumerate(SAMPLE_QUESTIONS, start=1):
        key = f"07_invoke_q{index}"
        tasks.append(
            _task(
                key,
                "07_invoke_genie_agent",
                task_module,
                facade_module,
                facade_class,
                depends_on=(previous,) if previous else (),
                extra_params={"question": question},
                description=question,
            )
        )
        previous = key
    return tuple(tasks)


def job_specs() -> list[JobSpec]:
    return [
        JobSpec(
            workflow_name="provision",
            job_name=JOB_NAMES["provision"],
            description=JOB_DESCRIPTIONS["provision"],
            tasks=_provision_tasks(),
        ),
        JobSpec(
            workflow_name="create_agents",
            job_name=JOB_NAMES["create_agents"],
            description=JOB_DESCRIPTIONS["create_agents"],
            tasks=(
                _task(
                    "03_create_genie_agent",
                    "03_create_genie_agent",
                    "ecommerce_genie_ontology.workflows.create_agents.tasks.t03_create_genie_agent",
                    "ecommerce_genie_ontology.workflows.create_agents.workspace_facade.impl",
                    "CreateAgentsWorkspaceFacadeImpl",
                    description="Create or update the Retail Analytics Genie agent",
                ),
            ),
        ),
        JobSpec(
            workflow_name="invoke_agents",
            job_name=JOB_NAMES["invoke_agents"],
            description=JOB_DESCRIPTIONS["invoke_agents"],
            tasks=_invoke_tasks(),
        ),
        JobSpec(
            workflow_name="cleanup",
            job_name=JOB_NAMES["cleanup"],
            description=JOB_DESCRIPTIONS["cleanup"],
            tasks=(
                _task(
                    "06_cleanup_delete_all_assets",
                    "06_cleanup_delete_all_assets",
                    "ecommerce_genie_ontology.workflows.cleanup.tasks.t06_cleanup",
                    "ecommerce_genie_ontology.workflows.cleanup.workspace_facade.impl",
                    "CleanupWorkspaceFacadeImpl",
                    description="Drop the demo catalog and trash the Genie agent",
                ),
            ),
        ),
    ]
