# npj submission v3 evidence

This directory contains the minimum machine-readable evidence needed to audit
the manuscript without relying on expiring GitHub Actions artifacts.

## Files

- `fullround_sparse_results.csv`:
  historical-key restricted-domain scans through (2^{20}) candidates.
- `finite_shot_summary.csv`:
  exact finite-shot stopping rules and 99% threshold-decoder bounds.
- `finite_shot_u20_sample.json`:
  deterministic 1024-shot million-candidate example (119 true-key counts,
  largest wrong-key count 2).
- `oracle_multiplicity_summary.csv`:
  128-trial wrong-key occupancy summaries for the many-key, critical and
  near-unique regimes.
- `local_component_cleanup.json`:
  S-box, modular-adder and MDS equivalence/cleanup checks.
- `exact_resource_audit.json`:
  exact functional full-cipher and complete-iteration resource totals.
- `full_oracle_certificate_summary.json`:
  independent-reference regression, clean phase-oracle widths/depths, cleanup
  and gate hashes.
- `finite_shot_report.md`:
  human-readable finite-shot interpretation.

## Reference and CI provenance

Pinned independent Kalyna reference:
`22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea`.

Key passing workflows:
- full validation run `41643474878`;
- exact resource audit `41643474832`;
- clean-oracle/depth certificate `41645374938`;
- finite-shot recovery `41627062982`.

See the repository root `SUBMISSION_SNAPSHOT.md` for the complete scope and
interpretation.
