import pandas as pd

from src.case_study import run_case_studies
from src.config import CaseStudySpec


def test_case_study_filters_rows(tmp_path) -> None:
    summary_df = pd.DataFrame(
        [
            {
                "variant_id": "A__WT",
                "allele_name": "A",
                "wildtype_peptide": "GILGFVFTL",
                "mutated_position": pd.NA,
                "mut_residue": pd.NA,
            },
            {
                "variant_id": "B__p2A",
                "allele_name": "B",
                "wildtype_peptide": "GILGFVFTL",
                "mutated_position": 2,
                "mut_residue": "A",
            },
        ]
    )
    result = run_case_studies(
        [
            CaseStudySpec(
                case_id="case1",
                description="desc",
                alleles=["B"],
                peptides=["GILGFVFTL"],
                mutation_positions=[2],
                substitutions=["A"],
                variants=[],
            )
        ],
        tmp_path,
        summary_df,
        summary_df,
        summary_df,
        pd.DataFrame(),
    )
    assert result[0]["num_variants"] == 1
    assert (tmp_path / "case1" / "filtered_variants.csv").exists()

