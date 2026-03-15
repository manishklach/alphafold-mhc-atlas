from src.mutation_generator import generate_single_mutants


def test_generate_single_mutants_preserves_wildtype_and_skips_identity_mutations() -> None:
    variants = generate_single_mutants(
        allele_name="HLA-A*02:01",
        reference_peptide="GILGFVFTL",
        mutation_positions=[2, 5],
        allowed_amino_acids=["A", "I", "V"],
    )

    variant_ids = [variant.local_variant_id for variant in variants]
    assert variant_ids[0] == "WT"
    assert "pos2_ItoA" in variant_ids
    assert "pos5_FtoA" in variant_ids
    assert "pos2_ItoI" not in variant_ids
    assert variants[0].variant_id.startswith("HLA_A_02_01__pep_")
    assert len(variants) == 6
