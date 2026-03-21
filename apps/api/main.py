from __future__ import annotations

from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from agents import comparison_agent, prioritization_agent, structure_agent
from core.config import get_settings
from core.runtime.autogen_runtime import AutoGenRuntime
from core.runtime.local_runtime import LocalRuntime
from core.runtime.nemo_runtime import NemoRuntime
from storage.db import get_decisions, init_db, save_decision

settings = get_settings()

app = FastAPI(title="MHC Atlas OS")


class ParseRequest(BaseModel):
    file_path: str = Field(..., min_length=1)


class CompareFilesRequest(BaseModel):
    wt_file: str = Field(..., min_length=1)
    mutant_file: str = Field(..., min_length=1)


class RankItem(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    comparison: dict[str, Any] = Field(default_factory=dict)


class RankRequest(BaseModel):
    comparisons: list[RankItem] = Field(default_factory=list)


class PipelineRequest(BaseModel):
    wt_file: str = Field(..., min_length=1)
    mutant_file: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    runtime: str = "local"


class BatchPipelineItem(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    wt_file: str = Field(..., min_length=1)
    mutant_file: str = Field(..., min_length=1)


class BatchPipelineRequest(BaseModel):
    runtime: str = "local"
    candidates: list[BatchPipelineItem] = Field(default_factory=list)


class StructureResponse(BaseModel):
    residues: list[dict[str, Any]]
    chains: list[str]
    coordinates: list[dict[str, Any]]
    confidence_summary: dict[str, Any]


class ComparisonResponse(BaseModel):
    residue_changes: list[dict[str, Any]]
    avg_shift: float
    max_shift: float
    large_shift_count: int
    confidence_delta: float
    flags: list[str]
    structure_shift_score: float


class RankedCandidateResponse(BaseModel):
    candidate_id: str
    priority_score: float
    priority_label: str
    explanation: str
    flags: list[str]


class RankResponse(BaseModel):
    ranked_candidates: list[RankedCandidateResponse]


class PipelineResponse(BaseModel):
    candidate_id: str
    wt_structure: StructureResponse
    mutant_structure: StructureResponse
    comparison: ComparisonResponse
    ranking: RankedCandidateResponse
    report_path: str
    decision: dict[str, Any]
    warnings: list[str] | None = None
    logs: list[dict[str, Any]] | None = None
    task_id: str | None = None
    agent_trace: list[str] | None = None


class BatchPipelineResultResponse(BaseModel):
    candidate_id: str
    priority_score: float | None = None
    priority_label: str | None = None
    explanation: str | None = None
    flags: list[str] = Field(default_factory=list)
    error: str | None = None
    warnings: list[str] | None = None
    log_summary: list[str] | None = None
    task_id: str | None = None
    agent_trace: list[str] | None = None


class BatchPipelineResponse(BaseModel):
    results: list[BatchPipelineResultResponse]
    top_candidates: list[BatchPipelineResultResponse]


class DecisionHistoryItemResponse(BaseModel):
    candidate_id: str
    priority_score: float
    priority_label: str
    timestamp: str | None = None
    explanation: str | None = None
    flags: list[str] | None = None


class DecisionHistoryResponse(BaseModel):
    decisions: list[DecisionHistoryItemResponse]


class ReportResponse(BaseModel):
    candidate_id: str
    file_name: str
    content: str


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": app.title}


@app.get("/decisions", response_model=DecisionHistoryResponse, response_model_exclude_none=True)
def decisions_endpoint(candidate_id: str | None = Query(default=None)) -> dict[str, Any]:
    decisions = get_decisions(candidate_id=candidate_id)
    return {
        "decisions": [
            {
                "candidate_id": item["candidate_id"],
                "priority_score": item["priority_score"],
                "priority_label": item["priority_label"],
                "timestamp": item["timestamp"],
                "explanation": item["explanation"],
                "flags": item["flags"],
            }
            for item in decisions
        ]
    }


@app.get("/report", response_model=ReportResponse)
def report_endpoint(candidate_id: str = Query(..., min_length=1)) -> dict[str, Any]:
    report_path = Path("reports") / f"{candidate_id}.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail=f"Report not found for candidate: {candidate_id}")
    return {
        "candidate_id": candidate_id,
        "file_name": report_path.name,
        "content": report_path.read_text(encoding="utf-8"),
    }


@app.post("/parse", response_model=StructureResponse)
def parse_endpoint(payload: ParseRequest) -> dict[str, Any]:
    return _parse_file(payload.file_path)


@app.post("/compare", response_model=ComparisonResponse)
def compare_endpoint(payload: CompareFilesRequest) -> dict[str, Any]:
    wt_structure = _parse_file(payload.wt_file)
    mutant_structure = _parse_file(payload.mutant_file)
    return comparison_agent.run(
        {"wt_structure": wt_structure, "mutant_structure": mutant_structure}
    )["output"]


@app.post("/rank", response_model=RankResponse)
def rank_endpoint(payload: RankRequest) -> dict[str, Any]:
    ranked = prioritization_agent.run(
        {"comparison_results": [item.model_dump() for item in payload.comparisons]}
    )["output"]
    return {"ranked_candidates": ranked}


@app.post("/pipeline", response_model=PipelineResponse, response_model_exclude_none=True)
def pipeline_endpoint(payload: PipelineRequest) -> dict[str, Any]:
    runtime = _get_runtime(payload.runtime)
    runtime_result = runtime.run(
        {
            "candidate_id": payload.candidate_id,
            "wt_file": payload.wt_file,
            "mutant_file": payload.mutant_file,
        }
    )
    orchestrated, extras = _normalize_runtime_result(runtime_result)

    structure_stage = orchestrated["stages"]["structure"]["output"]
    comparison = orchestrated["stages"]["comparison"]["output"]
    ranking = orchestrated["stages"]["policy"]["output"]

    decision = save_decision(
        candidate_id=payload.candidate_id,
        priority_score=ranking["priority_score"],
        priority_label=ranking["priority_label"],
        explanation=ranking["explanation"],
        flags=ranking["flags"],
    )
    report_path = str(Path("reports") / f"{payload.candidate_id}.md")
    return {
        "candidate_id": payload.candidate_id,
        "wt_structure": structure_stage["wt"],
        "mutant_structure": structure_stage["mutant"],
        "comparison": comparison,
        "ranking": ranking,
        "report_path": report_path,
        "decision": decision,
        **extras,
    }


@app.post("/batch_pipeline", response_model=BatchPipelineResponse, response_model_exclude_none=True)
def batch_pipeline_endpoint(payload: BatchPipelineRequest) -> dict[str, Any]:
    runtime = _get_runtime(payload.runtime)
    results: list[dict[str, Any]] = []

    for candidate in payload.candidates:
        try:
            runtime_result = runtime.run(
                {
                    "candidate_id": candidate.candidate_id,
                    "wt_file": candidate.wt_file,
                    "mutant_file": candidate.mutant_file,
                }
            )
            orchestrated, extras = _normalize_runtime_result(runtime_result)
            ranking = orchestrated["stages"]["policy"]["output"]
            row = {
                "candidate_id": ranking["candidate_id"],
                "priority_score": ranking["priority_score"],
                "priority_label": ranking["priority_label"],
                "explanation": ranking["explanation"],
                "flags": ranking["flags"],
            }
            if extras.get("warnings"):
                row["warnings"] = extras["warnings"]
            if extras.get("task_id"):
                row["task_id"] = extras["task_id"]
            if extras.get("agent_trace"):
                row["agent_trace"] = extras["agent_trace"]
            if extras.get("logs"):
                row["log_summary"] = [
                    f"{entry.get('stage', 'unknown')}:{entry.get('status', 'unknown')}"
                    for entry in extras["logs"]
                ]
            results.append(row)
        except HTTPException as exc:
            results.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "error": exc.detail,
                    "flags": [],
                }
            )
        except Exception as exc:  # pragma: no cover - defensive wrapper
            results.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "error": f"Unexpected error while processing candidate: {exc}",
                    "flags": [],
                }
            )

    successful_results = [
        result for result in results if result.get("priority_score") is not None
    ]
    successful_results.sort(
        key=lambda item: float(item["priority_score"]),
        reverse=True,
    )
    error_results = [result for result in results if result.get("error")]

    sorted_results = successful_results + error_results

    return {
        "results": sorted_results,
        "top_candidates": successful_results[:3],
    }


