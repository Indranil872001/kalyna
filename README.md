# Kalyna — clean reviewer reproducibility snapshot

**Paper:** Full-round quantum key search and spurious-key occupancy in Kalyna
**Target:** npj Quantum Information

This isolated branch contains *only the Kalyna code and permanent evidence required to reproduce the manuscript*. It excludes WARP, old exploratory ProjectQ estimators, duplicate v1/v2 datasets and retired workflows. **No other branch or repository was deleted or modified.**

## One command to verify the functional circuit

Requires Python 3.11+, git and GCC. The command fetches the independent Kalyna reference at a frozen commit.

```bash
git clone --branch npj-reviewer-clean-20261121 --single-branch https://github.com/Indranil872001/kalyna.git
cd kalyna
bash scripts/reproduce.sh quick
```

This checks all four S-box truth tables (all 256 inputs, three nonzero/zero output-register patterns, h=2/3/4), then performs original and optimized full-round oracle tests against independent ciphertext and round-key generation, including correct/wrong phase marks and cleanup. It also regenerates the original logical resource audit.

For the complete, slower restricted-key and occupancy experiments:

```bash
python3 -m pip install -r requirements.txt
bash scripts/reproduce.sh full
```

Outputs go to ignored `outputs/`. Reproducibility is also checked automatically under GitHub **Actions** for the clean branch. Full occupancy runs can be computationally expensive.

## Claim-to-code map

| Manuscript result | Code | Permanent evidence |
|---|---|---|
| Full-round Kalyna reference compiler, clean oracle | `src/kalyna_oracle/compiler.py`, `validation/run_full_oracle_certificate.py` | `evidence/npj_submission_v3/full_oracle_certificate_summary.json` |
| New monomial-bank S-box, verified h=3 and h=4 full oracles | `validation/optimized_oracle_experiment.py`, `validation/check_sbox_monomial_bank.py` | `evidence/npj_optimized_validation/verified_optimized_measurements.json`, `sbox_tradeoff.csv` |
| Local S-box, 64-bit adder and MDS cleanup checks | `validation/check_local_cleanup.py` | `evidence/npj_submission_v3/local_component_cleanup.json` |
| Original full-cipher gate counts | `validation/corrected_resource_counts.py` | `evidence/npj_submission_v3/exact_resource_audit.json` |
| Historical-key restricted-domain scan (up to 2^20) | `validation/reference_sparse_scan.c`, `validation/run_fullround_sparse.py` | `evidence/npj_submission_v3/fullround_sparse_results.csv` |
| Grover probabilities, 1024-shot decoder | `validation/run_finite_shot_recovery.py` | `evidence/npj_submission_v3/finite_shot_summary.csv`, `finite_shot_u20_sample.json` |
| Original 128-trial spurious-key study | `validation/reference_oracle_multiplicity.c`, `validation/run_oracle_multiplicity.py` | `evidence/npj_submission_v3/oracle_multiplicity_summary.csv` |
| 512-observation independently seeded replication | `validation/reference_oracle_multiplicity_seeded.c`, `validation/seeded_occupancy_replicate.py` | `evidence/npj_optimized_validation/seeded_occupancy_512_summary.csv` |

Read [`CLAIM_TO_CODE.md`](CLAIM_TO_CODE.md) for exact scope, limitations and previous validation-run provenance.

## Independent reference and scientific scope

Reference implementation: https://github.com/Roman-Oliynykov/Kalyna-reference at commit `22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea`. Its source is fetched, not duplicated here.

These experiments **do not** execute Grover on physical quantum hardware, nor densely simulate the several-thousand-qubit compiled oracle. The predicate is established from complete classical Kalyna encryptions on restricted master-key domains, then exact mathematical amplitude/shot formulas are applied. The reported quantum counts are logical circuit resources for specific emitted constructions, without hardware routing or error correction; optimized reductions are measured against our own original shared-ANF compiler. Occupancy comparisons use truncated b-bit outputs as a diagnostic, not a production full-equality historical-key oracle.

## Provenance

Original full-oracle/finite-shot submission snapshot: `npj-submission-v3` at `964c5c3ddb42b288f6a69d740e5cf400bcc271bd`.
Optimized source and seeded replication: `npj-optimized-oracle-audit-20261121` at `707bc0dc65a3c6660681b99c51c6718707d001d4`.
Certified original optimized workflow: https://github.com/Indranil872001/kalyna/actions/runs/44899708507 ; seeded-replication workflow: https://github.com/Indranil872001/kalyna/actions/runs/44899877953 .

The original development history remains intact on its existing branches.
