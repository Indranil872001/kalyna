#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REF_DIR="${ROOT}/.cache/Kalyna-reference"
PIN="22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea"

mkdir -p "${ROOT}/.cache"
if [ ! -d "${REF_DIR}/.git" ]; then
  git clone https://github.com/Roman-Oliynykov/Kalyna-reference.git "${REF_DIR}"
fi

git -C "${REF_DIR}" fetch --all --tags --quiet
git -C "${REF_DIR}" checkout --quiet "${PIN}"
test "$(git -C "${REF_DIR}" rev-parse HEAD)" = "${PIN}"

gcc -O3 -std=c11 -Wall -Wextra -I"${REF_DIR}" \
  "${ROOT}/validation/reference_oracle_certificate.c" \
  "${REF_DIR}/kalyna.c" "${REF_DIR}/tables.c" \
  -o "${ROOT}/validation/kalyna_reference_certificate"

python3 "${ROOT}/validation/run_full_oracle_certificate.py" \
  --reference "${ROOT}/validation/kalyna_reference_certificate" \
  --random-cases 10

echo
echo "Certificate: ${ROOT}/outputs/full_oracle_certificate/full_oracle_certificate.md"
