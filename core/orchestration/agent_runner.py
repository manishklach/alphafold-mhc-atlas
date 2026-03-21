from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents import comparison_agent, prioritization_agent, review_agent, structure_agent
from core.policies.policy_engine import apply_policies


def run_agent_pipeline(candidate_id: str, wt_file: str, mutant_file: str) -> dict[str, Any]:
    # The orchestration layer is responsible for sequencing reusable domain agents.
    # It does not decide which runtime is active; runtimes call into this function.
    # Keeping orchestration separate from runtime selection makes execution
    # pluggable across local, governed, and multi-agent modes.
    logs: list[dict[str, Any]] = []
    stages: dict[str, Any] = {}
    overall_start = _utcnow()

    structure_stage = _run_structure_stage(wt_file, mutant_file, logs)
    if structure_stage["status"] == "error":
        return _error_result(candidate_id, stages | {"structure": structure_stage}, logs, overall_start)
    stages["structure"] = structure_stage

    comparison_stage = _run_comparison_stage(structure_stage["output"], logs)
    if comparison_stage["status"] == "error":
        return _error_result(candidate_id, stages | {"comparison": comparison_stage}, logs, overall_start)
    stages["comparison"] = comparison_stage

    prioritization_stage = _run_prioritization_stage(
        candidate_id,
        comparison_stage["output"],
        logs,
    )
    if prioritization_stage["status"] == "error":
        return _error_result(candidate_id, stages | {"prioritization": prioritization_stage}, logs, overall_start)
    stages["prioritization"] = prioritization_stage

    policy_stage = _run_policy_stage(
        prioritization_stage["output"],
        comparison_stage["output"],
        structure_stage["output"],
        candidate_id,
        logs,
    )
    if policy_stage["status"] == "error":
        return _error_result(candidate_id, stages | {"policy": policy_stage}, logs, overall_start)
    stages["policy"] = policy_stage

    review_stage = _run_review_stage(
        candidate_id,
        structure_stage["output"],
        comparison_stage["output"],
        policy_stage["output"],
        logs,
    )
    if review_stage["status"] == "error":
        return _error_result(candidate_id, stages | {"review": review_stage}, logs, overall_start)
    stages["review"] = review_stage

    final_output = {
        "ranking": policy_stage["output"],
        "review": review_stage["output"],
        "confidence_summary": _build_final_confidence_summary(
            structure_stage["output"],
            policy_stage["output"],
        ),
    }
    return {
        "candidate_id": candidate_id,
        "status": "success",
        "stages": stages,
        "final_output": final_output,
        "logs": logs,
        "total_duration_ms": _duration_ms(overall_start, _utcnow()),
    }


def _run_structure_stage(wt_file: str, mutant_file: str, logs: list[dict[str, Any]]) -> dict[str, Any]:
    stage = "structure"
    started_at = _utcnow()
    input_summary = f"WT file={wt_file}; mutant file={mutant_file}"
    _log(logs, stage, "started", "Parsing WT and mutant structures.", input_summary, "", 0)
    try:
        wt_result = structure_agent.run({"structure_path": wt_file})
        mutant_result = structure_agent.run({"structure_path": mutant_file})
        output = {
            "wt": wt_result["output"],
            "mutant": mutant_result["output"],
        }
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        output_summary = (
            f"WT residues={len(output['wt'].get('residues', []))}; "
            f"mutant residues={len(output['mutant'].get('residues', []))}"
        )
        result = {
            "status": "success",
            "agent": "structure_agent",
            "output": output,
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }
        _log(logs, stage, "success", "Parsed WT and mutant structures successfully.", input_summary, output_summary, duration_ms)
        return result
    except Exception as exc:
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        _log(
            logs,
            stage,
            "failure",
            f"Failed to parse structures: {exc}",
            input_summary,
            "No structures parsed.",
            duration_ms,
        )
        return {
            "status": "error",
            "agent": "structure_agent",
            "message": f"Failed to parse structures: {exc}",
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }


