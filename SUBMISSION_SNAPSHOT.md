# npj Quantum Information submission snapshot v2

This branch is the working source for the revised manuscript
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
- Finite-shot Grover source:
  `6942bb2bdac6574ed6ef30594bbffff197ea197f`
- Successful finite-shot workflow run:
  `41627062982`
- Minimum machine-readable evidence:
  `evidence/npj_submission_v2/`

## Added finite-shot layer

The validated one-marked historical-key predicates are reused in an exact
1024-shot Grover recovery experiment. For a 100-count detection threshold,
the code computes both the expected-count stopping rule used in the recent
Mini-AES study and a stronger 99% recovery lower bound that union-bounds
threshold collisions from every wrong key.

At the largest validated search domain, (u=20), the first Grover maximum is
804 iterations. The 99%-confidence finite-shot decoder requires 181 iterations
per circuit. In the archived deterministic sample the historical key appears
119 times and the largest wrong-key count is 2.

This is explicitly a depth/noise trade-off: 1024 shots require 1024 independent
circuit executions and therefore do not reduce Grover's total query complexity.

## Evidence boundary

The full-round experiments exhaustively evaluate the standardized Kalyna
predicate in tractable master-key subspaces. They do not state-vector simulate
the complete reversible gate network. Local S-box, modular-adder and MDS checks
support component-level reversible correctness; physical routing and
fault-tolerant architecture overhead are outside the logical model.
