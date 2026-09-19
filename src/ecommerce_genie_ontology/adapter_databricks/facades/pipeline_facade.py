from __future__ import annotations

from typing import Any

from ecommerce_genie_ontology.adapter_databricks.session import WorkspaceSession
from ecommerce_genie_ontology.adapter_databricks.spark import etl as spark_etl
from ecommerce_genie_ontology.adapter_databricks.spark import ingest as spark_ingest
from ecommerce_genie_ontology.adapter_databricks.spark import oltp as spark_oltp
from ecommerce_genie_ontology.common.constants.fraud_cases import FRAUD_CASES, fraud_sql
from ecommerce_genie_ontology.common.dtos.pipeline import (
    EcCtx,
    EcReq,
    EcResp,
    EhCtx,
    EhReq,
    EhResp,
    EmCtx,
    EmReq,
    EmResp,
    FcCtx,
    NxCtx,
    NxReq,
    NxResp,
    OdCtx,
    OdReq,
    OdResp,
    OhCtx,
    OhReq,
    OhResp,
)
from ecommerce_genie_ontology.common.interfaces.jobs import JobsFacade
from ecommerce_genie_ontology.common.interfaces.pipeline import PipelineFacade
from ecommerce_genie_ontology.common.interfaces.sql import SqlFacade


