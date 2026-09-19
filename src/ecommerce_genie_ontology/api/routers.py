from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ecommerce_genie_ontology.api.schemas import (
    DpReq,
    DpRespResult,
    HlReq,
    HlRespResult,
    LsReq,
    LsRespResult,
    PwReq,
    PwRespResult,
    DyReq,
    DyRespResult,
    TcReq,
    TcRespResult,
    WfReq,
    WfRespResult,
    WhReq,
    WhRespResult,
    EcReq,
    EcRespResult,
    EhReq,
    EhRespResult,
    FcReq,
    FcRespResult,
    OdReq,
    OdRespResult,
    OhReq,
    OhRespResult,
    ChReq,
    ChRespResult,
)
from ecommerce_genie_ontology.common.constants.fraud_agents import FRAUD_AGENTS, case_names
from ecommerce_genie_ontology.common.constants.fraud_cases import FRAUD_CASES
from ecommerce_genie_ontology.common.dtos.pipeline import EcCtx, EcResp, EhCtx, EhResp, FcCtx, FcResp, OdCtx, OdResp, OhCtx, OhResp
from ecommerce_genie_ontology.common.dtos.chat import ChCtx, ChResp
from ecommerce_genie_ontology.api.services import WorkflowsApiService
from ecommerce_genie_ontology.common.dtos.ontology import (
    DpCtx,
    DpResp,
    HlCtx,
    HlResp,
    LsCtx,
    LsResp,
    PwCtx,
    PwResp,
    DyCtx,
    DyResp,
    TcCtx,
    TcResp,
    WfCtx,
    WfResp,
    WhCtx,
    WhResp,
)


class HealthRouter:
    def __init__(self, service: WorkflowsApiService) -> None:
        self._service = service
        self.router = APIRouter(tags=["health"])
        self.router.add_api_route("/health", self.health, methods=["GET"], response_model=HlRespResult)

    def health(self) -> HlRespResult:
        ctx = HlCtx(HlReq(), HlResp())
        self._service.health(ctx)
        return HlRespResult.of(ctx.resp)


class OntologyRouter:
    def __init__(self, service: WorkflowsApiService) -> None:
        self._service = service
        self.router = APIRouter(prefix="/api/v1/ontology", tags=["ontology"])
        self.router.add_api_route(
            "/workflows", self.list_workflows, methods=["GET"], response_model=LsRespResult
        )
        self.router.add_api_route(
            "/workflows/run", self.run_workflow, methods=["POST"], response_model=WfRespResult
        )
        self.router.add_api_route(
            "/workflows/deploy", self.deploy, methods=["POST"], response_model=DpRespResult
        )
        self.router.add_api_route(
            "/provision-workspace",
            self.provision_workspace,
            methods=["POST"],
            response_model=PwRespResult,
        )
        self.router.add_api_route(
            "/provision-warehouse",
            self.provision_warehouse,
            methods=["POST"],
            response_model=WhRespResult,
        )
        self.router.add_api_route(
            "/truncate",
            self.truncate,
            methods=["POST"],
            response_model=TcRespResult,
        )
        self.router.add_api_route(
            "/destroy",
            self.destroy,
            methods=["POST"],
            response_model=DyRespResult,
        )
        self.router.add_api_route(
            "/oltp/historical",
            self.generate_historical,
            methods=["POST"],
            response_model=OhRespResult,
        )
        self.router.add_api_route(
            "/oltp/realtime",
            self.generate_realtime,
            methods=["POST"],
            response_model=OdRespResult,
        )
        self.router.add_api_route(
            "/etl/historical",
            self.etl_historical,
            methods=["POST"],
            response_model=EhRespResult,
        )
        self.router.add_api_route(
            "/etl/cdc",
            self.etl_cdc,
            methods=["POST"],
            response_model=EcRespResult,
        )
        self.router.add_api_route("/fraud/cases", self.list_fraud_cases, methods=["GET"])
        self.router.add_api_route("/fraud/agents", self.list_fraud_agents, methods=["GET"])
        self.router.add_api_route(
            "/chat",
            self.chat,
            methods=["POST"],
            response_model=ChRespResult,
        )
        self.router.add_api_route(
            "/fraud/run",
            self.run_fraud_case,
            methods=["POST"],
            response_model=FcRespResult,
        )

    def list_workflows(self) -> LsRespResult:
        ctx = LsCtx(LsReq(), LsResp())
        self._service.list_workflows(ctx)
        return LsRespResult.of(ctx.resp)

    def run_workflow(self, req: WfReq) -> WfRespResult:
        ctx = WfCtx(req, WfResp())
        try:
            self._service.run_workflow(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return WfRespResult.of(ctx.resp)

    def deploy(self, req: DpReq | None = None) -> DpRespResult:
        ctx = DpCtx(req or DpReq(), DpResp())
        try:
            self._service.deploy(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return DpRespResult.of(ctx.resp)

    def provision_workspace(self, req: PwReq) -> PwRespResult:
        ctx = PwCtx(req, PwResp())
        try:
            self._service.provision_workspace(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PwRespResult.of(ctx.resp)

    def provision_warehouse(self, req: WhReq) -> WhRespResult:
        ctx = WhCtx(req, WhResp())
        try:
            self._service.provision_warehouse(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return WhRespResult.of(ctx.resp)

    def truncate(self, req: TcReq) -> TcRespResult:
        ctx = TcCtx(req, TcResp())
        try:
            self._service.truncate(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return TcRespResult.of(ctx.resp)

    def destroy(self, req: DyReq) -> DyRespResult:
        ctx = DyCtx(req, DyResp())
        try:
            self._service.destroy(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return DyRespResult.of(ctx.resp)

    def generate_historical(self, req: OhReq) -> OhRespResult:
        ctx = OhCtx(req, OhResp())
        try:
            self._service.generate_historical(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return OhRespResult.of(ctx.resp)

    def generate_realtime(self, req: OdReq) -> OdRespResult:
        ctx = OdCtx(req, OdResp())
        try:
            self._service.generate_realtime(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return OdRespResult.of(ctx.resp)

    def etl_historical(self, req: EhReq | None = None) -> EhRespResult:
        ctx = EhCtx(req or EhReq(), EhResp())
        try:
            self._service.etl_historical(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return EhRespResult.of(ctx.resp)

    def etl_cdc(self, req: EcReq | None = None) -> EcRespResult:
        ctx = EcCtx(req or EcReq(), EcResp())
        try:
            self._service.etl_cdc(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return EcRespResult.of(ctx.resp)

    def list_fraud_cases(self) -> dict:
        return {"cases": list(FRAUD_CASES)}

    def list_fraud_agents(self) -> dict:
        return {
            "agents": [
                {
                    "id": item["id"],
                    "title": item["title"],
                    "description": item["description"],
                    "case_ids": list(item["case_ids"]),
                    "cases": case_names(item["case_ids"]),  # type: ignore[arg-type]
                }
                for item in FRAUD_AGENTS
            ],
            "backends": ["langgraph", "google_adk", "genie"],
        }

    def chat(self, req: ChReq) -> ChRespResult:
        ctx = ChCtx(req, ChResp())
        try:
            self._service.chat(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return ChRespResult.of(ctx.resp)

    def run_fraud_case(self, req: FcReq) -> FcRespResult:
        ctx = FcCtx(req, FcResp())
        try:
            self._service.run_fraud_case(ctx)
        except SystemExit as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return FcRespResult.of(ctx.resp)
