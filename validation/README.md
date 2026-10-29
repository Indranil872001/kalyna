# Kalyna full-round validation package

This directory contains the executable checks used by the revised
known-plaintext quantum key-search manuscript.

## Evidence layers

1. **Pinned official reference predicate.** CI clones the public Kalyna
   reference implementation by Roman Oliynykov et al. at commit
   `22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea`. Every scanner first
   reproduces the official Kalyna-128/128 or Kalyna-128/256 known-answer
   vector before generating experimental data.

2. **Historical-key full-round searches.** All ten rounds of Kalyna-128/128
   or all fourteen rounds of Kalyna-128/256 and the complete key schedule are
   retained. The search domain is a deterministic spread affine subspace of
   the master key, rather than only the low key bits. The historical-key
   predicates use two plaintext-ciphertext pairs for 128/128 and three for
   128/256. Exhaustive scans are run for
   `u = 8,10,12,14,16,18,20`.

3. **Grover amplitude validation.** For `u <= 14`, every amplitude in the
   `2^u` candidate register is evolved explicitly. For larger `u`, the
   exactly equivalent two-amplitude recurrence for one marked state and the
   symmetric unmarked subspace is used. Both numerical routes are compared
   with the exact Grover success formula.

4. **Full-round wrong-key occupancy.** The multiplicity experiment retains
   the complete cipher but truncates only the ciphertext equality test. Each
   deterministic trial uses a different spread affine master-key subspace, a
   different plaintext, and a different output-window offset. For each tested
   `u`, the same full-round candidate encryptions are scored at
   `b=u-4,u,u+4`, corresponding to expected wrong-key multiplicities near
   `16,1,1/16` under the ideal-cipher model. The CI workflow uses
   `u = 12,14,16` and 128 trials per variant and subspace size.

5. **Local reversible cleanup and equivalence.** The optimized shared-monomial
   S-box construction is exhaustively checked on all 1024 S-box input cases
   with temporary products returned to zero. The 64-bit modulo adder is tested
   on boundary cases and 5000 seeded random pairs with the addend restored and
   carry cleaned. The MDS CNOT network is checked on all 64 basis vectors.

6. **Resource and depth regeneration.** Corrected logical resource tables and
   dependency-aware depths are regenerated in CI from the declared component
   model rather than copied manually into the evidence package.

## Scope boundary

The full-round restricted-key experiments validate the **known-plaintext
predicate**, the exact marked set in tractable master-key domains, and the
associated Grover or wrong-key occupancy calculations while preserving the
complete Kalyna cipher.

They do **not** constitute a gate-by-gate state-vector simulation of the full
reversible Kalyna oracle. The local cleanup tests certify the stated nonlinear
S-box work bits, Cuccaro-style carry cleanup, and MDS network, but not every
temporary register in one architecture-specific compiled full-oracle schedule.
Physical routing, surface-code overhead, magic-state scheduling, and device
latency are outside the present logical model.

The truncated equality test in the multiplicity experiment is an
**experimental surrogate** used to make the spurious-key occupancy transition
observable in a tractable domain. It is not the production historical-key
recovery oracle.

## Reproduce

The workflow `.github/workflows/fullround-validation.yml` performs the
complete run. On Linux with GCC and Python 3:

```bash
git clone https://github.com/Roman-Oliynykov/Kalyna-reference.git /tmp/Kalyna-reference
git -C /tmp/Kalyna-reference checkout 22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea

gcc -O3 -std=c11 -I/tmp/Kalyna-reference \
  validation/reference_sparse_scan.c \
  /tmp/Kalyna-reference/kalyna.c /tmp/Kalyna-reference/tables.c \
  -o validation/kalyna_scan

gcc -O3 -std=c11 -I/tmp/Kalyna-reference \
  validation/reference_oracle_multiplicity.c \
  /tmp/Kalyna-reference/kalyna.c /tmp/Kalyna-reference/tables.c \
  -o validation/kalyna_multiplicity_scan

python3 validation/check_local_cleanup.py

python3 validation/run_fullround_sparse.py \
  --scanner ./validation/kalyna_scan \
  --unknown-bits 8,10,12,14,16,18,20 \
  --include-minimal

python3 validation/run_oracle_multiplicity.py \
  --scanner ./validation/kalyna_multiplicity_scan \
  --unknown-bits 12,14,16 \
  --trials 128

python3 validation/corrected_resource_counts.py
```

Machine-readable output, human-readable reports, provenance information and
SHA-256 checksums are generated under `outputs/`.
