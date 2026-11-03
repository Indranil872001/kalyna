# Finite-shot Grover recovery on full-round Kalyna predicates

Shots S=1024, detection threshold T=100, required recovery lower bound=0.990.

The full-round Kalyna scanner determines the exact marked set in each
restricted master-key domain. The finite-shot experiment then executes the
mathematically exact Grover distribution for that marked set and samples
measurements. It is therefore an end-to-end reduced-domain Grover recovery
experiment at the predicate level, not a gate-by-gate state-vector simulation
of the complete reversible Kalyna circuit.

| Variant | u | j* | j_exp | j_99,T | p(j_99,T) | E[count] | recovery LB | depth reduction | j(single 99%) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 128/128 | 8 | 12 | 3 | 3 | 0.179721 | 184.0 | 1.000000000 | 4.00x | 12 |
| 128/128 | 10 | 25 | 5 | 6 | 0.156205 | 160.0 | 0.999999983 | 4.17x | 24 |
| 128/128 | 12 | 50 | 10 | 11 | 0.123695 | 126.7 | 0.996015623 | 4.55x | 47 |
| 128/128 | 14 | 100 | 20 | 23 | 0.128878 | 132.0 | 0.999141602 | 4.35x | 94 |
| 128/128 | 16 | 201 | 41 | 45 | 0.121125 | 124.0 | 0.992030125 | 4.47x | 188 |
| 128/128 | 18 | 402 | 81 | 91 | 0.122402 | 125.3 | 0.994320504 | 4.42x | 376 |
| 128/128 | 20 | 804 | 163 | 181 | 0.120488 | 123.4 | 0.990602553 | 4.44x | 753 |
| 128/256 | 8 | 12 | 3 | 3 | 0.179721 | 184.0 | 1.000000000 | 4.00x | 12 |
| 128/256 | 10 | 25 | 5 | 6 | 0.156205 | 160.0 | 0.999999983 | 4.17x | 24 |
| 128/256 | 12 | 50 | 10 | 11 | 0.123695 | 126.7 | 0.996015623 | 4.55x | 47 |
| 128/256 | 14 | 100 | 20 | 23 | 0.128878 | 132.0 | 0.999141602 | 4.35x | 94 |
| 128/256 | 16 | 201 | 41 | 45 | 0.121125 | 124.0 | 0.992030125 | 4.47x | 188 |
| 128/256 | 18 | 402 | 81 | 91 | 0.122402 | 125.3 | 0.994320504 | 4.42x | 376 |
| 128/256 | 20 | 804 | 163 | 181 | 0.120488 | 123.4 | 0.990602553 | 4.44x | 753 |

Interpretation:
- j_exp reproduces the expected-count logic used in the 2026 Mini-AES npj study.
- j_99,T strengthens that rule by requiring a 99% finite-shot recovery lower
  bound after union-bounding threshold collisions from every wrong key.
- The smaller j_99,T reduces circuit depth per shot by roughly fourfold, but
  1024 shots require 1024 independent circuit executions. It is therefore a
  depth/noise trade-off, not an asymptotic query reduction.
- j(single 99%) is the first iteration giving at least 99% single-run success
  and remains close to the first Grover maximum.
