# npj Quantum Information submission evidence snapshot

This directory freezes the machine-readable evidence used by the manuscript
"Verified quantum key search on Kalyna with spurious key occupancy".

## Provenance

- Full validation workflow: GitHub Actions run 40885242143.
- Full validation source commit:
  bcb4696e7f8235ef7d0fbba9136146da440fea4d.
- Pinned independent Kalyna reference:
  22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea.
- Independent shared-key-schedule resource audit:
  GitHub Actions run 40887441499 at commit
  e71442053da20f7473afa3a79b89b0e6dfbb9f29.

## Files

- fullround_sparse_results.csv: exhaustive historical-key restricted-domain
  results through 2^20 candidates for both Kalyna variants.
- oracle_multiplicity_summary.csv: 128-trial wrong-key occupancy summaries
  for u=12,14,16 and b=u-4,u,u+4.
- local_component_cleanup.json: S-box, modular-adder and MDS equivalence /
  cleanup checks.
- depth_summary.txt: dependency-aware logical depth results.
- resource_audit.json: independently asserted full-cipher and
  shared-key-schedule Grover non-Clifford counts.

The full trial-level occupancy records are deterministic outputs of
validation/run_oracle_multiplicity.py and can be regenerated from the source
commit and workflow. This directory is intended as a persistent minimum
dataset for manuscript review; the workflow artifacts contain the larger raw
logs and trial-level JSON while retained by GitHub Actions.
