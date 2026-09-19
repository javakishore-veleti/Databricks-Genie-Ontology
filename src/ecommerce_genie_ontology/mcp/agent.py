"""Scripted fraud agent: walk 15 cases and collect bounded evidence packs.

An LLM agent (Cursor, Claude Desktop, Databricks Genie) should call the MCP
tools instead of this script. This runner is the same loop without an LLM:
list cases, run each SQL pack, keep at most 50 rows. It never loads OLTP or
facts into context.
"""

from __future__ import annotations

from ecommerce_genie_ontology.common.constants.fraud_cases import FRAUD_CASES
from ecommerce_genie_ontology.common.dtos.pipeline import FcCtx, FcReq, FcResp
from ecommerce_genie_ontology.common.utils.env import load_env
from ecommerce_genie_ontology.workflows.objects_factory import WorkflowsObjectsFactory


def run_fraud_agent(case_ids: list[str] | None = None) -> list[dict]:
    load_env()
    wanted = {item.strip() for item in (case_ids or []) if item.strip()}
    cases = [item for item in FRAUD_CASES if not wanted or item["id"] in wanted]
    if wanted and len(cases) != len(wanted):
        known = {item["id"] for item in FRAUD_CASES}
        missing = sorted(wanted - known)
        raise SystemExit(f"Unknown fraud case id(s): {', '.join(missing)}")
    runner = WorkflowsObjectsFactory.instance().orchestrator()
    packs: list[dict] = []
    for case in cases:
        ctx = FcCtx(FcReq(case_id=case["id"]), FcResp())
        runner.run_fraud_case(ctx)
        pack = {
            "case_id": ctx.resp.case_id,
            "name": ctx.resp.name,
            "message": ctx.resp.message,
            "row_count": len(ctx.resp.rows),
            "rows": ctx.resp.rows,
        }
        packs.append(pack)
        print(f"{pack['case_id']} {pack['name']}: {pack['message']}")
    return packs
