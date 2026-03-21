from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.runtime.local_runtime import LocalRuntime
from core.runtime.nemo_runtime import NemoRuntime
from storage.db import get_decisions, init_db, save_decision


def run_demo_showcase() -> dict[str, Any]:
    init_db()

    local_runtime = LocalRuntime()
    nemo_runtime = NemoRuntime()

    single_result = local_runtime.run(
        {
            "candidate_id": "demo_single",
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut2.pdb",
        }
    )
    _persist_decision(single_result)

    batch_candidates = [
        {
            "candidate_id": "mut1",
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut1.pdb",
        },
        {
            "candidate_id": "mut2",
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut2.pdb",
        },
    ]
    batch_results = [local_runtime.run(candidate) for candidate in batch_candidates]
    sorted_batch = sorted(
        [result for result in batch_results if result.get("status") == "success"],
        key=lambda item: float(item["final_output"]["ranking"]["priority_score"]),
        reverse=True,
    )
    for result in sorted_batch:
        _persist_decision(result)

    nemo_result = nemo_runtime.run(
        {
            "candidate_id": "demo_governed",
            "wt_file": "data/wt.pdb",
            "mutant_file": "data/mut2.pdb",
        }
    )

    history = get_decisions()
    return {
        "single_result": single_result,
        "batch_results": sorted_batch,
        "nemo_result": nemo_result,
        "history": history[:10],
    }


def main() -> None:
    results = run_demo_showcase()
    single = results["single_result"]
    single_ranking = single["final_output"]["ranking"]
    single_comparison = single["stages"]["comparison"]["output"]
    single_confidence = single["final_output"]["confidence_summary"]

    print("MHC Atlas OS Demo Showcase")
    print()
    print("Demo Flow")
    print()
    print("“Here’s a wild-type and mutant structure”")
    print("Click Run Analysis")
    print()
    print(f"Structural shift: avg {single_comparison['avg_shift']:.1f} Å, max {single_comparison['max_shift']:.1f} Å")
    print(f"Confidence change: {single_confidence['confidence_delta']:.1f}")
    print(f"Explanation: {single_ranking['explanation']}")
    print()
    print("“This system explains why a mutation matters, not just scoring it”")
    print()
    print("Then show batch")
    print("“Now instead of one mutation, I can evaluate 20 at once”")
    print()
    print("Ranked shortlist:")
    for index, result in enumerate(results["batch_results"], start=1):
        ranking = result["final_output"]["ranking"]
        print(
            f"  {index}. {ranking['candidate_id']} | "
            f"score={ranking['priority_score']:.1f} | "
            f"label={ranking['priority_label']} | "
            f"flags={', '.join(ranking['flags']) or 'none'}"
        )
    print()
    print("“This gives me a shortlist of candidates to test experimentally”")
    print()
    print("Then show history")
    print("“And the system tracks past decisions, so we can compare over time”")
    print()
    print("Recent decision history:")
    for item in results["history"][:5]:
        print(
            f"  - {item['candidate_id']} | "
            f"{item['priority_label']} | "
            f"{item['priority_score']:.1f} | "
            f"{item['timestamp']}"
        )
    print()
    print("Then say THIS")
    print(
        "“The system is runtime-agnostic — I can run it locally or in a governed execution "
        "environment like Nemo-style systems with policy enforcement.”"
    )
    print()
    print("Governed runtime example:")
    print(f"  status={results['nemo_result']['status']}")
    print(f"  task_id={results['nemo_result'].get('task_id', 'n/a')}")
    print(f"  log_entries={len(results['nemo_result'].get('logs', []))}")


def _persist_decision(result: dict[str, Any]) -> None:
    if result.get("status") != "success":
        return
    ranking = result["final_output"]["ranking"]
    save_decision(
        candidate_id=ranking["candidate_id"],
        priority_score=ranking["priority_score"],
        priority_label=ranking["priority_label"],
        explanation=ranking["explanation"],
        flags=ranking["flags"],
    )


if __name__ == "__main__":
    main()
