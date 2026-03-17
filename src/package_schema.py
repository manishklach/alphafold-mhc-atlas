from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class PackageProfile:
    name: str
    description: str
    intended_user: str
    included_workflows: list[str]
    included_roles: list[str]
    included_packets: list[str]
    included_playbooks: list[str]
    included_eval_artifacts: list[str]
    setup_complexity: str
    scope_limitations: list[str]
    success_criteria: list[str]

@dataclass(frozen=True)
class WorkflowBundle:
    name: str
    description: str
    objective: str
    commands: list[str]
    expected_inputs: list[str]
    expected_outputs: list[str]
    caveats: list[str]
    recommended_roles: list[str]
    eval_questions: list[str]

@dataclass(frozen=True)
class DeploymentProfile:
    name: str
    description: str
    target_team: str
    likely_workflows: list[str]
    safe_to_ignore: list[str]
    key_artifacts: list[str]
    setup_path: str
    success_criteria: list[str]

@dataclass(frozen=True)
class ProductSurface:
    profile_name: str
    core_workflows: list[str]
    emphasized_outputs: list[str]
    primary_docs: list[str]
    de_emphasized_features: list[str]

@dataclass(frozen=True)
class ConversionArtifact:
    pilot_id: str
    workflows_tried: list[str]
    useful_artifacts: list[str]
    persisting_friction: list[str]
    next_steps: list[str]
    readiness_score: float
