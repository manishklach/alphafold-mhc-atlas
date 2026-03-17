from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any
from .package_schema import ProductSurface

def load_product_surfaces(path: Path) -> list[ProductSurface]:
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        return []
    surfaces = []
    for s in data:
        surfaces.append(ProductSurface(
            profile_name=s['profile_name'],
            core_workflows=s.get('core_workflows', []),
            emphasized_outputs=s.get('emphasized_outputs', []),
            primary_docs=s.get('primary_docs', []),
            de_emphasized_features=s.get('de_emphasized_features', [])
        ))
    return surfaces

def get_product_surface(surfaces: list[ProductSurface], profile_name: str) -> ProductSurface | None:
    for s in surfaces:
        if s.profile_name == profile_name:
            return s
    return None

def get_default_product_surface_path() -> Path:
    return Path(__file__).parent / \"resources\" / \"data\" / \"product_surfaces.yaml\"

def get_product_surface_manager():
    path = get_default_product_surface_path()
    return load_product_surfaces(path)
