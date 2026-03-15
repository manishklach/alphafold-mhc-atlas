from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from Bio.PDB import MMCIFParser, PDBParser
from Bio.PDB.Atom import Atom
from Bio.PDB.Chain import Chain
from Bio.PDB.Residue import Residue
import numpy as np

from .input_builder import VariantInputRecord


THREE_TO_ONE = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


@dataclass(frozen=True)
class StructureHandle:
    structure_path: Path
    format: str


@dataclass(frozen=True)
class ParsedResidue:
    chain_id: str
    residue_name: str
    residue_number: int
    insertion_code: str
    sequence_index: int
    sequence_code: str
    atom_names: tuple[str, ...]
    centroid: tuple[float, float, float] | None
    ca_coord: tuple[float, float, float] | None
    cb_coord: tuple[float, float, float] | None
    all_atom_coords: tuple[tuple[float, float, float], ...]

    @property
    def residue_identifier(self) -> str:
        insertion = self.insertion_code.strip() or ""
        return f"{self.chain_id}:{self.residue_name}:{self.residue_number}{insertion}"


@dataclass(frozen=True)
class ParsedChain:
    chain_id: str
    residues: tuple[ParsedResidue, ...]
    sequence: str

    @property
    def length(self) -> int:
        return len(self.residues)


@dataclass(frozen=True)
class ParsedStructure:
    structure_path: Path
    structure_format: str
    chains: tuple[ParsedChain, ...]


@dataclass(frozen=True)
class ChainRoleMap:
    variant_id: str
    structure_path: str | None
    structure_format: str | None
    heavy_chain_chain_id: str | None
    beta2m_chain_id: str | None
    peptide_chain_id: str | None
    heavy_chain_length: int | None
    beta2m_length: int | None
    peptide_length: int | None
    chain_mapping_confidence: str
    chain_mapping_notes: str | None

    def to_row(self) -> dict[str, object]:
        return {
            "variant_id": self.variant_id,
            "structure_path": self.structure_path,
            "structure_format": self.structure_format,
            "heavy_chain_chain_id": self.heavy_chain_chain_id,
            "beta2m_chain_id": self.beta2m_chain_id,
            "peptide_chain_id": self.peptide_chain_id,
            "heavy_chain_length": self.heavy_chain_length,
            "beta2m_length": self.beta2m_length,
            "peptide_length": self.peptide_length,
            "chain_mapping_confidence": self.chain_mapping_confidence,
            "chain_mapping_notes": self.chain_mapping_notes,
        }


def identify_structure_file(structure_path: str | Path | None) -> StructureHandle | None:
    if not structure_path:
        return None
    path = Path(structure_path)
    suffix = path.suffix.lower()
    if suffix not in {".pdb", ".cif", ".mmcif"}:
        return None
    structure_format = "mmcif" if suffix in {".cif", ".mmcif"} else "pdb"
    return StructureHandle(structure_path=path, format=structure_format)


def load_structure(structure_path: str | Path | None) -> ParsedStructure | None:
    handle = identify_structure_file(structure_path)
    if not handle or not handle.structure_path.exists():
        return None

    parser = MMCIFParser(QUIET=True) if handle.format == "mmcif" else PDBParser(QUIET=True)
    structure = parser.get_structure(handle.structure_path.stem, str(handle.structure_path))

    chains: list[ParsedChain] = []
    for model in structure:
        for chain in model:
            parsed_chain = _parse_chain(chain)
            if parsed_chain and parsed_chain.residues:
                chains.append(parsed_chain)
        break
    return ParsedStructure(
        structure_path=handle.structure_path,
        structure_format=handle.format,
        chains=tuple(chains),
    )


