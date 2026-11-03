#!/usr/bin/env python3
"""
Finite-shot reduced-domain Grover recovery for full-round Kalyna predicates.

This script consumes the historical-key marked-set results produced by
run_fullround_sparse.py.  For every tested search size N=2^u with one marked
historical key, it compares three iteration choices:

  1. j_star: first Grover maximum (near-unit single-shot success);
  2. j_exp: Mini-AES-style expected-count rule S*p_j >= T;
  3. j_conf: smallest j for which a threshold decoder succeeds with at least
     the requested confidence after S measurement shots.

The decoder declares recovery when one measured key appears at least T times.
For M=1 the target count is Binomial(S,p_j). Each individual wrong key has
marginal probability q_j=(1-p_j)/(N-1). A rigorous union bound gives

  P(recovery) >= P(C_target >= T)
                 - (N-1) P(C_wrong >= T).

This is a depth-per-shot trade-off, not an algorithmic query reduction:
S independent shots require S*j oracle iterations in total.

The script also performs deterministic Monte-Carlo shot sampling so the
submission package contains explicit 1024-shot histograms, not only formulas.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path


def grover_probability(N: int, M: int, j: int) -> float:
    theta = math.asin(math.sqrt(M / N))
    return math.sin((2 * j + 1) * theta) ** 2


def optimal_iterations(N: int, M: int) -> tuple[int, float]:
    theta = math.asin(math.sqrt(M / N))
    center = math.pi / (4.0 * theta) - 0.5
    lo = max(0, int(math.floor(center)) - 5)
    hi = int(math.ceil(center)) + 5
    best = max(range(lo, hi + 1), key=lambda j: grover_probability(N, M, j))
    return best, grover_probability(N, M, best)


def log_binom_pmf(n: int, k: int, p: float) -> float:
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == n else -math.inf
    return (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * math.log(p)
        + (n - k) * math.log1p(-p)
    )


def logsumexp(values: list[float]) -> float:
    finite = [x for x in values if math.isfinite(x)]
    if not finite:
        return -math.inf
    m = max(finite)
    return m + math.log(sum(math.exp(x - m) for x in finite))


def log_binom_tail_ge(n: int, p: float, threshold: int) -> float:
    if threshold <= 0:
        return 0.0
    if threshold > n:
        return -math.inf
    return logsumexp([log_binom_pmf(n, k, p) for k in range(threshold, n + 1)])


def binom_tail_ge(n: int, p: float, threshold: int) -> float:
    lt = log_binom_tail_ge(n, p, threshold)
    if lt == -math.inf:
        return 0.0
    if lt >= 0.0:
        return 1.0
    return min(1.0, math.exp(lt))


def recovery_lower_bound(N: int, j: int, shots: int, threshold: int) -> tuple[float, float, float, float]:
    p = grover_probability(N, 1, j)
    q = (1.0 - p) / (N - 1)

    target_tail = binom_tail_ge(shots, p, threshold)
    log_wrong_tail = log_binom_tail_ge(shots, q, threshold)
    log_union = math.log(N - 1) + log_wrong_tail
    union_wrong = 0.0 if log_union < -745 else min(1.0, math.exp(log_union))
    lower = min(1.0, max(0.0, target_tail - union_wrong))
    log10_false_alarm = log_union / math.log(10.0)
    return p, target_tail, lower, log10_false_alarm


def first_expected_count_iteration(N: int, shots: int, threshold: int, j_star: int) -> int:
    for j in range(j_star + 1):
        if shots * grover_probability(N, 1, j) >= threshold:
            return j
    raise RuntimeError("threshold not reached before first Grover maximum")


def first_confident_iteration(N: int, shots: int, threshold: int, confidence: float, j_star: int) -> tuple[int, float, float, float]:
    for j in range(j_star + 1):
        p, target_tail, lower, log10_false = recovery_lower_bound(
            N, j, shots, threshold
        )
        if lower >= confidence:
            return j, p, lower, log10_false
    raise RuntimeError("requested confidence not reached before first Grover maximum")


def sample_binomial(rng: random.Random, n: int, p: float) -> int:
    return sum(1 for _ in range(n) if rng.random() < p)


def sample_histogram_one_marked(
    rng: random.Random, N: int, p: float, shots: int, marked: int = 0
) -> dict:
    target_count = sample_binomial(rng, shots, p)
    remaining = shots - target_count
    counts: dict[int, int] = {marked: target_count}
    if remaining:
        # Conditional on an unmarked outcome, all N-1 wrong keys are uniform.
        for _ in range(remaining):
            r = rng.randrange(N - 1)
            key = r if r < marked else r + 1
            counts[key] = counts.get(key, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    top = ordered[:5]
    max_wrong = max((c for k, c in counts.items() if k != marked), default=0)
    return {
        "target_count": target_count,
        "max_wrong_count": max_wrong,
        "distinct_wrong_keys_observed": len([1 for k in counts if k != marked]),
        "top5": [{"key_index": k, "count": c} for k, c in top],
    }


def load_historical_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        rows = json.loads(path.read_text())
    hist = [r for r in rows if r.get("model") == "historical-key"]
    if not hist:
        raise RuntimeError("no historical-key rows found")
    for r in hist:
        if int(r["marked_count"]) != 1:
            raise AssertionError(f"finite-shot experiment requires M=1: {r}")
    return hist


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/fullround_validation/fullround_sparse_results.json"),
    )
    ap.add_argument(
        "--outdir",
        type=Path,
        default=Path("outputs/finite_shot_recovery"),
    )
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument("--threshold", type=int, default=100)
    ap.add_argument("--confidence", type=float, default=0.99)
    ap.add_argument("--seed", type=int, default=20261103)
    args = ap.parse_args()

    rows = load_historical_rows(args.input)
    args.outdir.mkdir(parents=True, exist_ok=True)

    summary: list[dict] = []
    samples: list[dict] = []

    # The amplitude dynamics depend only on N and M.  We retain one summary row
    # per cipher variant to keep the cipher-specific provenance explicit.
    for r in rows:
        u = int(r["unknown_bits"])
        N = int(r["candidates"])
        variant = r["variant"]
        j_star, p_star = optimal_iterations(N, 1)
        j_exp = first_expected_count_iteration(
            N, args.shots, args.threshold, j_star
        )
        p_exp = grover_probability(N, 1, j_exp)
        j_conf, p_conf, lower_conf, log10_false = first_confident_iteration(
            N, args.shots, args.threshold, args.confidence, j_star
        )
        target_tail_conf = binom_tail_ge(args.shots, p_conf, args.threshold)

        # Query-efficient 99% single-run point, included to distinguish
        # depth-per-shot reduction from total oracle work.
        j_single_99 = None
        p_single_99 = None
        for j in range(j_star + 1):
            p = grover_probability(N, 1, j)
            if p >= args.confidence:
                j_single_99 = j
                p_single_99 = p
                break
        if j_single_99 is None:
            j_single_99, p_single_99 = j_star, p_star

        row = {
            "variant": variant,
            "unknown_bits": u,
            "candidates": N,
            "shots": args.shots,
            "threshold": args.threshold,
            "confidence_target": args.confidence,
            "j_star": j_star,
            "p_star": p_star,
            "j_expected_count": j_exp,
            "p_expected_count": p_exp,
            "expected_target_count_at_j_expected": args.shots * p_exp,
            "j_confident_threshold": j_conf,
            "p_at_j_confident": p_conf,
            "expected_target_count_at_j_confident": args.shots * p_conf,
            "target_threshold_probability": target_tail_conf,
            "recovery_probability_lower_bound": lower_conf,
            "log10_union_false_alarm_bound": log10_false,
            "depth_reduction_vs_j_star": j_star / j_conf,
            "total_oracle_iterations_for_1024_shots": args.shots * j_conf,
            "j_single_run_99": j_single_99,
            "p_single_run_99": p_single_99,
        }
        summary.append(row)

        rng = random.Random(
            args.seed
            + 1000003 * (128 if variant == "128/128" else 256)
            + 7919 * u
        )
        for label, j, p in [
            ("expected_count", j_exp, p_exp),
            ("confidence_99", j_conf, p_conf),
            ("first_maximum", j_star, p_star),
        ]:
            sample = sample_histogram_one_marked(rng, N, p, args.shots)
            samples.append(
                {
                    "variant": variant,
                    "unknown_bits": u,
                    "candidates": N,
                    "policy": label,
                    "iterations": j,
                    "success_probability": p,
                    "shots": args.shots,
                    **sample,
                }
            )

    (args.outdir / "finite_shot_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    (args.outdir / "finite_shot_samples.json").write_text(
        json.dumps(samples, indent=2, sort_keys=True) + "\n"
    )

    fields = list(summary[0].keys())
    with (args.outdir / "finite_shot_summary.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(summary)

    report = [
        "# Finite-shot Grover recovery on full-round Kalyna predicates",
        "",
        f"Shots S={args.shots}, detection threshold T={args.threshold}, "
        f"required recovery lower bound={args.confidence:.3f}.",
        "",
        "The full-round Kalyna scanner determines the exact marked set in each",
        "restricted master-key domain.  The finite-shot experiment then executes",
        "the mathematically exact Grover distribution for that marked set and",
        "samples measurements.  It is therefore an end-to-end reduced-domain",
        "Grover recovery experiment at the predicate level, not a gate-by-gate",
        "state-vector simulation of the complete reversible Kalyna circuit.",
        "",
        "| Variant | u | j* | j_exp | j_99,T | p(j_99,T) | E[count] | recovery LB | depth reduction | j(single 99%) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary:
        report.append(
            f"| {r['variant']} | {r['unknown_bits']} | {r['j_star']} | "
            f"{r['j_expected_count']} | {r['j_confident_threshold']} | "
            f"{r['p_at_j_confident']:.6f} | "
            f"{r['expected_target_count_at_j_confident']:.1f} | "
            f"{r['recovery_probability_lower_bound']:.9f} | "
            f"{r['depth_reduction_vs_j_star']:.2f}x | "
            f"{r['j_single_run_99']} |"
        )
    report += [
        "",
        "Interpretation:",
        "- j_exp reproduces the expected-count logic used in the recent Mini-AES study.",
        "- j_99,T strengthens that rule by requiring a 99% finite-shot recovery",
        "  lower bound after also union-bounding threshold collisions from every",
        "  wrong key.",
        "- The smaller j_99,T reduces circuit depth per shot by roughly fourfold,",
        "  but 1024 shots require 1024 independent circuit executions.  It is",
        "  therefore a depth/noise trade-off, not an asymptotic query reduction.",
        "- j(single 99%) is the first iteration giving at least 99% single-run",
        "  success.  It remains close to the first Grover maximum and is the",
        "  appropriate comparison when total oracle calls, rather than per-shot",
        "  depth, are the objective.",
    ]
    (args.outdir / "finite_shot_report.md").write_text("\n".join(report) + "\n")

    for r in summary:
        print(json.dumps(r, sort_keys=True))


if __name__ == "__main__":
    main()
