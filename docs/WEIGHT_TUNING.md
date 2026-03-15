# Prioritization Weight Tuning

This repo does not hide prioritization heuristics behind a trained model. Ranking modes are config-driven and decomposable.

If someone disagrees with the current weights, the intended workflow is:

1. copy a config
2. change the prioritization weights in YAML
3. rerun analysis
4. compare ranking outputs and robustness summaries
5. discuss the differences with the evidence table in hand

## Where weights live

Weights are defined under:

- `prioritization.ranking_modes.<mode>.features`

Each feature entry has:

- `name`
- `weight`

Positive weights mean higher values increase priority.

Negative weights mean lower values increase priority.

## Example

```yaml
prioritization:
  enabled: true
  default_top_k: 10
  ranking_modes:
    disruptive_mutations:
      enabled: true
      normalize_features: true
      require_structural_support: false
      features:
        - name: "delta_total_contacts_vs_wt"
          weight: -1.0
        - name: "delta_mean_min_distance_vs_wt"
          weight: 0.75
        - name: "delta_confidence_vs_wt"
          weight: -0.5
        - name: "anchor_disruption_flag"
          weight: 1.0
```

## Practical tuning patterns

### More conservative

Use this when your team wants stronger evidence and less appetite for noisy exploratory rankings.

- increase weights on evidence-linked disruption flags
- decrease weights on softer or more coverage-sensitive features
- require structural support where appropriate

### More cross-allele focused

Use this when the main goal is discrimination across alleles rather than within-allele disruption.

- increase weights on `cross_allele_contact_divergence`
- increase weights on `cross_allele_rank_divergence`
- compare resulting panels and next actions

### More anchor-focused

Use this when anchor behavior matters more than broad contact change.

- increase `anchor_disruption_flag`
- increase anchor-position contact deltas
- review the uncertainty and structural-support status carefully

## What to compare after changing weights

- `variant_priority_table.csv`
- `priority_evidence_table.csv`
- `priority_uncertainty_table.csv`
- `ranking_stability.csv`
- review packets and next actions if decision workflows depend on the ranking

## Recommended team workflow

If there is weight disagreement inside a team:

1. keep the original config
2. create a second config with the alternative weighting logic
3. rerun both
4. compare scenario and packet outputs side by side
5. treat the differences as review material, not as proof that one weighting is biologically correct

## Example configs

- [../examples/researcher_project_template.yaml](../examples/researcher_project_template.yaml)
- [../examples/researcher_conservative_weights.yaml](../examples/researcher_conservative_weights.yaml)
- [../examples/researcher_cross_allele_weights.yaml](../examples/researcher_cross_allele_weights.yaml)

## Important caveat

Changing weights changes prioritization behavior, not biological truth.

This framework is conservative by design. Weight tuning is meant to support transparent discussion of priorities, not to smuggle in hidden modeling assumptions.