def map_chain_roles(
    variant_id: str,
    parsed_structure: ParsedStructure | None,
    variant_input: VariantInputRecord | None,
    require_confident_mapping: bool,
) -> ChainRoleMap:
    if not parsed_structure:
        return ChainRoleMap(
            variant_id=variant_id,
            structure_path=None,
            structure_format=None,
            heavy_chain_chain_id=None,
            beta2m_chain_id=None,
            peptide_chain_id=None,
            heavy_chain_length=None,
            beta2m_length=None,
            peptide_length=None,
            chain_mapping_confidence="unavailable",
            chain_mapping_notes="No structure file available.",
        )
    if not variant_input or not variant_input.chain_records:
        return ChainRoleMap(
            variant_id=variant_id,
            structure_path=str(parsed_structure.structure_path),
            structure_format=parsed_structure.structure_format,
            heavy_chain_chain_id=None,
            beta2m_chain_id=None,
            peptide_chain_id=None,
            heavy_chain_length=None,
            beta2m_length=None,
            peptide_length=None,
            chain_mapping_confidence="unavailable",
            chain_mapping_notes="No chain manifest context available for mapping.",
        )

    expected = {chain.chain_role: chain.sequence for chain in variant_input.chain_records}
    assignments: dict[str, tuple[ParsedChain, float]] = {}
    notes: list[str] = []

    available_chains = list(parsed_structure.chains)
    for role in ("mhc_heavy_chain", "beta2m", "peptide"):
        best_chain, best_score, ambiguous = _match_chain_for_role(available_chains, expected.get(role))
        if best_chain is None:
            notes.append(f"No chain matched role '{role}'.")
            continue
        assignments[role] = (best_chain, best_score)
        available_chains = [chain for chain in available_chains if chain.chain_id != best_chain.chain_id]
        if ambiguous:
            notes.append(f"Role '{role}' had ambiguous sequence matches.")

    confidence = _mapping_confidence(assignments, notes, require_confident_mapping)
    if require_confident_mapping and confidence not in {"high", "medium"}:
        notes.append("Chain mapping did not meet the configured confidence requirement.")

    return ChainRoleMap(
        variant_id=variant_id,
        structure_path=str(parsed_structure.structure_path),
        structure_format=parsed_structure.structure_format,
        heavy_chain_chain_id=assignments.get("mhc_heavy_chain", (None, 0.0))[0].chain_id
        if assignments.get("mhc_heavy_chain")
        else None,
        beta2m_chain_id=assignments.get("beta2m", (None, 0.0))[0].chain_id if assignments.get("beta2m") else None,
        peptide_chain_id=assignments.get("peptide", (None, 0.0))[0].chain_id if assignments.get("peptide") else None,
        heavy_chain_length=assignments.get("mhc_heavy_chain", (None, 0.0))[0].length
        if assignments.get("mhc_heavy_chain")
        else None,
        beta2m_length=assignments.get("beta2m", (None, 0.0))[0].length if assignments.get("beta2m") else None,
        peptide_length=assignments.get("peptide", (None, 0.0))[0].length if assignments.get("peptide") else None,
        chain_mapping_confidence=confidence,
        chain_mapping_notes="; ".join(notes) if notes else None,
    )


def get_chain_by_role(
    parsed_structure: ParsedStructure,
    chain_map: ChainRoleMap,
    role: str,
) -> ParsedChain | None:
    role_to_chain_id = {
        "mhc_heavy_chain": chain_map.heavy_chain_chain_id,
        "beta2m": chain_map.beta2m_chain_id,
        "peptide": chain_map.peptide_chain_id,
    }
    chain_id = role_to_chain_id.get(role)
    if not chain_id:
        return None
    for chain in parsed_structure.chains:
        if chain.chain_id == chain_id:
            return chain
    return None


def residue_distance(
    residue_a: ParsedResidue,
    residue_b: ParsedResidue,
    use_all_atom_contacts: bool,
    fallback_to_ca_distance: bool,
) -> float | None:
    coords_a = residue_coordinates(residue_a, use_all_atom_contacts, fallback_to_ca_distance)
    coords_b = residue_coordinates(residue_b, use_all_atom_contacts, fallback_to_ca_distance)
    if not coords_a or not coords_b:
        return None
    array_a = np.asarray(coords_a, dtype=float)
    array_b = np.asarray(coords_b, dtype=float)
    deltas = array_a[:, None, :] - array_b[None, :, :]
    distances = np.sqrt(np.sum(deltas * deltas, axis=2))
    return float(np.min(distances))


def residue_coordinates(
    residue: ParsedResidue,
    use_all_atom_contacts: bool,
    fallback_to_ca_distance: bool,
) -> list[tuple[float, float, float]]:
    if use_all_atom_contacts and residue.all_atom_coords:
        return list(residue.all_atom_coords)
    preferred = [residue.cb_coord, residue.ca_coord] if fallback_to_ca_distance else [residue.cb_coord]
    for coord in preferred:
        if coord is not None:
            return [coord]
    if not use_all_atom_contacts and residue.all_atom_coords:
        return [residue.all_atom_coords[0]]
    return []


def peptide_centroid(chain: ParsedChain) -> tuple[float, float, float] | None:
    coords = [residue.centroid for residue in chain.residues if residue.centroid is not None]
    if not coords:
        return None
    array = np.asarray(coords, dtype=float)
    return tuple(np.mean(array, axis=0))


