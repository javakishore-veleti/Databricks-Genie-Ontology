from __future__ import annotations

from ecommerce_genie_ontology.adapter_databricks.daos.jobs_dao import JobsDao
from ecommerce_genie_ontology.common.dtos.jobs import JobSpec
from ecommerce_genie_ontology.common.dtos.settings import Settings
from ecommerce_genie_ontology.common.interfaces.jobs import JobsFacade


class JobsFacadeImpl:
    def __init__(self, jobs_dao: JobsDao, settings: Settings) -> None:
        self._jobs = jobs_dao
        self._settings = settings

    def deploy(self, jobs: list[JobSpec]) -> dict[str, int]:
        print(f"Uploading package + notebooks to {self._settings.workspace_path}")
        self._jobs.upload_package()
        self._jobs.upload_notebooks(jobs)
        job_ids = {job.workflow_name: self._jobs.upsert_job(job) for job in jobs}
        host = self._settings.host.rstrip("/")
        print("\nDatabricks workflows:")
        for job in jobs:
            print(f"  {job.job_name}: {host}/#job/{job_ids[job.workflow_name]}")
        return job_ids

    def trigger(self, job_name: str, job_parameters: dict[str, str] | None = None) -> object:
        run = self._jobs.trigger(job_name, job_parameters)
        state = getattr(run, "state", None)
        result_state = state.result_state.value if state and state.result_state else "UNKNOWN"
        life_cycle = state.life_cycle_state.value if state and state.life_cycle_state else "UNKNOWN"
        print(f"Run {getattr(run, 'run_id', None)} finished: {life_cycle}/{result_state}")
        if result_state not in {"SUCCESS", "SUCCEEDED"}:
            raise RuntimeError(f"Workflow {job_name} did not succeed ({result_state})")
        return run


def _assert_protocol() -> None:
    _: type[JobsFacade] = JobsFacadeImpl
