from __future__ import annotations

from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agents import comparison_agent, prioritization_agent, review_agent, structure_agent
from core.config import get_settings
from core.policies.policy_engine import apply_policies
from storage.db import init_db, save_decision

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


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": app.title}


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
    wt_structure = _parse_file(payload.wt_file)
    mutant_structure = _parse_file(payload.mutant_file)
    comparison = comparison_agent.run(
        {"wt_structure": wt_structure, "mutant_structure": mutant_structure}
    )["output"]
    ranked = prioritization_agent.run(
        [
            {
                "comparison_results": [
                    {
                        "candidate_id": payload.candidate_id,
                        "comparison": comparison,
                    }
                ]
            }
        ][0]
    )["output"]
    ranking = apply_policies(
        {
            **ranked[0],
            "comparison": comparison,
            "mutant_confidence": mutant_structure.get("confidence_summary", {}).get("avg"),
        }
    )
    pipeline_output = {
        "candidate_id": payload.candidate_id,
        "wt_structure": wt_structure,
        "mutant_structure": mutant_structure,
        "comparison": comparison,
        "ranking": ranking,
    }
    review_agent.run({"ranked_candidates": [ranking], "pipeline_output": pipeline_output})
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
        "wt_structure": wt_structure,
        "mutant_structure": mutant_structure,
        "comparison": comparison,
        "ranking": ranking,
        "report_path": report_path,
        "decision": decision,
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


if __name__ == "__main__":
    run()
