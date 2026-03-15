from __future__ import annotations

# Backward-compatible public config surface.
# Schema types now live in config_schema and parsing/validation in config_loader.
from .config_loader import get_peptides_for_allele, load_config
from .config_schema import *
