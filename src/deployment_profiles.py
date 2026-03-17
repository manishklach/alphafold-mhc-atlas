from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any
from .package_schema import DeploymentProfile

def load_deployment_profiles(profiles_path: Path) -> list[DeploymentProfile]:
    if not profiles_path.exists():
        return []
    with open(profiles_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        return []
    profiles = []
    for p in data:
        profiles.append(DeploymentProfile(
            name=p['name'],
            description=p['description'],
            target_team=p['target_team'],
            likely_workflows=p.get('likely_workflows', []),
            safe_to_ignore=p.get('safe_to_ignore', []),
            key_artifacts=p.get('key_artifacts', []),
            setup_path=p.get('setup_path', ''),
            success_criteria=p.get('success_criteria', [])
        ))
    return profiles

def get_deployment_profile(profiles: list[DeploymentProfile], name: str) -> DeploymentProfile | None:
    for p in profiles:
        if p.name == name:
            return p
    return None
