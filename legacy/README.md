# Legacy and exploratory scripts

These files are preserved for research provenance. They are **not** the
canonical implementation used to certify the npj Quantum Information
submission.

## components/

- `addition_modulo2_64_projectq.py` — ProjectQ component experiment for the
  corrected Cuccaro-style 64-bit modular adder.
- `kalyna_mixcolumns_projectq.py` — ProjectQ/CNOT-network experiment for the
  Kalyna MDS layer.

## estimators/

- `kalyna_key_256_depth.py` — structural ProjectQ depth estimator used during
  development. It intentionally omits some functional key-schedule details in
  its default counting mode (for example selected-word copy costs and
  specification constants) and must not be treated as a complete cipher
  implementation.
- `kalyna_key_128_shared_monomial_fragment.py` — historical shared-monomial
  S-box analysis fragment.
- `kalyna_key_schedule_128_pre_correction.py` — obsolete pre-correction
  formula estimator. It contains the earlier 514-CNOT eta convention and
  direct-ANF S-box counts; it is archived only to preserve the development
  history.

## Canonical submission code

Use:

- `src/kalyna_oracle/compiler.py` for the exact functional reversible
  compiler;
- `validation/run_full_oracle_certificate.py` for the clean-oracle
  certificate;
- the scripts under `validation/` for restricted-key, finite-shot,
  occupancy, component-cleanup and resource checks.

Do not quote numerical results from the legacy directory in a manuscript.
