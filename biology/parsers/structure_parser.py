from __future__ import annotations

from pathlib import Path
from typing import Any

from Bio.PDB import MMCIFParser, PDBParser
from Bio.PDB.Residue import Residue


def parse_structure(file_path: str | Path) -> dict[str, Any]:
    return parse_structure_file(file_path)


def parse_structure_file(path: str | Path) -> dict[str, Any]:
    structure_path = Path(path)
    if not structure_path.exists():
        raise FileNotFoundError(f"Structure file not found: {structure_path}")

    structure = _load_structure(structure_path)

    residues: list[dict[str, Any]] = []
    coordinates: list[dict[str, Any]] = []
    chains: set[str] = set()
    confidence_values: list[float] = []

    for model in structure:
        for chain in model:
            chain_id = str(chain.id).strip() or "_"
            chains.add(chain_id)
            for residue in chain:
                if not _is_standard_residue(residue):
                    continue
                residue_record = _extract_residue_record(chain_id, residue)
                residues.append(residue_record)
                coordinate_record = _extract_ca_coordinate(chain_id, residue)
                if coordinate_record is not None:
                    coordinates.append(coordinate_record)
                confidence_value = _extract_confidence_value(residue)
                if confidence_value is not None:
                    confidence_values.append(confidence_value)

    return {
        "residues": residues,
        "chains": sorted(chains),
        "coordinates": coordinates,
        "confidence_summary": _build_confidence_summary(confidence_values),
    }


def _load_structure(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".cif":
        parser = MMCIFParser(QUIET=True)
    elif suffix == ".pdb":
        parser = PDBParser(QUIET=True)
    else:
        raise ValueError(f"Unsupported structure format: {path.suffix}")
    try:
        return parser.get_structure(path.stem, str(path))
    except Exception as exc:  # pragma: no cover - defensive wrapping
        raise ValueError(f"Failed to parse structure file: {path}") from exc


def _is_standard_residue(residue: Residue) -> bool:
    hetfield = residue.id[0]
    return hetfield == " "


def _extract_residue_record(chain_id: str, residue: Residue) -> dict[str, Any]:
    residue_number = int(residue.id[1])
    insertion_code = str(residue.id[2]).strip()
    residue_id = f"{chain_id}:{residue_number}{insertion_code}" if insertion_code else f"{chain_id}:{residue_number}"
    return {
        "residue_id": residue_id,
        "chain_id": chain_id,
        "residue_name": residue.get_resname().strip(),
        "residue_number": residue_number,
    }


def _extract_ca_coordinate(chain_id: str, residue: Residue) -> dict[str, Any] | None:
    if not residue.has_id("CA"):
        return None
    atom = residue["CA"]
    x, y, z = atom.coord.tolist()
    residue_number = int(residue.id[1])
    insertion_code = str(residue.id[2]).strip()
    residue_id = f"{chain_id}:{residue_number}{insertion_code}" if insertion_code else f"{chain_id}:{residue_number}"
    return {
        "residue_id": residue_id,
        "chain_id": chain_id,
        "residue_name": residue.get_resname().strip(),
        "residue_number": residue_number,
        "x": round(float(x), 3),
        "y": round(float(y), 3),
        "z": round(float(z), 3),
    }


def _build_confidence_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "avg": None,
            "min": None,
            "max": None,
        }
    return {
        "avg": round(sum(values) / len(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def _extract_confidence_value(residue: Residue) -> float | None:
    values = []
    for atom in residue.get_atoms():
        bfactor = atom.get_bfactor()
        if bfactor is not None:
            values.append(float(bfactor))
    if not values:
        return None
    return sum(values) / len(values)
