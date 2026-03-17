from __future__ import annotations
from pathlib import Path
from .package_schema import PackageProfile
from .package_profiles import load_package_profiles

def get_default_package_profiles_path() -> Path:
    return Path(__file__).parent / "resources" / "data" / "package_profiles.yaml"

def get_pilot_package_manager():
    path = get_default_package_profiles_path()
    return load_package_profiles(path)
