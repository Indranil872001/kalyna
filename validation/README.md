# Kalyna full-round validation package

This directory contains executable checks added to support the manuscript's
full-round validation claims.

## What is tested

1. **Pinned official reference predicate.** CI clones the public Kalyna reference
   implementation by Roman Oliynykov et al. at commit
   `22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea`. The scanner first reproduces the
   official Kalyna-128/128 and Kalyna-128/256 known-answer vectors.
2. **Restricted-key full-round searches.** For each variant, all rounds and the
   complete key schedule are retained. Only an affine subspace of the master-key
   bits is varied. The historical-key predicates use two pairs for 128/128 and
   three pairs for 128/256.
3. **Explicit sparse Grover amplitudes.** The marked set produced by the full
   cipher is used in an explicit amplitude simulation on the restricted
   candidate-key register and compared with the exact closed-form Grover
   probability.
4. **Local reversible cleanup.** The shared-monomial S-box construction is
   exhaustively checked on all 1024 S-box input cases with temporary products
   returned to zero. The 64-bit modulo adder is tested on edge cases and 5000
   seeded random pairs with the addend restored and carry cleaned. The MDS CNOT
   network is checked on all 64 basis vectors.

## Scope boundary

The full-round restricted-key experiment validates the **known-plaintext
predicate** and Grover amplitude dynamics while preserving the complete Kalyna
cipher. The local cleanup script validates the nonlinear S-box work bits,
Cuccaro-style carry cleanup, and MDS linear network.

These checks do **not** yet constitute a gate-by-gate certificate that every
temporary register in the complete ProjectQ key-schedule/encryption composition
is returned to zero, and they do not certify physical routing, surface-code
overhead, or magic-state scheduling.

## Reproduce

The GitHub Actions workflow `.github/workflows/fullround-validation.yml`
performs the complete run. On a Linux machine with GCC and Python 3:

```bash
git clone https://github.com/Roman-Oliynykov/Kalyna-reference.git /tmp/Kalyna-reference
git -C /tmp/Kalyna-reference checkout 22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea

gcc -O3 -std=c11 -I/tmp/Kalyna-reference \
  validation/reference_sparse_scan.c \
  /tmp/Kalyna-reference/kalyna.c /tmp/Kalyna-reference/tables.c \
  -o validation/kalyna_scan

python3 validation/check_local_cleanup.py
python3 validation/run_fullround_sparse.py \
  --scanner ./validation/kalyna_scan \
  --unknown-bits 8,10,12,14
```

Machine-readable results are written to `outputs/fullround_validation/`.
