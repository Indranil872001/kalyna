#!/usr/bin/env python3
"""Generate the compiler-level clean-oracle certificate for Kalyna.

The script:
  * compiles the exact reversible key schedule + encryption for 128/128 and
    128/256;
  * compares the ciphertext and every round key against the pinned independent
    C reference for the official KAT plus seeded random cases;
  * verifies exact compute/reverse restoration on every tested basis input;
  * compiles the historical-key multi-pair phase oracle;
  * verifies the historical key is phase-marked, a nearby wrong key is not,
    and both executions restore every non-key work wire;
  * asserts the complete CCX-equivalent Grover-iteration counts used by the
    manuscript;
  * records exact gate hashes, width and corrected Clifford counts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.kalyna_oracle.compiler import (  # noqa: E402
    compile_cipher,
    compile_phase_oracle,
    complete_iteration_nonclifford,
    historical_key,
    known_pairs,
    simulate_cipher_program,
    simulate_phase_oracle_basis,
    structural_inverse_certificate,
)


def reference_case(exe: Path, key_bits: int, key: bytes, pt: bytes) -> dict:
    cp = subprocess.run(
        [str(exe), str(key_bits), key.hex(), pt.hex()],
        check=True,
        text=True,
        capture_output=True,
    )
    lines = [x for x in cp.stdout.splitlines() if x.strip()]
    if not lines:
        raise RuntimeError("reference harness produced no output")
    return json.loads(lines[-1])


def test_cipher_variant(exe: Path, key_bits: int, random_cases: int) -> dict:
    program = compile_cipher(key_bits)
    rng = random.Random(20261103 + key_bits)

    cases: list[tuple[bytes, bytes, str]] = []
    if key_bits == 128:
        cases.append(
            (
                bytes(range(0x00, 0x10)),
                bytes(range(0x10, 0x20)),
                "official_kat",
            )
        )
    else:
        cases.append(
            (
                bytes(range(0x00, 0x20)),
                bytes(range(0x20, 0x30)),
                "official_kat",
            )
        )

    for i in range(random_cases):
        key = bytes(rng.randrange(256) for _ in range(key_bits // 8))
        pt = bytes(rng.randrange(256) for _ in range(16))
        cases.append((key, pt, f"seeded_random_{i}"))

    checked = []
    for key, pt, label in cases:
        ref = reference_case(exe, key_bits, key, pt)
        ct, rks, clean = simulate_cipher_program(program, key, pt)
        ref_ct = bytes.fromhex(ref["ciphertext"])
        ref_rks = [bytes.fromhex(x) for x in ref["round_keys"]]

        if ct != ref_ct:
            raise AssertionError(
                f"{key_bits} {label}: ciphertext mismatch "
                f"{ct.hex()} != {ref_ct.hex()}"
            )
        if rks != ref_rks:
            for i, (a, b) in enumerate(zip(rks, ref_rks)):
                if a != b:
                    raise AssertionError(
                        f"{key_bits} {label}: round key K{i} mismatch "
                        f"{a.hex()} != {b.hex()}"
                    )
            raise AssertionError(f"{key_bits} {label}: round-key length mismatch")
        if not clean:
            raise AssertionError(f"{key_bits} {label}: reverse tape did not clean")

        checked.append(
            {
                "label": label,
                "key": key.hex(),
                "plaintext": pt.hex(),
                "ciphertext": ct.hex(),
                "round_keys_checked": len(rks),
                "exact_reverse_cleanup": True,
            }
        )

    expected = {
        128: {"CCX": 609232, "CNOT": 504548, "X": 1550, "width": 5126},
        256: {"CCX": 803920, "CNOT": 665604, "X": 2047, "width": 6790},
    }[key_bits]
    for gate in ("CCX", "CNOT", "X"):
        if program.tape.counts[gate] != expected[gate]:
            raise AssertionError(
                f"{key_bits}: exact compiler {gate} {program.tape.counts[gate]} "
                f"!= frozen value {expected[gate]}"
            )
    if program.tape.physical_width != expected["width"]:
        raise AssertionError(
            f"{key_bits}: cipher width {program.tape.physical_width} "
            f"!= frozen value {expected['width']}"
        )

    return {
        "variant": f"128/{key_bits}",
        "tests": checked,
        "forward_summary": program.tape.summary(),
        "forward_gate_sha256": program.tape.hash_gate_slice(),
        "nonclifford_matches_manuscript": True,
    }


def test_phase_oracle(key_bits: int) -> dict:
    ps, cs = known_pairs(key_bits)
    program = compile_phase_oracle(key_bits, ps, cs)

    true_key = historical_key(key_bits)
    marked, clean = simulate_phase_oracle_basis(program, true_key)
    if not marked or not clean:
        raise AssertionError(
            f"{key_bits}: historical key oracle result marked={marked}, clean={clean}"
        )

    wrong_specs = [
        (0, 0x01),
        (0, 0x80),
        (len(true_key) // 2, 0x04),
        (len(true_key) - 1, 0x40),
    ]
    wrong_results = []
    for byte_index, mask in wrong_specs:
        wrong = bytearray(true_key)
        wrong[byte_index] ^= mask
        wrong_marked, wrong_clean = simulate_phase_oracle_basis(program, bytes(wrong))
        if wrong_marked or not wrong_clean:
            raise AssertionError(
                f"{key_bits}: wrong key at byte {byte_index} mask {mask:#x} "
                f"marked={wrong_marked}, clean={wrong_clean}"
            )
        wrong_results.append(
            {
                "byte_index": byte_index,
                "xor_mask": mask,
                "phase_marked": wrong_marked,
                "exact_cleanup": wrong_clean,
            }
        )

    resources = complete_iteration_nonclifford(program)
    expected_iter = 1703126 if key_bits == 128 else 2963222
    expected_t = 11921882 if key_bits == 128 else 20742554
    expected_width = 6781 if key_bits == 128 else 11005
    expected_phase_depth = 2787759 if key_bits == 128 else 4846565
    if resources["complete_iteration_CCX_equivalent"] != expected_iter:
        raise AssertionError(
            f"{key_bits}: complete iteration CCX-equivalent mismatch "
            f"{resources['complete_iteration_CCX_equivalent']} != {expected_iter}"
        )
    if resources["complete_iteration_T_7_per_CCX"] != expected_t:
        raise AssertionError(
            f"{key_bits}: complete iteration T mismatch "
            f"{resources['complete_iteration_T_7_per_CCX']} != {expected_t}"
        )
    if resources["compiled_physical_width"] != expected_width:
        raise AssertionError(
            f"{key_bits}: phase-oracle width {resources['compiled_physical_width']} "
            f"!= frozen value {expected_width}"
        )
    if resources["complete_phase_oracle_dependency_depth"] != expected_phase_depth:
        raise AssertionError(
            f"{key_bits}: phase-oracle depth "
            f"{resources['complete_phase_oracle_dependency_depth']} "
            f"!= frozen value {expected_phase_depth}"
        )

    structural = structural_inverse_certificate(program)
    return {
        "variant": f"128/{key_bits}",
        "historical_key_phase_marked": marked,
        "historical_key_exact_cleanup": clean,
        "wrong_key_checks": wrong_results,
        "resources": resources,
        "structural_inverse_certificate": structural,
        "work_wires_returned_to_zero": resources["compiled_physical_width"] - key_bits,
    }


def write_report(result: dict, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "full_oracle_certificate.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )

    lines = [
        "# Full reversible Kalyna oracle certificate",
        "",
        "This certificate is generated from the exact functional reversible compiler,",
        "not from the legacy structural depth estimators.",
        "",
    ]
    for variant in ("128/128", "128/256"):
        c = next(x for x in result["cipher_tests"] if x["variant"] == variant)
        o = next(x for x in result["oracles"] if x["variant"] == variant)
        fs = c["forward_summary"]
        rs = o["resources"]
        lines += [
            f"## Kalyna-{variant}",
            "",
            f"- Cipher/reference cases passed: {len(c['tests'])}.",
            f"- All round keys checked in every case: yes.",
            f"- Exact forward/reverse basis cleanup: yes.",
            f"- Exact compiler forward CCX: {fs['CCX']}.",
            f"- Exact compiler forward CNOT: {fs['CNOT']}.",
            f"- Exact compiler forward X: {fs['X']}.",
            f"- Compiler physical/peak width: {fs['physical_width']} qubits.",
            f"- Historical-key phase mark: PASS.",
            f"- Four perturbed wrong-key non-marks: PASS.",
            f"- Work wires restored by compute-mark-inverse: "
            f"{o['work_wires_returned_to_zero']}.",
            f"- Complete phase-oracle dependency depth: "
            f"{rs['complete_phase_oracle_dependency_depth']}.",
            f"- Complete iteration CCX-equivalent: "
            f"{rs['complete_iteration_CCX_equivalent']}.",
            f"- Complete iteration T (7 per CCX-equivalent): "
            f"{rs['complete_iteration_T_7_per_CCX']}.",
            "",
        ]

    lines += [
        "## Interpretation",
        "",
        "The full oracle uses the same out-of-place ANF S-box construction that",
        "underlies the manuscript's nonlinear gate counts. Intermediate S-box and",
        "key-schedule histories are therefore retained as reversible garbage during",
        "the forward computation. They are not silently discarded: the phase marker",
        "is basis preserving, and the exact gate reversal restores every work wire.",
        "The certificate consequently validates a clean Grover phase oracle, while",
        "also exposing the true width of this retained-garbage realization.",
        "",
        "The older root-level ProjectQ files remain useful historical depth/count",
        "estimators but are not the canonical functional certificate.",
    ]
    (outdir / "full_oracle_certificate.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("outputs/full_oracle_certificate"),
    )
    ap.add_argument("--random-cases", type=int, default=2)
    args = ap.parse_args()

    result = {
        "reference_harness": str(args.reference),
        "cipher_tests": [
            test_cipher_variant(args.reference, 128, args.random_cases),
            test_cipher_variant(args.reference, 256, args.random_cases),
        ],
        "oracles": [
            test_phase_oracle(128),
            test_phase_oracle(256),
        ],
    }
    write_report(result, args.outdir)
    print(json.dumps(result, indent=2, sort_keys=True))
    print("FULL_ORACLE_CERTIFICATE_PASS")


if __name__ == "__main__":
    main()