def _run_comparison_stage(structure_output: dict[str, Any], logs: list[dict[str, Any]]) -> dict[str, Any]:
    stage = "comparison"
    started_at = _utcnow()
    input_summary = (
        f"WT residues={len(structure_output['wt'].get('residues', []))}; "
        f"mutant residues={len(structure_output['mutant'].get('residues', []))}"
    )
    _log(logs, stage, "started", "Comparing parsed structures.", input_summary, "", 0)
    try:
        result = comparison_agent.run(
            {
                "wt_structure": structure_output["wt"],
                "mutant_structure": structure_output["mutant"],
            }
        )
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        output_summary = (
            f"avg_shift={result['output'].get('avg_shift', 0.0):.2f} Å; "
            f"flags={len(result['output'].get('flags', []))}"
        )
        _log(logs, stage, "success", "Compared WT and mutant structures successfully.", input_summary, output_summary, duration_ms)
        return {
            "status": "success",
            "agent": result["agent"],
            "output": result["output"],
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        _log(logs, stage, "failure", f"Failed to compare structures: {exc}", input_summary, "No comparison generated.", duration_ms)
        return {
            "status": "error",
            "agent": "comparison_agent",
            "message": f"Failed to compare structures: {exc}",
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }


def _run_prioritization_stage(
    candidate_id: str,
    comparison_output: dict[str, Any],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    stage = "prioritization"
    started_at = _utcnow()
    input_summary = (
        f"candidate_id={candidate_id}; avg_shift={comparison_output.get('avg_shift', 0.0):.2f} Å"
    )
    _log(logs, stage, "started", "Scoring candidate with prioritization agent.", input_summary, "", 0)
    try:
        result = prioritization_agent.run(
            {
                "comparison_results": [
                    {
                        "candidate_id": candidate_id,
                        "comparison": comparison_output,
                    }
                ]
            }
        )
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        output_summary = (
            f"score={result['output'][0].get('priority_score', 0.0):.2f}; "
            f"label={result['output'][0].get('priority_label', '')}"
        )
        _log(logs, stage, "success", "Scored candidate successfully.", input_summary, output_summary, duration_ms)
        return {
            "status": "success",
            "agent": result["agent"],
            "output": result["output"][0],
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        _log(logs, stage, "failure", f"Failed to score candidate: {exc}", input_summary, "No ranking generated.", duration_ms)
        return {
            "status": "error",
            "agent": "prioritization_agent",
            "message": f"Failed to score candidate: {exc}",
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }


def _run_policy_stage(
    ranking_output: dict[str, Any],
    comparison_output: dict[str, Any],
    structure_output: dict[str, Any],
    candidate_id: str,
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    stage = "policy"
    started_at = _utcnow()
    input_summary = (
        f"candidate_id={candidate_id}; label={ranking_output.get('priority_label', '')}; "
        f"mutant_confidence={structure_output['mutant'].get('confidence_summary', {}).get('avg')}"
    )
    _log(logs, stage, "started", "Applying policy rules to ranking output.", input_summary, "", 0)
    try:
        policy_output = apply_policies(
            {
                **ranking_output,
                "candidate_id": candidate_id,
                "comparison": comparison_output,
                "mutant_confidence": structure_output["mutant"].get("confidence_summary", {}).get("avg"),
            }
        )
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        output_summary = (
            f"score={policy_output.get('priority_score', 0.0):.2f}; "
            f"label={policy_output.get('priority_label', '')}; flags={len(policy_output.get('flags', []))}"
        )
        _log(logs, stage, "success", "Applied policy rules successfully.", input_summary, output_summary, duration_ms)
        return {
            "status": "success",
            "agent": "policy_engine",
            "output": policy_output,
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        _log(logs, stage, "failure", f"Failed to apply policy rules: {exc}", input_summary, "No policy-adjusted ranking.", duration_ms)
        return {
            "status": "error",
            "agent": "policy_engine",
            "message": f"Failed to apply policy rules: {exc}",
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }


def _run_review_stage(
    candidate_id: str,
    structure_output: dict[str, Any],
    comparison_output: dict[str, Any],
    policy_output: dict[str, Any],
    logs: list[dict[str, Any]],
) -> dict[str, Any]:
    stage = "review"
    started_at = _utcnow()
    input_summary = (
        f"candidate_id={candidate_id}; label={policy_output.get('priority_label', '')}; "
        f"flags={len(policy_output.get('flags', []))}"
    )
    _log(logs, stage, "started", "Generating final review summary payload.", input_summary, "", 0)
    try:
        pipeline_output = {
            "candidate_id": candidate_id,
            "wt_structure": structure_output["wt"],
            "mutant_structure": structure_output["mutant"],
            "comparison": comparison_output,
            "ranking": policy_output,
        }
        result = review_agent.run(
            {
                "ranked_candidates": [policy_output],
                "pipeline_output": pipeline_output,
            }
        )
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        output_summary = (
            f"top_candidates={len(result['output'].get('top_candidates', []))}; "
            f"flagged={result['output'].get('summary', {}).get('num_flagged', 0)}"
        )
        _log(logs, stage, "success", "Generated review summary successfully.", input_summary, output_summary, duration_ms)
        return {
            "status": "success",
            "agent": result["agent"],
            "output": result["output"],
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        ended_at = _utcnow()
        duration_ms = _duration_ms(started_at, ended_at)
        _log(logs, stage, "failure", f"Failed to generate review summary: {exc}", input_summary, "No review summary generated.", duration_ms)
        return {
            "status": "error",
            "agent": "review_agent",
            "message": f"Failed to generate review summary: {exc}",
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
            "duration_ms": duration_ms,
        }


def _log(
    logs: list[dict[str, Any]],
    stage: str,
    status: str,
    message: str,
    input_summary: str,
    output_summary: str,
    duration_ms: int,
) -> None:
    logs.append(
        {
            "stage": stage,
            "status": status,
            "message": message,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "duration_ms": duration_ms,
        }
    )


def _error_result(
    candidate_id: str,
    stages: dict[str, Any],
    logs: list[dict[str, Any]],
    overall_start: datetime,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "status": "error",
        "stages": stages,
        "final_output": {},
        "logs": logs,
        "total_duration_ms": _duration_ms(overall_start, _utcnow()),
    }


def _build_final_confidence_summary(
    structure_output: dict[str, Any],
    ranking_output: dict[str, Any],
) -> dict[str, Any]:
    wt_confidence = structure_output["wt"].get("confidence_summary", {}).get("avg")
    mutant_confidence = structure_output["mutant"].get("confidence_summary", {}).get("avg")
    confidence_delta = None
    if wt_confidence is not None and mutant_confidence is not None:
        confidence_delta = round(float(mutant_confidence) - float(wt_confidence), 2)
    return {
        "wt_avg_confidence": wt_confidence,
        "mutant_avg_confidence": mutant_confidence,
        "confidence_delta": confidence_delta,
        "priority_label": ranking_output.get("priority_label"),
        "flags": ranking_output.get("flags", []),
    }


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _duration_ms(started_at: datetime, ended_at: datetime) -> int:
    return max(0, int((ended_at - started_at).total_seconds() * 1000))
