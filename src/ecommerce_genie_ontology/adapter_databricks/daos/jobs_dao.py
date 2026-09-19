from __future__ import annotations

from databricks.sdk.service.jobs import (
    JobParameterDefinition,
    JobSettings,
    NotebookTask,
    QueueSettings,
    Source,
    Task,
    TaskDependency,
)
from databricks.sdk.service.workspace import ImportFormat, Language

from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.common.dtos.jobs import JobSpec
from ecommerce_genie_ontology.common.dtos.settings import Settings
from ecommerce_genie_ontology.common.paths import PROJECT_ROOT


class JobsDao:
    def __init__(self, session: WorkspaceSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    def upload_package(self) -> None:
        src_root = PROJECT_ROOT / "src"
        dest_root = self._settings.package_workspace_path.rstrip("/")
        self._mkdir(dest_root)
        for path in sorted(src_root.rglob("*")):
            if not path.is_file() or path.suffix != ".py" or "__pycache__" in path.parts:
                continue
            dest = f"{dest_root}/{path.relative_to(src_root).as_posix()}"
            self._mkdir(dest.rsplit("/", 1)[0])
            self._session.workspace.workspace.upload(
                dest, path.read_bytes(), overwrite=True, format=ImportFormat.AUTO
            )
            print(f"uploaded {dest}")

    def upload_notebooks(self, jobs: list[JobSpec]) -> None:
        notebooks_root = self._settings.notebooks_workspace_path.rstrip("/")
        self._mkdir(notebooks_root)
        seen: set[str] = set()
        for job in jobs:
            for spec in job.tasks:
                if spec.notebook in seen:
                    continue
                seen.add(spec.notebook)
                dest = f"{notebooks_root}/{spec.notebook}"
                self._session.workspace.workspace.upload(
                    dest,
                    self._notebook_source(spec.task_module, spec.facade_module, spec.facade_class).encode("utf-8"),
                    overwrite=True,
                    format=ImportFormat.SOURCE,
                    language=Language.PYTHON,
                )
                print(f"uploaded notebook {dest}")

    def upsert_job(self, spec: JobSpec) -> int:
        notebooks_root = self._settings.notebooks_workspace_path.rstrip("/")
        tasks = [
            Task(
                task_key=task.key,
                description=task.description,
                notebook_task=NotebookTask(
                    notebook_path=f"{notebooks_root}/{task.notebook}",
                    source=Source.WORKSPACE,
                    base_parameters=self._base_parameters(task.extra_params),
                ),
                depends_on=[TaskDependency(task_key=dep) for dep in task.depends_on],
            )
            for task in spec.tasks
        ]
        settings = JobSettings(
            name=spec.job_name,
            description=spec.description,
            tasks=tasks,
            parameters=self._job_parameters(),
            max_concurrent_runs=1,
            queue=QueueSettings(enabled=True),
            tags={"project": "ecommerce-genie-ontology", "workflow": spec.workflow_name},
        )
        job_id = self.find_job_id(spec.job_name)
        if job_id is None:
            created = self._session.workspace.jobs.create(
                name=settings.name,
                description=settings.description,
                tasks=settings.tasks,
                parameters=settings.parameters,
                max_concurrent_runs=settings.max_concurrent_runs,
                queue=settings.queue,
                tags=settings.tags,
            )
            print(f"created job {spec.job_name} (job_id={created.job_id})")
            return created.job_id
        self._session.workspace.jobs.reset(job_id=job_id, new_settings=settings)
        print(f"updated job {spec.job_name} (job_id={job_id})")
        return job_id

    def find_job_id(self, name: str) -> int | None:
        for job in self._session.workspace.jobs.list(name=name):
            if job.settings and job.settings.name == name:
                return job.job_id
        return None

    def trigger(self, job_name: str, job_parameters: dict[str, str] | None = None):
        job_id = self.find_job_id(job_name)
        if job_id is None:
            raise RuntimeError(f"Job {job_name} not found. Deploy workflows first.")
        print(f"Triggering {job_name} (job_id={job_id})")
        return self._session.workspace.jobs.run_now_and_wait(
            job_id=job_id, job_parameters=job_parameters or {}
        )

    def _mkdir(self, path: str) -> None:
        self._session.workspace.workspace.mkdirs(path)

    def _job_parameters(self) -> list[JobParameterDefinition]:
        return [
            JobParameterDefinition(name="catalog_name", default=self._settings.catalog),
            JobParameterDefinition(name="schema_name", default=self._settings.schema),
            JobParameterDefinition(name="warehouse_id", default=self._settings.warehouse_id),
            JobParameterDefinition(name="parent_path", default=self._session.parent_path),
            JobParameterDefinition(name="agent_title", default=self._settings.agent_title),
            JobParameterDefinition(name="space_id", default=self._settings.genie_space_id),
            JobParameterDefinition(name="package_path", default=self._settings.package_workspace_path),
            JobParameterDefinition(name="confirm", default=""),
        ]

    @staticmethod
    def _base_parameters(extra: dict[str, str] | None = None) -> dict[str, str]:
        params = {
            "catalog_name": "{{job.parameters.catalog_name}}",
            "schema_name": "{{job.parameters.schema_name}}",
            "warehouse_id": "{{job.parameters.warehouse_id}}",
            "parent_path": "{{job.parameters.parent_path}}",
            "agent_title": "{{job.parameters.agent_title}}",
            "space_id": "{{job.parameters.space_id}}",
            "package_path": "{{job.parameters.package_path}}",
            "confirm": "{{job.parameters.confirm}}",
        }
        if extra:
            params.update(extra)
        return params

    @staticmethod
    def _notebook_source(task_module: str, facade_module: str, facade_class: str) -> str:
        return f"""# Databricks notebook source
dbutils.widgets.text("catalog_name", "genie_ontology_demo", "Catalog name")
dbutils.widgets.text("schema_name", "retail_demo", "Schema name")
dbutils.widgets.text("warehouse_id", "", "SQL warehouse ID")
dbutils.widgets.text("parent_path", "", "Genie agent parent folder")
dbutils.widgets.text("agent_title", "Retail Analytics Genie", "Genie agent title")
dbutils.widgets.text("space_id", "", "Existing Genie space ID")
dbutils.widgets.text("package_path", "", "Workspace path to uploaded package src/")
dbutils.widgets.text("question", "", "Question for invoke tasks")
dbutils.widgets.text("confirm", "", "Type DELETE to confirm cleanup")

# COMMAND ----------

import sys

package_path = dbutils.widgets.get("package_path")
if package_path:
    sys.path.insert(0, package_path)

from {task_module} import run
from {facade_module} import {facade_class}

run({facade_class}.from_databricks(dbutils=dbutils, spark=spark))
"""
