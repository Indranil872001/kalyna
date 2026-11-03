# npj Quantum Information submission snapshot v3

This snapshot supports the manuscript
"Full round quantum key search and spurious key occupancy in Kalyna".

## Canonical implementation

- Exact functional reversible compiler:
  `src/kalyna_oracle/compiler.py`
- Full clean-oracle certificate:
  `validation/run_full_oracle_certificate.py`
- One-command reproduction:
  `bash scripts/reproduce_oracle_certificate.sh`
- Frozen machine-readable evidence:
  `evidence/npj_submission_v3/`

## Independent reference

The workflows pin the public Kalyna reference implementation at:

`22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea`

## Passing evidence used by the manuscript

- Cleaned-repository full validation:
  - source `32ebf6170a28359bb82ea9455750d53e796dc0ff`
  - GitHub Actions run `41643474878`
  - local S-box/adder/MDS cleanup, full-round restricted-key scans through
    (2^{20}), 128-trial occupancy experiment, exact resource regeneration
    and legacy structural-depth diagnostics all pass.
- Exact functional resource audit:
  - source `32ebf6170a28359bb82ea9455750d53e796dc0ff`
  - GitHub Actions run `41643474832`
  - asserts full-cipher counts
    ((1550,504548,609232)) and ((2047,665604,803920)) in
    ((X,\mathrm{CNOT},\mathrm{CCNOT})).
- Full clean-oracle certificate with exact depth lock:
  - source `16017141cf37eae2ab423c60e37ddd9661e48225`
  - GitHub Actions run `41645374938`
  - official KAT plus ten seeded random cases per variant;
  - every round key and ciphertext checked against the pinned C reference;
  - historical key phase-marked and four perturbed wrong keys not marked;
  - exact compute-mark-inverse restoration of every work wire;
  - complete phase-oracle dependency depths 2787759 and 4846565.
- Finite-shot Grover validation:
  - source `6942bb2bdac6574ed6ef30594bbffff197ea197f`
  - GitHub Actions run `41627062982`
  - 1024-shot threshold decoder, including the archived (u=20) example
    with historical-key count 119 and largest wrong-key count 2.

## Certified logical resources

Kalyna-128/128:
- full cipher: 1550 X, 504548 CNOT, 609232 CCNOT;
- exact forward cipher width: 5126 qubits;
- historical-key phase-oracle width: 6781 qubits;
- complete phase-oracle dependency depth: 2787759;
- complete Grover iteration: 1703126 CCNOT-equivalent;
- seven-T template: 11921882 logical T gates.

Kalyna-128/256:
- full cipher: 2047 X, 665604 CNOT, 803920 CCNOT;
- exact forward cipher width: 6790 qubits;
- historical-key phase-oracle width: 11005 qubits;
- complete phase-oracle dependency depth: 4846565;
- complete Grover iteration: 2963222 CCNOT-equivalent;
- seven-T template: 20742554 logical T gates.

## Important scope boundary

The full-round restricted-key Grover experiments determine the exact marked set
with the complete classical Kalyna reference cipher and evolve the Grover
amplitudes exactly in the tractable search domain. They are not dense
state-vector simulations of the 6781- or 11005-qubit compiled phase oracles.

The new compiler certificate addresses the separate gate-level question:
it compiles the exact functional Kalyna mapping, independently verifies round
keys/ciphertexts, phase marks the historical key, and proves coherent cleanup
because the uncompute is the exact reverse of the emitted reversible tape.

The compiler uses an out-of-place ANF S-box and therefore retains substantial
reversible history. Its reported widths and depths describe this concrete
certified realization; they are not global lower bounds or optimality claims.

## Legacy code

Historical ProjectQ estimators and component experiments are archived under
`legacy/`. They are retained for provenance only and are not the canonical
submission implementation.