class PipelineFacadeImpl:
    def __init__(self, session: WorkspaceSession, jobs: JobsFacade, sql: SqlFacade) -> None:
        self._session = session
        self._jobs = jobs
        self._sql = sql

    @classmethod
    def from_factory(cls, factory: Any) -> PipelineFacadeImpl:
        return cls(factory.session(), factory.jobs_facade(), factory.sql_facade())

    @classmethod
    def from_databricks(cls, dbutils: Any, spark: Any) -> PipelineFacadeImpl:
        from ecommerce_genie_ontology.adapter_databricks.objects_factory import AdapterDatabricksObjectsFactory

        factory = AdapterDatabricksObjectsFactory.from_databricks(dbutils, spark)
        return cls.from_factory(factory)

    def generate_historical(self, ctx: OhCtx) -> None:
        ctx.resp.message = self._run_spark_or_job(
            "generate_historical",
            ctx.req.as_job,
            lambda spark: spark_oltp.generate_historical(
                spark,
                self._session.catalog,
                self._session.context.oltp_schema,
                ctx.req.customer_count,
                ctx.req.orders_per_year,
                ctx.req.year_count,
            ),
            {
                "customer_count": str(ctx.req.customer_count),
                "orders_per_year": str(ctx.req.orders_per_year),
                "year_count": str(ctx.req.year_count),
            },
        )
        if isinstance(ctx.resp.message, dict):
            stats = ctx.resp.message
            ctx.resp.customers = int(stats.get("customers", 0))
            ctx.resp.addresses = int(stats.get("addresses", 0))
            ctx.resp.orders = int(stats.get("orders", 0))
            ctx.resp.lines = int(stats.get("lines", 0))
            ctx.resp.message = "generated"
        ctx.resp.status = "ok"

    def generate_realtime(self, ctx: OdCtx) -> None:
        result = self._run_spark_or_job(
            "generate_realtime",
            ctx.req.as_job,
            lambda spark: spark_oltp.generate_realtime(
                spark,
                self._session.catalog,
                self._session.context.oltp_schema,
                ctx.req.count,
                ctx.req.year_window,
            ),
            {"cdc_count": str(ctx.req.count), "year_window": ctx.req.year_window},
        )
        if isinstance(result, dict):
            ctx.resp.orders = int(result.get("orders", 0))
            ctx.resp.lines = int(result.get("lines", 0))
            ctx.resp.year_window = str(result.get("year_window", ctx.req.year_window))
            ctx.resp.message = "generated"
        else:
            ctx.resp.year_window = ctx.req.year_window
            ctx.resp.message = str(result)
        ctx.resp.status = "ok"

    def generate_next_oltp(self, ctx: NxCtx) -> None:
        result = self._run_spark_or_job(
            "generate_next_oltp",
            ctx.req.as_job,
            lambda spark: spark_ingest.generate_next_oltp(
                spark,
                self._session.catalog,
                self._session.context.oltp_schema,
                ctx.req.row_count,
            ),
            {"row_count": str(ctx.req.row_count)},
        )
        if isinstance(result, dict):
            ctx.resp.rows = int(result.get("rows", 0))
            ctx.resp.orders = int(result.get("orders", 0))
            ctx.resp.postings = int(result.get("postings", 0))
            ctx.resp.start_date = str(result.get("start_date", ""))
            ctx.resp.end_date = str(result.get("end_date", ""))
            ctx.resp.year = int(result.get("year", 0) or 0)
            ctx.resp.status = str(result.get("status", "ok"))
            ctx.resp.message = str(result.get("message", "ok"))
        else:
            ctx.resp.status = "ok"
            ctx.resp.message = str(result)

    def etl_historical(self, ctx: EhCtx) -> None:
        self._run_spark_or_job(
            "etl_historical",
            ctx.req.as_job,
            lambda spark: spark_etl.etl_historical(
                spark,
                self._session.catalog,
                self._session.schema_name,
                self._session.context.oltp_schema,
            ),
            {},
        )
        ctx.resp.status = "ok"
        ctx.resp.message = "etl historical completed"

    def etl_cdc(self, ctx: EcCtx) -> None:
        result = self._run_spark_or_job(
            "etl_cdc",
            ctx.req.as_job,
            lambda spark: spark_etl.etl_cdc(
                spark,
                self._session.catalog,
                self._session.schema_name,
                self._session.context.oltp_schema,
            ),
            {},
        )
        ctx.resp.rows = int(result.get("rows", 0)) if isinstance(result, dict) else 0
        ctx.resp.status = "ok"
        ctx.resp.message = "etl cdc completed"

    def etl_next_months(self, ctx: EmCtx) -> None:
        result = self._run_spark_or_job(
            "etl_next_months",
            ctx.req.as_job,
            lambda spark: spark_ingest.etl_next_months(
                spark,
                self._session.catalog,
                self._session.schema_name,
                self._session.context.oltp_schema,
                ctx.req.months,
            ),
            {"months": str(ctx.req.months)},
        )
        if isinstance(result, dict):
            ctx.resp.rows = int(result.get("rows", 0))
            ctx.resp.months = int(result.get("months", ctx.req.months))
            ctx.resp.start_date = str(result.get("start_date", ""))
            ctx.resp.end_date = str(result.get("end_date", ""))
            ctx.resp.year = int(result.get("year", 0) or 0)
            ctx.resp.status = str(result.get("status", "ok"))
            ctx.resp.message = str(result.get("message", "ok"))
        else:
            ctx.resp.status = "ok"
            ctx.resp.message = str(result)

    def run_fraud_case(self, ctx: FcCtx) -> None:
        case = next((item for item in FRAUD_CASES if item["id"] == ctx.req.case_id), None)
        if case is None:
            raise SystemExit(f"Unknown fraud case {ctx.req.case_id!r}")
        oltp = f"{self._session.catalog}.{self._session.context.oltp_schema}"
        star = self._session.fq_schema
        statement = fraud_sql(ctx.req.case_id, oltp, star)
        result = self._sql.execute(statement)
        rows: list[dict] = []
        data = getattr(getattr(result, "result", None), "data_array", None)
        if data:
            for row in data[:50]:
                rows.append({"cols": list(row)})
        ctx.resp.case_id = case["id"]
        ctx.resp.name = case["name"]
        ctx.resp.rows = rows
        ctx.resp.message = f"{len(rows)} evidence rows"

    def run_generate_historical(self) -> None:
        ctx = OhCtx(
            OhReq(
                customer_count=self._session.context.customer_count,
                orders_per_year=self._session.context.orders_per_year,
                year_count=self._session.context.year_count,
                as_job=False,
            ),
            OhResp(),
        )
        self.generate_historical(ctx)

    def run_generate_realtime(self) -> None:
        ctx = OdCtx(
            OdReq(
                count=self._session.context.cdc_count,
                year_window=self._session.context.year_window,
                as_job=False,
            ),
            OdResp(),
        )
        self.generate_realtime(ctx)

    def run_etl_historical(self) -> None:
        self.etl_historical(EhCtx(EhReq(as_job=False), EhResp()))

    def run_etl_cdc(self) -> None:
        self.etl_cdc(EcCtx(EcReq(as_job=False), EcResp()))

    def run_generate_next_oltp(self) -> None:
        self.generate_next_oltp(
            NxCtx(NxReq(row_count=self._session.context.row_count, as_job=False), NxResp())
        )

    def run_etl_next_months(self) -> None:
        self.etl_next_months(EmCtx(EmReq(months=self._session.context.months, as_job=False), EmResp()))

    def _run_spark_or_job(self, workflow: str, as_job: bool, fn, params: dict[str, str]):
        spark = self._session.spark
        if spark is not None:
            return fn(spark) or "ok"
        if as_job:
            self._jobs.trigger(
                f"ecommerce-genie-ontology-{workflow.replace('_', '-')}",
                {
                    "catalog_name": self._session.catalog,
                    "schema_name": self._session.schema_name,
                    "oltp_schema": self._session.context.oltp_schema,
                    "warehouse_id": self._session.warehouse_id,
                    **params,
                },
            )
            return f"triggered job {workflow}"
        raise SystemExit(f"{workflow} needs Spark. Deploy jobs and pass as_job=true.")


def _assert_protocol() -> None:
    _: type[PipelineFacade] = PipelineFacadeImpl
