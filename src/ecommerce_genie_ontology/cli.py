"""CLI: deploy Databricks workflows or run the same tasks from this machine."""

from __future__ import annotations

import argparse

from ecommerce_genie_ontology.common.interfaces.workflow import WorkflowRunner
from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory


class CliApp:
    def __init__(self, runner: WorkflowRunner) -> None:
        self._runner = runner

    def main(self, argv: list[str] | None = None) -> int:
        parser = self._build_parser()
        args = parser.parse_args(argv)
        settings = WorkflowsObjectsFactory.instance().settings()
        if settings.env_file:
            print(f"Loaded credentials from {settings.env_file}")
        else:
            print("No .env file found; using process environment")

        if args.command == "deploy":
            self._runner.deploy()
            return 0
        if args.command == "run":
            if args.as_job:
                self._runner.trigger(args.workflow, confirm=args.confirm)
            else:
                self._runner.run(args.workflow, question=args.question, confirm=args.confirm)
            return 0
        if args.command == "serve":
            self._serve(args.host, args.port)
            return 0
        parser.error(f"Unknown command {args.command}")
        return 2

    def _serve(self, host: str, port: int) -> None:
        import uvicorn

        uvicorn.run("ecommerce_genie_ontology.api.app:app", host=host, port=port, reload=False)

    @staticmethod
    def _build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="genie-ontology",
            description=(
                "Provision the ecommerce Genie Ontology demo, create the Genie agent, "
                "and invoke it. Credentials come from .env. Use uv, not pip."
            ),
        )
        sub = parser.add_subparsers(dest="command", required=True)
        sub.add_parser("deploy", help="Upload task code and create/update the Databricks workflows")
        run = sub.add_parser("run", help="Run a workflow locally (default) or as a Databricks job")
        run.add_argument(
            "workflow",
            choices=["provision", "create_agents", "invoke_agents", "cleanup", "all"],
            help="Workflow to run. 'all' is provision, then create_agents, then invoke_agents.",
        )
        run.add_argument(
            "--as-job",
            action="store_true",
            help="Trigger the Databricks workflow created by `deploy` instead of running locally.",
        )
        run.add_argument("--question", default="", help="Override invoke_agents with a single question")
        run.add_argument("--confirm", default="", help="Required value DELETE for the cleanup workflow")
        serve = sub.add_parser("serve", help="Start the FastAPI HTTP interface")
        serve.add_argument("--host", default="127.0.0.1")
        serve.add_argument("--port", type=int, default=8000)
        return parser


def main(argv: list[str] | None = None) -> int:
    runner = WorkflowsObjectsFactory.instance().orchestrator()
    return CliApp(runner).main(argv)
