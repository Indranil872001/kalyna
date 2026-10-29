#!/usr/bin/env python3
"""
Aggregate the full-round Kalyna oracle-multiplicity experiment.

For a 2^u candidate-key subspace and a b-bit ciphertext comparison, the
ideal-cipher prediction for each wrong candidate is p = 2^{-b}, so

    W ~ Binomial(2^u - 1, 2^{-b}),
    E[W] = (2^u - 1) 2^{-b}.

The scanner evaluates b=u-4, u, u+4 on the same full-round encryptions,
giving expected wrong-key multiplicities approximately 16, 1, and 1/16.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


def run(scanner: Path, key_bits: int, u: int, trials: int) -> list[dict]:
    cp = subprocess.run(
        [str(scanner), str(key_bits), str(u), str(trials)],
        check=True,
        text=True,
        capture_output=True,
    )
    rows = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    expected = 3 * trials
    if len(rows) != expected:
        raise RuntimeError(f"expected {expected} rows, got {len(rows)}")
    if not all(r.get("official_kat_pass") for r in rows):
        raise AssertionError("official KAT failed")
    return rows


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def summarize(rows: list[dict]) -> dict:
    u = int(rows[0]["unknown_bits"])
    b = int(rows[0]["compare_bits"])
    N = int(rows[0]["candidates"])
    p = 2.0 ** (-b)
    lam = (N - 1) * p
    p0_bin = (1.0 - p) ** (N - 1)
    wrong = [int(r["wrong_count"]) for r in rows]
    n = len(wrong)
    mean = statistics.fmean(wrong)
    var = statistics.pvariance(wrong)
    zero_fraction = sum(x == 0 for x in wrong) / n
    hist = Counter(wrong)

    kmax = max(hist)
    tv = 0.0
    for k in range(kmax + 1):
        tv += abs(hist.get(k, 0) / n - poisson_pmf(k, lam))
    poisson_tail = max(0.0, 1.0 - sum(poisson_pmf(k, lam) for k in range(kmax + 1)))
    tv = 0.5 * (tv + poisson_tail)

    mean_se = math.sqrt((N - 1) * p * (1.0 - p) / n)
    mean_z = (mean - lam) / mean_se if mean_se > 0 else 0.0

    return {
        "variant": rows[0]["variant"],
        "key_bits": rows[0]["key_bits"],
        "unknown_bits": u,
        "compare_bits": b,
        "trials": n,
        "ideal_lambda": lam,
        "ideal_zero_probability_binomial": p0_bin,
        "ideal_zero_probability_poisson": math.exp(-lam),
        "empirical_mean_wrong": mean,
        "empirical_variance_wrong": var,
        "empirical_zero_fraction": zero_fraction,
        "variance_to_mean": (var / mean) if mean > 0 else None,
        "mean_standard_error": mean_se,
        "mean_z_score": mean_z,
        "poisson_tv_on_observed_support": tv,
        "min_wrong": min(wrong),
        "max_wrong": max(wrong),
        "histogram": dict(sorted(hist.items())),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scanner", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, default=Path("outputs/oracle_multiplicity"))
    ap.add_argument("--unknown-bits", type=int, default=16)
    ap.add_argument("--trials", type=int, default=32)
    args = ap.parse_args()

    u = args.unknown_bits
    args.outdir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict] = []
    summaries: list[dict] = []

    for key_bits in (128, 256):
        rows = run(args.scanner, key_bits, u, args.trials)
        all_rows.extend(rows)
        groups: dict[int, list[dict]] = defaultdict(list)
        for row in rows:
            groups[int(row["compare_bits"])].append(row)
        for b in sorted(groups):
            s = summarize(groups[b])
            summaries.append(s)
            print(json.dumps(s, sort_keys=True))

    (args.outdir / "oracle_multiplicity_trials.json").write_text(
        json.dumps(all_rows, indent=2, sort_keys=True) + "\n"
    )
    (args.outdir / "oracle_multiplicity_summary.json").write_text(
        json.dumps(summaries, indent=2, sort_keys=True) + "\n"
    )

    fields = [
        "variant", "key_bits", "unknown_bits", "compare_bits", "trials",
        "ideal_lambda", "ideal_zero_probability_binomial",
        "ideal_zero_probability_poisson", "empirical_mean_wrong",
        "empirical_variance_wrong", "empirical_zero_fraction",
        "variance_to_mean", "mean_standard_error", "mean_z_score",
        "poisson_tv_on_observed_support", "min_wrong", "max_wrong",
    ]
    with (args.outdir / "oracle_multiplicity_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(summaries)

    report = [
        "# Full-round Kalyna oracle-multiplicity experiment",
        "",
        "Each trial evaluates the complete Kalyna cipher and complete key schedule",
        "for every key in a 2^u affine key subspace. Only the equality test is",
        "truncated to b ciphertext bits so the false-key occupancy transition is",
        "observable at tractable u. The same full-round candidate encryption is",
        "scored at b=u-4, u, and u+4. This is an experimental surrogate, not a",
        "claim that the production key-recovery oracle compares only b bits.",
        "",
        "| Variant | u | b | trials | ideal lambda | empirical mean W | z(mean) | ideal Pr[W=0] | empirical Pr[W=0] | var/mean |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in summaries:
        vm = s["variance_to_mean"]
        vm_txt = "n/a" if vm is None else f"{vm:.3f}"
        report.append(
            f"| {s['variant']} | {s['unknown_bits']} | {s['compare_bits']} | "
            f"{s['trials']} | {s['ideal_lambda']:.5f} | "
            f"{s['empirical_mean_wrong']:.5f} | {s['mean_z_score']:.2f} | "
            f"{s['ideal_zero_probability_binomial']:.5f} | "
            f"{s['empirical_zero_fraction']:.5f} | {vm_txt} |"
        )
    report += [
        "",
        "Interpretation: b<u is the many-spurious-key regime, b=u is the",
        "critical Poisson-like regime with about one wrong key on average, and",
        "b>u is the near-unique regime. The experiment asks whether full-round",
        "Kalyna follows this generic ideal-cipher occupancy prediction within",
        "restricted searchable subspaces.",
    ]
    (args.outdir / "oracle_multiplicity_report.md").write_text("\n".join(report) + "\n")


if __name__ == "__main__":
    main()
