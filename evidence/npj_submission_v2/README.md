# npj Quantum Information submission evidence snapshot v2

This directory freezes the machine-readable evidence used by the revised
manuscript after adding rigorous finite-shot Grover recovery.

## Core provenance

- Full validation source:
  `bcb4696e7f8235ef7d0fbba9136146da440fea4d`
- Successful full-validation workflow:
  `40885242143`
- Pinned independent Kalyna reference:
  `22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea`
- Shared-key-schedule resource audit:
  source `e71442053da20f7473afa3a79b89b0e6dfbb9f29`,
  workflow `40887441499`
- Finite-shot source:
  `6942bb2bdac6574ed6ef30594bbffff197ea197f`
- Successful finite-shot workflow:
  `41627062982`

## Evidence files

- `fullround_sparse_results.csv`: exact historical-key marked sets through
  (2^{20}) candidates for both variants.
- `oracle_multiplicity_summary.csv`: 128-trial wrong-key occupancy summaries.
- `finite_shot_summary.csv`: exact finite-shot stopping rules and confidence
  bounds for (u=8,10,12,14,16,18,20).
- `finite_shot_u20_sample.json`: deterministic 1024-shot million-candidate
  example; target count 119, largest wrong-key count 2 at 181 iterations.
- `finite_shot_report.md`: human-readable finite-shot results.
- `local_component_cleanup.json`: reversible component checks.
- `depth_summary.txt`: dependency-aware logical depths.
- `resource_audit.json`: independently asserted complete Grover costs.

The finite-shot layer is a reduced-domain Grover recovery experiment at the
validated predicate level. It does not claim a gate-by-gate state-vector
simulation of the complete reversible Kalyna oracle. The 1024-shot reduced
iteration count is reported as a depth/noise trade-off, not as an asymptotic
or total-query improvement.
