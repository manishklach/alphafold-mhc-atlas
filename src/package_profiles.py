from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any
from .package_schema import PackageProfile

def load_package_profiles(profiles_path: Path) -> list[PackageProfile]:
    if not profiles_path.exists():
        return []
    with open(profiles_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        return []
    profiles = []
    for p in data:
        profiles.append(PackageProfile(
            name=p['name'],
            description=p['description'],
            intended_user=p['intended_user'],
            included_workflows=p.get('included_workflows', []),
            included_roles=p.get('included_roles', []),
            included_packets=p.get('included_packets', []),
            included_playbooks=p.get('included_playbooks', []),
            included_eval_artifacts=p.get('included_eval_artifacts', []),
            setup_complexity=p.get('setup_complexity', 'Moderate'),
            scope_limitations=p.get('scope_limitations', []),
            success_criteria=p.get('success_criteria', [])
        ))
    return profiles

def get_package_profile(profiles: list[PackageProfile], name: str) -> PackageProfile | None:
    for p in profiles:
        if p.name == name:
            return p
    return None
