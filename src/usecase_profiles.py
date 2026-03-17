from __future__ import annotations
from pathlib import Path
from .package_schema import DeploymentProfile
from .deployment_profiles import load_deployment_profiles

def get_default_deployment_profiles_path() -> Path:
    return Path(__file__).parent / "resources" / "data" / "deployment_profiles.yaml"

def get_deployment_profile_manager():
    path = get_default_deployment_profiles_path()
    return load_deployment_profiles(path)
