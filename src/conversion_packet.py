from __future__ import annotations
import csv
import json
from pathlib import Path
from typing import Any
from .package_schema import ConversionArtifact

def generate_conversion_packet(
    artifact: ConversionArtifact,
    output_dir: Path
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # conversion_summary.md
    summary_path = output_dir / "conversion_summary.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# Conversion Summary: {artifact.pilot_id}\n\n")
        f.write(f"**Readiness Score:** {artifact.readiness_score:.2f}/1.0\n\n")
        f.write("## Workflows Used\n")
        for w in artifact.workflows_tried:
            if w: f.write(f"- {w}\n")
        f.write("\n## Useful Artifacts\n")
        for a in artifact.useful_artifacts:
            if a: f.write(f"- {a}\n")
        f.write("\n## Next Pilot Recommendations\n")
        for n in artifact.next_steps:
            if n: f.write(f"- {n}\n")
            
    # workflows_used.csv
    workflows_path = output_dir / "workflows_used.csv"
    with open(workflows_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["workflow_name"])
        for w in artifact.workflows_tried:
            if w: writer.writerow([w])
            
    # useful_artifacts.csv
    useful_path = output_dir / "useful_artifacts.csv"
    with open(useful_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["artifact_name"])
        for a in artifact.useful_artifacts:
            if a: writer.writerow([a])
            
    # friction_artifacts.csv
    friction_path = output_dir / "friction_artifacts.csv"
    with open(friction_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["friction_point"])
        for fp in artifact.persisting_friction:
            if fp: writer.writerow([fp])
            
    # adoption_readiness_summary.csv
    readiness_path = output_dir / "adoption_readiness_summary.csv"
    with open(readiness_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["pilot_id", "readiness_score", "num_workflows", "num_useful_artifacts", "num_friction_points"])
        writer.writerow([
            artifact.pilot_id, 
            artifact.readiness_score, 
            len([w for w in artifact.workflows_tried if w]),
            len([a for a in artifact.useful_artifacts if a]),
            len([fp for fp in artifact.persisting_friction if fp])
        ])

    # caveats.md
    caveats_path = output_dir / "caveats.md"
    with open(caveats_path, "w", encoding="utf-8") as f:
        f.write("# Conversion Caveats\n\n")
        f.write("- Readiness score is a qualitative proxy based on pilot feedback.\n")
        f.write("- Success in pilot does not guarantee clinical or commercial success.\n")
        f.write("- Friction points must be addressed before broad rollout.\n")