def backbone_rmsd(chain_a: ParsedChain, chain_b: ParsedChain) -> float | None:
    if chain_a.length != chain_b.length or chain_a.length == 0:
        return None
    coords_a: list[np.ndarray] = []
    coords_b: list[np.ndarray] = []
    for residue_a, residue_b in zip(chain_a.residues, chain_b.residues):
        if residue_a.ca_coord is None or residue_b.ca_coord is None:
            return None
        coords_a.append(np.asarray(residue_a.ca_coord, dtype=float))
        coords_b.append(np.asarray(residue_b.ca_coord, dtype=float))
    deltas = np.stack(coords_a) - np.stack(coords_b)
    return float(np.sqrt(np.mean(np.sum(deltas * deltas, axis=1))))


def load_structure_stub(structure_path: str | Path | None) -> StructureHandle | None:
    return identify_structure_file(structure_path)


def _parse_chain(chain: Chain) -> ParsedChain | None:
    residues: list[ParsedResidue] = []
    sequence_codes: list[str] = []
    sequence_index = 0
    for residue in chain:
        if not _is_protein_residue(residue):
            continue
        residue_name = residue.get_resname().upper()
        sequence_code = THREE_TO_ONE.get(residue_name)
        if not sequence_code:
            continue
        atom_coords = _collect_atom_coords(residue)
        parsed_residue = ParsedResidue(
            chain_id=str(chain.id),
            residue_name=residue_name,
            residue_number=int(residue.id[1]),
            insertion_code=str(residue.id[2]).strip(),
            sequence_index=sequence_index,
            sequence_code=sequence_code,
            atom_names=tuple(atom.get_name() for atom in residue if atom.element != "H"),
            centroid=_mean_coord(atom_coords),
            ca_coord=_atom_coord(residue, "CA"),
            cb_coord=_atom_coord(residue, "CB"),
            all_atom_coords=tuple(atom_coords),
        )
        residues.append(parsed_residue)
        sequence_codes.append(sequence_code)
        sequence_index += 1
    if not residues:
        return None
    return ParsedChain(chain_id=str(chain.id), residues=tuple(residues), sequence="".join(sequence_codes))


def _collect_atom_coords(residue: Residue) -> list[tuple[float, float, float]]:
    coords: list[tuple[float, float, float]] = []
    for atom in residue:
        if _is_hydrogen(atom):
            continue
        vector = atom.get_coord()
        coords.append((float(vector[0]), float(vector[1]), float(vector[2])))
    return coords


def _atom_coord(residue: Residue, atom_name: str) -> tuple[float, float, float] | None:
    if atom_name not in residue:
        return None
    vector = residue[atom_name].get_coord()
    return float(vector[0]), float(vector[1]), float(vector[2])


def _mean_coord(coords: Iterable[tuple[float, float, float]]) -> tuple[float, float, float] | None:
    coords_list = list(coords)
    if not coords_list:
        return None
    array = np.asarray(coords_list, dtype=float)
    mean = np.mean(array, axis=0)
    return float(mean[0]), float(mean[1]), float(mean[2])


def _is_protein_residue(residue: Residue) -> bool:
    return residue.id[0] == " " and residue.get_resname().upper() in THREE_TO_ONE


def _is_hydrogen(atom: Atom) -> bool:
    element = getattr(atom, "element", "").strip().upper()
    return element == "H" or atom.get_name().startswith("H")


def _match_chain_for_role(
    parsed_chains: list[ParsedChain],
    expected_sequence: str | None,
) -> tuple[ParsedChain | None, float, bool]:
    if not expected_sequence:
        return None, 0.0, False
    scored: list[tuple[ParsedChain, float]] = []
    for chain in parsed_chains:
        score = _sequence_match_score(chain.sequence, expected_sequence)
        scored.append((chain, score))
    if not scored:
        return None, 0.0, False
    scored.sort(key=lambda item: item[1], reverse=True)
    best_chain, best_score = scored[0]
    ambiguous = len(scored) > 1 and abs(scored[0][1] - scored[1][1]) < 0.05
    if best_score < 0.5:
        return None, best_score, ambiguous
    return best_chain, best_score, ambiguous


def _sequence_match_score(observed: str, expected: str) -> float:
    if not observed or not expected:
        return 0.0
    if observed == expected:
        return 1.0
    max_len = max(len(observed), len(expected))
    min_len = min(len(observed), len(expected))
    matches = sum(1 for a, b in zip(observed, expected) if a == b)
    length_penalty = min_len / max_len
    return (matches / max_len) * length_penalty


def _mapping_confidence(
    assignments: dict[str, tuple[ParsedChain, float]],
    notes: list[str],
    require_confident_mapping: bool,
) -> str:
    if len(assignments) != 3:
        return "unresolved"
    min_score = min(score for _, score in assignments.values())
    if notes:
        return "medium" if min_score >= 0.9 and not require_confident_mapping else "low"
    if min_score >= 0.99:
        return "high"
    if min_score >= 0.85:
        return "medium"
    return "low"