def run() -> None:
    uvicorn.run(
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


def _parse_file(file_path: str) -> dict[str, Any]:
    try:
        normalized_path = str(Path(file_path))
        return structure_agent.run({"structure_path": normalized_path})["output"]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise HTTPException(status_code=500, detail=f"Unexpected error while parsing structure: {exc}") from exc


def _get_runtime(runtime_name: str):
    normalized = str(runtime_name).lower()
    if normalized == "nemo":
        return NemoRuntime()
    if normalized == "autogen":
        return AutoGenRuntime()
    return LocalRuntime()


def _normalize_runtime_result(runtime_result: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if runtime_result.get("status") == "blocked":
        raise HTTPException(status_code=400, detail=runtime_result.get("reason", "Execution blocked."))
    if runtime_result.get("status") == "error" and "result" not in runtime_result:
        detail = runtime_result.get("error")
        if not detail:
            failed_log = next(
                (entry for entry in reversed(runtime_result.get("logs", [])) if entry.get("status") in {"failure", "error"}),
                None,
            )
            detail = failed_log.get("message") if failed_log else "Pipeline execution failed."
        if "not found" in str(detail).lower():
            raise HTTPException(status_code=404, detail=str(detail))
        raise HTTPException(status_code=400, detail=str(detail))

    if "result" in runtime_result:
        return runtime_result["result"], {
            "warnings": runtime_result.get("warnings"),
            "logs": runtime_result.get("logs"),
            "task_id": runtime_result.get("task_id"),
            "agent_trace": runtime_result.get("agent_trace"),
        }

    return runtime_result, {}


if __name__ == "__main__":
    run()
