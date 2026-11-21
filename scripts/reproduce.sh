#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODE="${1:-quick}"
if [[ "$MODE" != "quick" && "$MODE" != "full" ]]; then echo 'Usage: bash scripts/reproduce.sh [quick|full]' >&2; exit 2; fi
REFDIR="$ROOT/.cache/Kalyna-reference"
PIN="22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea"
if [[ ! -d "$REFDIR/.git" ]]; then mkdir -p "$ROOT/.cache"; git clone https://github.com/Roman-Oliynykov/Kalyna-reference.git "$REFDIR"; fi
git -C "$REFDIR" fetch origin --quiet
git -C "$REFDIR" checkout --detach --quiet "$PIN"
test "$(git -C "$REFDIR" rev-parse HEAD)" = "$PIN"
REFEXE="$ROOT/validation/kalyna_reference_certificate"
gcc -O3 -std=c11 -Wall -Wextra -I"$REFDIR" validation/reference_oracle_certificate.c "$REFDIR/kalyna.c" "$REFDIR/tables.c" -o "$REFEXE"
python3 -m py_compile src/kalyna_oracle/compiler.py validation/run_full_oracle_certificate.py validation/optimized_oracle_experiment.py validation/check_sbox_monomial_bank.py validation/corrected_resource_counts.py validation/run_fullround_sparse.py validation/run_finite_shot_recovery.py validation/run_oracle_multiplicity.py validation/seeded_occupancy_replicate.py
PYTHONPATH=. python3 validation/check_sbox_monomial_bank.py
PYTHONPATH=. python3 validation/run_full_oracle_certificate.py --reference "$REFEXE" --random-cases 10
for h in 3 4; do PYTHONPATH=. python3 validation/optimized_oracle_experiment.py --cutoff "$h" --reference "$REFEXE" --random-cases 10 --out "outputs/optimized_oracle/cutoff_$h.json"; done
PYTHONPATH=. python3 validation/corrected_resource_counts.py
if [[ "$MODE" == "quick" ]]; then echo KALYNA_REVIEWER_QUICK_PASS; exit 0; fi
gcc -O3 -std=c11 -Wall -Wextra -I"$REFDIR" validation/reference_sparse_scan.c "$REFDIR/kalyna.c" "$REFDIR/tables.c" -o validation/kalyna_scan
PYTHONPATH=. python3 validation/run_fullround_sparse.py --scanner "$ROOT/validation/kalyna_scan" --unknown-bits 8,10,12,14,16,18,20 --include-minimal
PYTHONPATH=. python3 validation/run_finite_shot_recovery.py
gcc -O3 -std=c11 -Wall -Wextra -I"$REFDIR" validation/reference_oracle_multiplicity.c "$REFDIR/kalyna.c" "$REFDIR/tables.c" -o validation/kalyna_multiplicity_scan
PYTHONPATH=. python3 validation/run_oracle_multiplicity.py --scanner "$ROOT/validation/kalyna_multiplicity_scan" --unknown-bits 12,14,16 --trials 128
python3 -c 'import scipy' || { echo 'Install dependencies: python3 -m pip install -r requirements.txt' >&2; exit 1; }
gcc -O3 -std=c11 -Wall -Wextra -I"$REFDIR" validation/reference_oracle_multiplicity_seeded.c "$REFDIR/kalyna.c" "$REFDIR/tables.c" -o validation/kalyna_multiplicity_seeded
PYTHONPATH=. python3 validation/seeded_occupancy_replicate.py --scanner "$ROOT/validation/kalyna_multiplicity_seeded" --unknown-bits 12,14,16 --trials-per-seed 256
echo KALYNA_REVIEWER_FULL_PASS
