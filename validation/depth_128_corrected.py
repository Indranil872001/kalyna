#!/usr/bin/env python3
"""Dependency-aware ProjectQ depth remeasurement for corrected Kalyna-128/128.

This script imports the common corrected 128-bit components from
../kalyna_key_256 and instantiates the 10-round 128/128 key schedule and
encryption structure used by the manuscript.  It is intentionally a depth
checker, not a physical routing model.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

from projectq import MainEngine


ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("kalyna_common", str(ROOT / "kalyna_key_256"))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


def ksigma_128(eng, master):
    state = eng.allocate_qureg(128)
    state = m.kalyna_eta_add_round_key_mod64(eng, state, master)
    state = m.kalyna_pi_tau_psi_optimized(eng, state)
    state = m.kalyna_kappa_xor_key(eng, state, master)
    state = m.kalyna_pi_tau_psi_optimized(eng, state)
    state = m.kalyna_eta_add_round_key_mod64(eng, state, master)
    state = m.kalyna_pi_tau_psi_optimized(eng, state)
    return list(state)


def one_even_key_128(eng, master, ksigma, even_index):
    # Explicit phi_i layer, as in the manuscript component model.
    phi = m.generate_phi_i_explicit(eng, ksigma)
    state = eng.allocate_qureg(128)

    # The rotated W_i selection is a wire-reindexing operation in the stated
    # model. As in the 128/256 depth script, no explicit input-copy CNOTs are
    # included in the manuscript's component-count convention.
    _ = m.rotl_logical(master, 16 * even_index)

    state = m.kalyna_eta_add_round_key_mod64(eng, state, phi)
    state = m.kalyna_pi_tau_psi_optimized(eng, state)
    state = m.kalyna_kappa_xor_key(eng, state, phi)
    state = m.kalyna_pi_tau_psi_optimized(eng, state)
    state = m.kalyna_eta_add_round_key_mod64(eng, state, phi)
    return list(state)


def key_schedule_128(eng, master):
    ks = ksigma_128(eng, master)
    roundkeys = [None] * 11
    for i in range(0, 11, 2):
        roundkeys[i] = one_even_key_128(eng, master, ks, i)
    for i in range(1, 10, 2):
        roundkeys[i] = m.rotl_logical(roundkeys[i - 1], 56)
    return roundkeys


def encryption_core_128(eng, plaintext, roundkeys):
    s = m.kalyna_eta_add_round_key_mod64(eng, plaintext, roundkeys[0])
    for r in range(1, 10):
        s = m.kalyna_inner_round_128_optimized(eng, s, roundkeys[r])
    s = m.kalyna_final_round_128_optimized(eng, s, roundkeys[10])
    return s


def measure(which):
    dc = m.DepthEstimator()
    eng = MainEngine(backend=dc)
    if which == "ks":
        master = eng.allocate_qureg(128)
        _ = key_schedule_128(eng, master)
    elif which == "enc":
        plaintext = eng.allocate_qureg(128)
        rks = [eng.allocate_qureg(128) for _ in range(11)]
        _ = encryption_core_128(eng, plaintext, rks)
    elif which == "full":
        master = eng.allocate_qureg(128)
        plaintext = eng.allocate_qureg(128)
        rks = key_schedule_128(eng, master)
        _ = encryption_core_128(eng, plaintext, rks)
    else:
        raise ValueError(which)
    eng.flush()
    return dc.max_depth


if __name__ == "__main__":
    for mode in ("enc", "ks", "full"):
        print(f"128/128 {mode} depth = {measure(mode)}")
