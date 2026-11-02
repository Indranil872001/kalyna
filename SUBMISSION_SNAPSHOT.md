# npj Quantum Information submission snapshot

This branch is the frozen code/data snapshot supporting the manuscript
"Full round quantum key search and spurious key occupancy in Kalyna".

## Immutable provenance used by the manuscript

- Full validation source commit:
  `bcb4696e7f8235ef7d0fbba9136146da440fea4d`
- Successful full-validation GitHub Actions run:
  `40885242143`
- Pinned independent Kalyna reference:
  `22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea`
- Shared-key-schedule resource-model source:
  `0b9f227502d1a27f26119942d3929ff2ee21d7e7`
- Independent resource-audit source:
  `e71442053da20f7473afa3a79b89b0e6dfbb9f29`
- Successful resource-audit run:
  `40887441499`
- Minimum machine-readable evidence:
  `evidence/npj_submission_v1/`

The validation scripts on this branch include the spread-subspace historical-key
scanner, the full-round wrong-key occupancy experiment, local reversible
component checks, corrected logical-depth scripts, and the optimized
shared-key-schedule Grover resource calculation.

## Evidence boundary

The full-round experiments exhaustively evaluate the standardized Kalyna
predicate in tractable master-key subspaces. They do not state-vector simulate
the complete reversible gate network. Local S-box, modular-adder and MDS checks
support component-level reversible correctness; physical routing and
fault-tolerant architecture overhead are outside the logical model.
