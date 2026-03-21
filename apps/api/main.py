from __future__ import annotations

from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from agents import comparison_agent, prioritization_agent, review_agent, structure_agent
from core.config import get_settings
from core.runtime.local_runtime import LocalRuntime
from core.policies.policy_engine import apply_policies
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


class BatchPipelineItem(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    wt_file: str = Field(..., min_length=1)
    mutant_file: str = Field(..., min_length=1)


class BatchPipelineRequest(BaseModel):
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


class BatchPipelineResultResponse(BaseModel):
    candidate_id: str
    priority_score: float | None = None
    priority_label: str | None = None
    explanation: str | None = None
    flags: list[str] = Field(default_factory=list)
    error: str | None = None


class BatchPipelineResponse(BaseModel):
    results: list[BatchPipelineResultResponse]
    top_candidates: list[BatchPipelineResultResponse]


class DecisionHistoryItemResponse(BaseModel):
    candidate_id: str
    priority_score: float
    priority_label: str
    timestamp: str | None = None


class DecisionHistoryResponse(BaseModel):
    decisions: list[DecisionHistoryItemResponse]


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
            }
            for item in decisions
        ]
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


@app.post("/pipeline", response_model=PipelineResponse)
def pipeline_endpoint(payload: PipelineRequest) -> dict[str, Any]:
    runtime = LocalRuntime()
    orchestrated = runtime.run(
        {
            "candidate_id": payload.candidate_id,
            "wt_file": payload.wt_file,
            "mutant_file": payload.mutant_file,
        }
    )
    if orchestrated["status"] == "error":
        failed_log = next(
            (entry for entry in reversed(orchestrated["logs"]) if entry["status"] == "failure"),
            None,
        )
        detail = failed_log["message"] if failed_log else "Pipeline execution failed."
        if "not found" in detail.lower():
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)

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
    }


@app.post("/batch_pipeline", response_model=BatchPipelineResponse, response_model_exclude_none=True)
def batch_pipeline_endpoint(payload: BatchPipelineRequest) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for candidate in payload.candidates:
        try:
            pipeline_result = _run_pipeline(
                candidate.candidate_id,
                candidate.wt_file,
                candidate.mutant_file,
            )
            ranking = pipeline_result["ranking"]
            results.append(
                {
                    "candidate_id": ranking["candidate_id"],
                    "priority_score": ranking["priority_score"],
                    "priority_label": ranking["priority_label"],
                    "explanation": ranking["explanation"],
                    "flags": ranking["flags"],
                }
            )
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


def _run_pipeline(candidate_id: str, wt_file: str, mutant_file: str) -> dict[str, Any]:
    wt_structure = _parse_file(wt_file)
    mutant_structure = _parse_file(mutant_file)
    comparison = comparison_agent.run(
        {"wt_structure": wt_structure, "mutant_structure": mutant_structure}
    )["output"]
    ranked = prioritization_agent.run(
        {
            "comparison_results": [
                {
                    "candidate_id": candidate_id,
                    "comparison": comparison,
                }
            ]
        }
    )["output"]
    ranking = apply_policies(
        {
            **ranked[0],
            "comparison": comparison,
            "mutant_confidence": mutant_structure.get("confidence_summary", {}).get("avg"),
        }
    )
    pipeline_output = {
        "candidate_id": candidate_id,
        "wt_structure": wt_structure,
        "mutant_structure": mutant_structure,
        "comparison": comparison,
        "ranking": ranking,
    }
    review_agent.run({"ranked_candidates": [ranking], "pipeline_output": pipeline_output})
    decision = save_decision(
        candidate_id=candidate_id,
        priority_score=ranking["priority_score"],
        priority_label=ranking["priority_label"],
        explanation=ranking["explanation"],
        flags=ranking["flags"],
    )
    report_path = str(Path("reports") / f"{candidate_id}.md")
    return {
        "candidate_id": candidate_id,
        "wt_structure": wt_structure,
        "mutant_structure": mutant_structure,
        "comparison": comparison,
        "ranking": ranking,
        "report_path": report_path,
        "decision": decision,
    }


if __name__ == "__main__":
    run()
