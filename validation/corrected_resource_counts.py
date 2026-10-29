#!/usr/bin/env python3
"""Recompute corrected logical resource tables and Grover CCX baselines."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "fullround_validation"

PI = {"X": 60, "CNOT": 16048, "CCX": 24144}
PSI = {"X": 0, "CNOT": 3540, "CCX": 0}
KAPPA = {"X": 0, "CNOT": 128, "CCX": 0}
# Two independent corrected 64-bit modulo adders:
# one adder = 256 CNOT + 128 CCX.
ETA = {"X": 0, "CNOT": 512, "CCX": 256}


def add(*parts):
    return {g: sum(p[g] for p in parts) for g in ("X", "CNOT", "CCX")}


def scale(a, n):
    return {g: n * a[g] for g in a}


def finish(a):
    x, c, t = a["X"], a["CNOT"], a["CCX"]
    return {
        **a,
        "total_nct": x + c + t,
        "nct_cost_w5": x + c + 5*t,
        "T_7_per_CCX": 7*t,
        "H_2_per_CCX": 2*t,
        "CNOT_after_6_per_CCX": c + 6*t,
        "total_Clifford_T_template": x + (c + 6*t) + 7*t + 2*t,
    }


def encryption(rounds):
    # initial eta, rounds-1 inner (pi,psi,kappa), final (pi,psi,eta)
    return add(
        scale(ETA, 2),
        scale(PI, rounds),
        scale(PSI, rounds),
        scale(KAPPA, rounds - 1),
    )


def key_schedule(even_keys):
    # K_sigma: 3 pi + 3 psi + 2 eta + 1 kappa
    ksigma = add(scale(PI,3), scale(PSI,3), scale(ETA,2), KAPPA)
    # Each even key including explicit phi_i:
    # phi_i eta + Xi(eta,pi,psi,kappa,pi,psi,eta)
    one_even = add(scale(PI,2), scale(PSI,2), scale(ETA,3), KAPPA)
    return add(ksigma, scale(one_even, even_keys))


def historical_grover_ccx(enc_ccx: int, ks_ccx: int, key_bits: int,
                         block_bits: int, pairs: int) -> dict:
    """CCX count for one historical-key Grover iteration.

    The optimized retained-key-bank model computes the key schedule once,
    performs r forward encryptions using the shared round-key bank, marks the
    joint rn-bit equality condition, uncomputes the r encryptions, and then
    uncomputes the key schedule. Key fanout, when parallel encryption copies
    are used, is Clifford-only and therefore does not change this CCX count.

    A conservative recompute-per-pair baseline is retained for comparison.
    """
    eq = 2 * pairs * block_bits - 5
    diff = 2 * key_bits - 5

    shared_cipher = 2 * ks_ccx + 2 * pairs * enc_ccx
    shared_total = shared_cipher + eq + diff

    full_ccx = enc_ccx + ks_ccx
    recompute_cipher = 2 * pairs * full_ccx
    recompute_total = recompute_cipher + eq + diff

    return {
        "pairs": pairs,
        "equality_ccx": eq,
        "diffuser_ccx": diff,
        "shared_key_schedule": {
            "cipher_ccx": shared_cipher,
            "complete_iteration_ccx": shared_total,
            "T_7_per_CCX": 7 * shared_total,
        },
        "recompute_key_schedule_per_pair": {
            "cipher_ccx": recompute_cipher,
            "complete_iteration_ccx": recompute_total,
            "T_7_per_CCX": 7 * recompute_total,
        },
    }


def main():
    rows = {
        "128/128": {
            "encryption": finish(encryption(10)),
            "key_schedule": finish(key_schedule(6)),
        },
        "128/256": {
            "encryption": finish(encryption(14)),
            "key_schedule": finish(key_schedule(8)),
        },
    }
    for v in rows:
        raw = add(
            {g: rows[v]["encryption"][g] for g in ("X","CNOT","CCX")},
            {g: rows[v]["key_schedule"][g] for g in ("X","CNOT","CCX")},
        )
        rows[v]["full"] = finish(raw)

    expected = {
        "128/128": {
            "encryption": (600,198056,241952),
            "key_schedule": (900,304956,367280),
            "full": (1500,503012,609232),
        },
        "128/256": {
            "encryption": (840,276920,338528),
            "key_schedule": (1140,386636,465392),
            "full": (1980,663556,803920),
        },
    }
    for v, sections in expected.items():
        for sec, tup in sections.items():
            got = rows[v][sec]
            assert (got["X"],got["CNOT"],got["CCX"]) == tup, (v,sec,got,tup)

    rows["128/128"]["historical_grover"] = historical_grover_ccx(
        rows["128/128"]["encryption"]["CCX"],
        rows["128/128"]["key_schedule"]["CCX"],
        key_bits=128, block_bits=128, pairs=2,
    )
    rows["128/256"]["historical_grover"] = historical_grover_ccx(
        rows["128/256"]["encryption"]["CCX"],
        rows["128/256"]["key_schedule"]["CCX"],
        key_bits=256, block_bits=128, pairs=3,
    )

    # Lock the two headline optimized iteration counts.
    assert rows["128/128"]["historical_grover"]["shared_key_schedule"]["complete_iteration_ccx"] == 1703126
    assert rows["128/128"]["historical_grover"]["shared_key_schedule"]["T_7_per_CCX"] == 11921882
    assert rows["128/256"]["historical_grover"]["shared_key_schedule"]["complete_iteration_ccx"] == 2963222
    assert rows["128/256"]["historical_grover"]["shared_key_schedule"]["T_7_per_CCX"] == 20742554

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "corrected_resource_counts.json").write_text(
        json.dumps(rows, indent=2, sort_keys=True) + "\n"
    )

    print(json.dumps(rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
