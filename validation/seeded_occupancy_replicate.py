#!/usr/bin/env python3
"""Independently seeded full-round genuine-Kalyna occupancy replication.

Outputs trial-level evidence and exact-binomial multiplicity-adjusted summaries.
The binomial null is a nominal ideal-cipher reference, not an assumed theorem
about the deterministic affine-subspace sampling or about actual Kalyna.
"""
import argparse, collections, csv, json, math, subprocess, statistics
from pathlib import Path
from scipy.stats import binomtest

SEEDS=("0x6a09e667f3bcc909","0xbb67ae8584caa73b")
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scanner",required=True)
    parser.add_argument("--trials-per-seed",type=int,default=256)
    parser.add_argument("--unknown-bits",default="12,14,16")
    parser.add_argument("--outdir",type=Path,default=Path("outputs/seeded_occupancy"))
    args=parser.parse_args()
    args.outdir.mkdir(parents=True,exist_ok=True)
    raw=[]
    for variant in (128,256):
        for u in (int(v) for v in args.unknown_bits.split(",")):
            for seed in SEEDS:
                cmd=[args.scanner,str(variant),str(u),str(args.trials_per_seed),seed]
                run=subprocess.run(cmd,check=True,capture_output=True,text=True)
                rows=[json.loads(x) for x in run.stdout.splitlines() if x.strip()]
                if len(rows)!=3*args.trials_per_seed:
                    raise AssertionError(f"row count {variant=} {u=} {seed=}")
                for r in rows:r["seed"]=seed
                raw.extend(rows)
                print(f"COMPLETE variant={variant} u={u} seed={seed}: {len(rows)} rows",flush=True)
    # Each trial uses all three nested output windows; b groups within a fixed
    # (variant,u) are statistically dependent. Holm adjustment controls
    # familywise nominal error even without independence across test statistics.
    groups=collections.defaultdict(list)
    for r in raw:
        groups[(r["variant"],int(r["unknown_bits"]),int(r["compare_bits"]))].append(r)
    out=[]
    for (variant,u,b),rr in sorted(groups.items()):
        n=len(rr)
        N=1<<u
        ideal_q0=(1-2.0**(-b))**(N-1)
        zero=sum(r["wrong_count"]==0 for r in rr)
        wrong=[r["wrong_count"] for r in rr]
        p=binomtest(zero,n,ideal_q0,alternative="two-sided").pvalue
        out.append(dict(variant=variant,unknown_bits=u,compare_bits=b,trials=n,
                        seed_count=len(set(r["seed"] for r in rr)),
                        unique_subspace_count=len(set((r["seed"],r["subspace_base"],r["subspace_stride"]) for r in rr)),
                        zero_count=zero,zero_fraction=zero/n,ideal_zero_probability=ideal_q0,
                        empirical_mean_wrong=statistics.fmean(wrong),
                        ideal_mean_wrong=(N-1)*2.0**(-b),binomial_two_sided_p=p))
    order=sorted(range(len(out)),key=lambda i:out[i]["binomial_two_sided_p"])
    adj=[0.]*len(out);running=0.
    for rank,i in enumerate(order):
        v=min(1.,out[i]["binomial_two_sided_p"]*(len(out)-rank))
        running=max(running,v)
        adj[i]=running
    for i in range(len(out)):out[i]["holm_adjusted_p"]=adj[i]
    (args.outdir/"trials.json").write_text(json.dumps(raw,indent=1)+"\n")
    (args.outdir/"summary.json").write_text(json.dumps(out,indent=2)+"\n")
    with (args.outdir/"summary.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
    print("SUMMARY_ROWS",len(out))
    print("LOWEST_NOMINAL",json.dumps(sorted(out,key=lambda r:r["binomial_two_sided_p"])[:4],indent=2))
    print("SEEDED_OCCUPANCY_REPLICATION_PASS")

if __name__=="__main__":main()
