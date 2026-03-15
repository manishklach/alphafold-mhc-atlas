import textwrap

import pandas as pd

from src.config import PocketRegionsConfig
from src.pocket_region_analysis import build_pocket_region_outputs


def test_pocket_region_aggregation_uses_mapping_file(tmp_path) -> None:
    mapping_path = tmp_path / "regions.yaml"
    mapping_path.write_text(
        textwrap.dedent(
            """
            class_I:
              region_definitions:
                region_a:
                  residues: ["45", "66"]
            """
        ),
        encoding="utf-8",
    )
    heavy_chain_df = pd.DataFrame(
        [
            {
                "allele_name": "A",
                "variant_id": "v1",
                "mhc_residue_identifier": "45",
                "peptide_positions_contacted": "2;9",
            },
            {
                "allele_name": "A",
                "variant_id": "v1",
                "mhc_residue_identifier": "66",
                "peptide_positions_contacted": "2",
            },
        ]
    )
    contacts_df, signature_df, overlap_df = build_pocket_region_outputs(
        heavy_chain_df,
        PocketRegionsConfig(True, mapping_path, False),
    )
    assert not contacts_df.empty
    assert signature_df.iloc[0]["pocket_region"] == "region_a"
    assert overlap_df.iloc[0]["allele_count"] == 1

