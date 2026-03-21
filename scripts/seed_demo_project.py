from __future__ import annotations

from pathlib import Path
from pprint import pprint
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from biology.comparisons.comparison_engine import compare_structures
from biology.parsers.structure_parser import parse_structure_file
from core.reporting.report_generator import generate_report
from core.scoring.prioritization import rank_candidates


DEMO_STRUCTURES_DIR = REPO_ROOT / "data" / "demo_structures"
DEFAULT_REPORT_PATH = REPO_ROOT / "storage" / "reports" / "demo_pipeline_report.md"


def run_demo_pipeline() -> dict[str, Any]:
    structure_paths = {
        "wt": DEMO_STRUCTURES_DIR / "wt_example.pdb",
        "mutant_a": DEMO_STRUCTURES_DIR / "mutant_example_a.pdb",
        "mutant_b": DEMO_STRUCTURES_DIR / "mutant_example_b.pdb",
    }

    parsed_structures = {
        name: parse_structure_file(path)
        for name, path in structure_paths.items()
    }

    comparisons = []
    for candidate_id in ("mutant_a", "mutant_b"):
        comparison = compare_structures(
            wt_structure=parsed_structures["wt"],
            mutant_structure=parsed_structures[candidate_id],
        )
        comparison["candidate_id"] = candidate_id
        comparison["confidence_summary"] = parsed_structures[candidate_id]["confidence_summary"]
        comparisons.append(comparison)

    ranked_candidates = rank_candidates(comparisons)
    report_path = generate_report(ranked_candidates, output_path=DEFAULT_REPORT_PATH)

    return {
        "structure_paths": {name: str(path) for name, path in structure_paths.items()},
        "parsed_structures": parsed_structures,
        "comparisons": comparisons,
        "ranked_candidates": ranked_candidates,
        "report_path": str(report_path),
    }


def main() -> None:
    results = run_demo_pipeline()
    print("MHC Atlas OS demo pipeline completed.")
    print()
    print("Structures:")
    for name, path in results["structure_paths"].items():
        print(f"  {name}: {path}")
    print()
    print("Ranked candidates:")
    pprint(results["ranked_candidates"])
    print()
    print(f"Report written to: {results['report_path']}")


if __name__ == "__main__":
    main()
