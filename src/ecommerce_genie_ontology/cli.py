"""CLI: deploy Databricks workflows or run the same tasks from this machine."""

from __future__ import annotations

import argparse

from ecommerce_genie_ontology.common.dtos.ontology import (
    DpCtx,
    DpReq,
    DpResp,
    PwCtx,
    PwReq,
    PwResp,
    DyCtx,
    DyReq,
    DyResp,
    TcCtx,
    TcReq,
    TcResp,
    WfCtx,
    WfReq,
    WfResp,
    WhCtx,
    WhReq,
    WhResp,
)
from ecommerce_genie_ontology.common.dtos.pipeline import (
    EcCtx,
    EcReq,
    EcResp,
    EhCtx,
    EhReq,
    EhResp,
    FcCtx,
    FcReq,
    FcResp,
    OdCtx,
    OdReq,
    OdResp,
    EmCtx,
    EmReq,
    EmResp,
    NxCtx,
    NxReq,
    NxResp,
    OhCtx,
    OhReq,
    OhResp,
)
from ecommerce_genie_ontology.common.interfaces.workflow import WorkflowRunner
from ecommerce_genie_ontology.common.utils.env import find_env_file, load_env
from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory


class CliApp:
    def __init__(self, runner: WorkflowRunner) -> None:
        self._runner = runner

    def main(self, argv: list[str] | None = None) -> int:
        parser = self._build_parser()
        args = parser.parse_args(argv)
        env_file = load_env()
        if env_file or find_env_file():
            print(f"Loaded credentials from {env_file or find_env_file()}")
        else:
            print("No .env file found; using process environment")

        if args.command == "deploy":
            ctx = DpCtx(DpReq(), DpResp())
            self._runner.deploy(ctx)
            return 0
        if args.command == "run":
            return self._run(args)
        if args.command == "serve":
            self._serve(args.host, args.port)
            return 0
        if args.command == "mcp":
            from ecommerce_genie_ontology.mcp.server import main as mcp_main

            mcp_main()
            return 0
        if args.command == "fraud-agent":
            from ecommerce_genie_ontology.mcp.agent import run_fraud_agent

            case_ids = [part.strip() for part in args.cases.split(",") if part.strip()] if args.cases else []
            run_fraud_agent(case_ids or None)
            return 0
        parser.error(f"Unknown command {args.command}")
        return 2

    def _run(self, args: argparse.Namespace) -> int:
        if args.workflow == "provision_workspace":
            ctx = PwCtx(PwReq(), PwResp())
            self._runner.provision_workspace(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "provision_warehouse":
            ctx = WhCtx(WhReq(), WhResp())
            self._runner.provision_warehouse(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "truncate":
            ctx = TcCtx(
                TcReq(catalog=args.catalog, confirm=args.confirm),
                TcResp(),
            )
            self._runner.truncate(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "destroy":
            ctx = DyCtx(
                DyReq(
                    workspace_name=args.workspace_name,
                    warehouse_name=args.warehouse_name,
                    catalog=args.catalog,
                    confirm=args.confirm,
                ),
                DyResp(),
            )
            self._runner.destroy(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "generate_historical":
            ctx = OhCtx(
                OhReq(
                    customer_count=args.customers,
                    orders_per_year=args.orders_per_year,
                    year_count=args.years,
                    as_job=args.as_job,
                ),
                OhResp(),
            )
            self._runner.generate_historical(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "generate_realtime":
            ctx = OdCtx(
                OdReq(count=args.count, year_window=args.year_window, as_job=args.as_job),
                OdResp(),
            )
            self._runner.generate_realtime(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "etl_historical":
            ctx = EhCtx(EhReq(as_job=args.as_job), EhResp())
            self._runner.etl_historical(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "etl_cdc":
            ctx = EcCtx(EcReq(as_job=args.as_job), EcResp())
            self._runner.etl_cdc(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "generate_next_oltp":
            ctx = NxCtx(NxReq(row_count=args.row_count, as_job=args.as_job), NxResp())
            self._runner.generate_next_oltp(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "etl_next_months":
            ctx = EmCtx(EmReq(months=args.months, as_job=args.as_job), EmResp())
            self._runner.etl_next_months(ctx)
            print(ctx.resp)
            return 0
        if args.workflow == "fraud":
            ctx = FcCtx(FcReq(case_id=args.case_id), FcResp())
            self._runner.run_fraud_case(ctx)
            print(ctx.resp)
            return 0
        ctx = WfCtx(
            WfReq(
                workflow=args.workflow,
                question=args.question,
                confirm=args.confirm,
                as_job=args.as_job,
            ),
            WfResp(),
        )
        if args.as_job:
            self._runner.trigger(ctx)
        else:
            self._runner.run(ctx)
        return 0

    def _serve(self, host: str, port: int) -> None:
        import uvicorn

        uvicorn.run("ecommerce_genie_ontology.api.app:app", host=host, port=port, reload=False)

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="genie-ontology",
            description=(
                "Provision the ecommerce Genie Ontology demo, generate OLTP/CDC data, "
                "run star-schema ETL, and invoke Genie or the operational MCP. "
                "Credentials come from .env. Use uv, not pip."
            ),
        )
        sub = parser.add_subparsers(dest="command", required=True)
        sub.add_parser("deploy", help="Upload task code and create/update the Databricks workflows")
        run = sub.add_parser("run", help="Run a workflow locally (default) or as a Databricks job")
        run.add_argument(
            "workflow",
            choices=[
                "provision_workspace",
                "provision_warehouse",
                "provision",
                "create_agents",
                "invoke_agents",
                "cleanup",
                "truncate",
                "destroy",
                "generate_historical",
                "generate_realtime",
                "etl_historical",
                "etl_cdc",
                "generate_next_oltp",
                "etl_next_months",
                "fraud",
                "all",
            ],
            help="Workflow to run.",
        )
        run.add_argument(
            "--as-job",
            action="store_true",
            help="Trigger the Databricks workflow created by `deploy` instead of running locally.",
        )
        run.add_argument("--question", default="", help="Override invoke_agents with a single question")
        run.add_argument("--confirm", default="", help="Required value DELETE for destroy, truncate, and cleanup")
        run.add_argument(
            "--catalog",
            default="",
            help="Catalog for truncate/destroy. Empty uses DATABRICKS_CATALOG.",
        )
        run.add_argument(
            "--workspace-name",
            default="",
            help="Workspace for destroy. Empty uses DATABRICKS_WORKSPACE_NAME.",
        )
        run.add_argument(
            "--warehouse-name",
            default="",
            help="Warehouse for destroy. Empty uses DATABRICKS_WAREHOUSE_NAME.",
        )
        run.add_argument("--customers", type=int, default=200, help="OLTP customers for generate_historical")
        run.add_argument(
            "--orders-per-year",
            type=int,
            default=25000,
            help="Orders per customer per year for generate_historical",
        )
        run.add_argument("--years", type=int, default=3, choices=[1, 2, 3], help="History window ending this month")
        run.add_argument("--count", type=int, default=1000, help="Realtime orders (100-10000)")
        run.add_argument(
            "--year-window",
            default="latest",
            choices=["latest", "last_2", "last_3", "all"],
            help="Date window for realtime orders",
        )
        run.add_argument("--row-count", type=int, default=100000, help="Next OLTP rows (max 100000)")
        run.add_argument("--months", type=int, default=3, choices=list(range(1, 13)), help="Next star months")
        run.add_argument("--case-id", default="01", help="Fraud case id 01-15")
        serve = sub.add_parser("serve", help="Start the FastAPI HTTP interface")
        serve.add_argument("--host", default="127.0.0.1")
        serve.add_argument("--port", type=int, default=8000)
        sub.add_parser("mcp", help="Start the operational MCP server on stdio")
        fraud = sub.add_parser("fraud-agent", help="Run 15 fraud evidence packs (or a subset) via SQL")
        fraud.add_argument(
            "--cases",
            default="",
            help="Comma-separated case ids (01-15). Empty runs all 15.",
        )
        return parser


def main(argv: list[str] | None = None) -> int:
    runner = WorkflowsObjectsFactory.instance().orchestrator()
    return CliApp(runner).main(argv)
