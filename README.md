# Verified quantum key search on Kalyna

Reproducibility repository for the npj Quantum Information manuscript on
full-round known-plaintext Grover key search for Kalyna-128/128 and
Kalyna-128/256.

## Start here

There is **one canonical reversible implementation** for the submission:

- `src/kalyna_oracle/compiler.py`
  - exact functional reversible compiler for the Kalyna key schedule and
    encryption;
  - includes the K_t specification constant, tmv constants, selected/rotated
    master-key-word copies and odd-key rotation;
  - emits a concrete X/CNOT/CCNOT gate tape;
  - retains out-of-place S-box history explicitly and cleans it globally by
    exact forward-mark-inverse uncomputation.

The main certification driver is:

- `validation/run_full_oracle_certificate.py`

The easiest reproduction path is:

```bash
bash scripts/reproduce_oracle_certificate.sh
```

It pins the independent reference implementation, compiles the reference
harness, runs the exact compiler, compares every round key and ciphertext,
checks phase marking, checks four perturbed wrong keys per variant, measures
the concrete logical depth/width, and verifies exact work-register restoration.

## Submission evidence

The reviewer-facing machine-readable snapshot is:

- `evidence/npj_submission_v3/`

It contains the restricted-key search results, finite-shot tables, occupancy
statistics, local component checks, exact resource audit and clean-oracle
certificate summary.

The core passing CI runs used by the submission are documented in
`SUBMISSION_SNAPSHOT.md`.

## Other submission experiments

- `validation/run_fullround_sparse.py` - exhaustive full-round restricted-key
  historical-key scans and exact Grover amplitudes.
- `validation/run_finite_shot_recovery.py` - 1024-shot recovery and rigorous
  threshold-confidence bounds.
- `validation/run_oracle_multiplicity.py` - full-round wrong-key occupancy
  experiments.
- `validation/check_local_cleanup.py` - exhaustive/local component cleanup
  and equivalence checks.
- `validation/corrected_resource_counts.py` - exact functional resource
  accounting and complete Grover non-Clifford totals.

GitHub Actions workflows under `.github/workflows/` reproduce these checks.

## What is in legacy/

The former root-level files
`kalyna_key-128`, `kalyna_key_256`, `kalyna_key_schedule_128`,
`addition_modulo2^64` and `kalyna_mixcolumn` came from different stages of
the research. They are preserved under `legacy/` so they cannot be mistaken
for the submission implementation.

In particular:

- the old 256-bit file is a **structural depth estimator**, not the canonical
  functional key schedule;
- the old 128-bit schedule estimator contains pre-correction resource
  conventions and must not be used for manuscript numbers.

See `legacy/README.md` for details.

## Evidence boundary

The compiler certificate establishes a clean **logical** phase oracle. It does
not claim present-day hardware execution, surface-code overhead, routing,
magic-state-factory cost or architecture-specific latency. The concrete
retained-garbage compiler reports its actual width and a schedule-dependent
logical dependency depth rather than silently discarding intermediate
S-box/key-schedule history.
