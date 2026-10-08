#!/usr/bin/env python3
"""
Local reversible-component validation independent of ProjectQ.

Checks:
  * all four optimized shared-monomial Kalyna S-boxes on all 256 inputs,
    including explicit temporary-product cleanup;
  * the 64-bit Cuccaro-style modulo adder on edge cases and seeded random
    vectors, including restoration of the addend and clean carry;
  * the synthesized Kalyna MDS CNOT network on every 64 basis vectors.

This script deliberately does not claim full-circuit ancilla cleanup.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_sboxes() -> list[list[int]]:
    text = (ROOT / "kalyna_key_256").read_text()
    out = []
    for sid in range(4):
        m = re.search(rf"PI{sid}_HEX\s*=\s*\"\"\"(.*?)\"\"\"", text, re.S)
        if not m:
            raise RuntimeError(f"PI{sid}_HEX not found in kalyna_key_256")
        vals = [int(x, 16) for x in m.group(1).split()]
        if len(vals) != 256:
            raise RuntimeError(f"PI{sid} has {len(vals)} entries")
        out.append(vals)
    return out


def anf_masks(sbox: list[int], out_bit: int) -> list[int]:
    a = [(sbox[x] >> out_bit) & 1 for x in range(256)]
    for i in range(8):
        bit = 1 << i
        for mask in range(256):
            if mask & bit:
                a[mask] ^= a[mask ^ bit]
    return [m for m, c in enumerate(a) if c]


def deg(mask: int) -> int:
    return mask.bit_count()


def direct_ccx_cost(mask: int) -> int:
    d = deg(mask)
    if d <= 1:
        return 0
    if d == 2:
        return 1
    return 2 * d - 3


def shared_ccx_cost(mask: int) -> int:
    d = deg(mask)
    assert d >= 2
    return 2 * d - 2


def should_share(mask: int, occurrences: int) -> bool:
    return deg(mask) >= 2 and shared_ccx_cost(mask) < occurrences * direct_ccx_cost(mask)


class Bits:
    def __init__(self, values: list[int]):
        self.s = list(values)

    def alloc(self, n: int) -> list[int]:
        ids = list(range(len(self.s), len(self.s) + n))
        self.s.extend([0] * n)
        return ids

    def cnot(self, c: int, t: int) -> None:
        self.s[t] ^= self.s[c]

    def ccx(self, a: int, b: int, t: int) -> None:
        self.s[t] ^= self.s[a] & self.s[b]


def compute_product(sim: Bits, controls: list[int]) -> list[int]:
    d = len(controls)
    assert d >= 2
    temps = sim.alloc(d - 1)
    sim.ccx(controls[0], controls[1], temps[0])
    for i in range(2, d):
        sim.ccx(temps[i - 2], controls[i], temps[i - 1])
    return temps


def uncompute_product(sim: Bits, controls: list[int], temps: list[int]) -> None:
    d = len(controls)
    for i in reversed(range(2, d)):
        sim.ccx(temps[i - 2], controls[i], temps[i - 1])
    sim.ccx(controls[0], controls[1], temps[0])
    assert all(sim.s[q] == 0 for q in temps)


def apply_direct(sim: Bits, controls: list[int], target: int) -> None:
    d = len(controls)
    if d == 0:
        sim.s[target] ^= 1
    elif d == 1:
        sim.cnot(controls[0], target)
    elif d == 2:
        sim.ccx(controls[0], controls[1], target)
    else:
        tmp = sim.alloc(d - 2)
        sim.ccx(controls[0], controls[1], tmp[0])
        for i in range(2, d - 1):
            sim.ccx(tmp[i - 2], controls[i], tmp[i - 1])
        sim.ccx(tmp[d - 3], controls[d - 1], target)
        for i in reversed(range(2, d - 1)):
            sim.ccx(tmp[i - 2], controls[i], tmp[i - 1])
        sim.ccx(controls[0], controls[1], tmp[0])
        assert all(sim.s[q] == 0 for q in tmp)


def simulate_sbox(sbox: list[int], x: int) -> int:
    xbits = [(x >> i) & 1 for i in range(8)]
    sim = Bits(xbits + [0] * 8)
    inp = list(range(8))
    out = list(range(8, 16))

    occ: dict[int, list[int]] = {}
    for ob in range(8):
        for mask in anf_masks(sbox, ob):
            occ.setdefault(mask, []).append(ob)

    for mask in sorted(occ, key=lambda m: (deg(m), m)):
        outs = occ[mask]
        d = deg(mask)
        if d == 0:
            for ob in outs:
                sim.s[out[ob]] ^= 1
        elif d == 1:
            q = (mask & -mask).bit_length() - 1
            for ob in outs:
                sim.cnot(inp[q], out[ob])
        else:
            ctrls = [inp[i] for i in range(8) if (mask >> i) & 1]
            if should_share(mask, len(outs)):
                temps = compute_product(sim, ctrls)
                prod = temps[-1]
                for ob in outs:
                    sim.cnot(prod, out[ob])
                uncompute_product(sim, ctrls, temps)
            else:
                for ob in outs:
                    apply_direct(sim, ctrls, out[ob])

    y = sum((sim.s[out[i]] & 1) << i for i in range(8))
    # All appended work bits beyond the dedicated 8 output bits must be zero.
    assert all(v == 0 for v in sim.s[16:])
    return y


def optimized_sbox_costs(sboxes: list[list[int]]) -> dict:
    layer = {"X": 0, "CNOT": 0, "CCX": 0}
    per_sbox = []
    for sbox in sboxes:
        occ: dict[int, list[int]] = {}
        for ob in range(8):
            for mask in anf_masks(sbox, ob):
                occ.setdefault(mask, []).append(ob)
        c = {"X": 0, "CNOT": 0, "CCX": 0}
        for mask, outs in occ.items():
            d = deg(mask)
            n = len(outs)
            if d == 0:
                c["X"] += n
            elif d == 1:
                c["CNOT"] += n
            elif should_share(mask, n):
                c["CCX"] += shared_ccx_cost(mask)
                c["CNOT"] += n
            else:
                c["CCX"] += n * direct_ccx_cost(mask)
        per_sbox.append(c)
        for k in layer:
            layer[k] += 4 * c[k]  # each S-box type appears four times in 128 bits
    return {"per_sbox": per_sbox, "full_layer": layer}


def cnot(st: list[int], c: int, t: int) -> None:
    st[t] ^= st[c]


def ccx(st: list[int], a: int, b: int, t: int) -> None:
    st[t] ^= st[a] & st[b]


def maj(st: list[int], a: int, b: int, c: int) -> None:
    cnot(st, a, b)
    cnot(st, a, c)
    ccx(st, b, c, a)


def uma(st: list[int], a: int, b: int, c: int) -> None:
    ccx(st, b, c, a)
    cnot(st, a, c)
    cnot(st, c, b)


def add64(a: int, b: int) -> tuple[int, int, int]:
    n = 64
    st = [(a >> i) & 1 for i in range(n)]
    st += [(b >> i) & 1 for i in range(n)]
    st += [0]
    A = list(range(n))
    B = list(range(n, 2*n))
    carry = 2*n

    maj(st, A[0], B[0], carry)
    for i in range(1, n):
        maj(st, A[i], B[i], A[i-1])
    cnot(st, A[n-1], B[n-1])
    for i in reversed(range(1, n)):
        uma(st, A[i], B[i], A[i-1])
    uma(st, A[0], B[0], carry)

    aa = sum(st[A[i]] << i for i in range(n))
    bb = sum(st[B[i]] << i for i in range(n))
    return aa, bb, st[carry]


GF_POLY_LOW = 0x1D
V = [0x01, 0x01, 0x05, 0x01, 0x08, 0x06, 0x07, 0x04]


def gf_mul(a: int, b: int) -> int:
    res, aa, bb = 0, a & 0xFF, b & 0xFF
    for _ in range(8):
        if bb & 1:
            res ^= aa
        carry = aa & 0x80
        aa = (aa << 1) & 0xFF
        if carry:
            aa ^= GF_POLY_LOW
        bb >>= 1
    return res & 0xFF


def mix_column_bytes(col: list[int]) -> list[int]:
    out = []
    for i in range(8):
        acc = 0
        for j in range(8):
            acc ^= gf_mul(V[(j - i) % 8], col[j])
        out.append(acc)
    return out


def bits_to_bytes(bits: list[int]) -> list[int]:
    return [sum(bits[8*r+i] << i for i in range(8)) for r in range(8)]


def bytes_to_bits(bs: list[int]) -> list[int]:
    return [((bs[r] >> i) & 1) for r in range(8) for i in range(8)]


def build_matrix() -> list[list[int]]:
    A = [[0]*64 for _ in range(64)]
    for i in range(64):
        bits = [0]*64
        bits[i] = 1
        out = bytes_to_bits(mix_column_bytes(bits_to_bytes(bits)))
        for r in range(64):
            A[r][i] = out[r]
    return A


def gauss_ops(A0: list[list[int]]) -> list[tuple[str,int,int]]:
    A = [r[:] for r in A0]
    ops = []
    for p in range(64):
        piv = next((r for r in range(p,64) if A[r][p]), None)
        if piv is None:
            raise AssertionError("singular MDS binary matrix")
        if piv != p:
            A[p], A[piv] = A[piv], A[p]
            ops.append(("swap", p, piv))
        for r in range(64):
            if r != p and A[r][p]:
                A[r] = [x ^ y for x, y in zip(A[r], A[p])]
                ops.append(("rowxor", p, r))
    return ops


def apply_linear(bits: list[int], ops: list[tuple[str,int,int]]) -> list[int]:
    q = list(range(64))
    st = bits[:]
    for kind, i, j in reversed(ops):
        if kind == "swap":
            q[i], q[j] = q[j], q[i]
        else:
            st[q[j]] ^= st[q[i]]
    return [st[q[i]] for i in range(64)]


def main() -> None:
    sboxes = load_sboxes()
    for sid, s in enumerate(sboxes):
        for x in range(256):
            got = simulate_sbox(s, x)
            if got != s[x]:
                raise AssertionError(f"S-box {sid} input {x:02x}: {got:02x} != {s[x]:02x}")

    costs = optimized_sbox_costs(sboxes)
    expected_layer = {"X": 60, "CNOT": 16048, "CCX": 24144}
    if costs["full_layer"] != expected_layer:
        raise AssertionError((costs["full_layer"], expected_layer))

    mask = (1 << 64) - 1
    tests = [
        (0,0), (1,0), (0,1), (mask,0), (0,mask), (mask,1),
        (mask,mask), (1 << 63, 1 << 63), (0x0123456789ABCDEF, 0xFEDCBA9876543210),
    ]
    rng = random.Random(20261009)
    tests.extend((rng.getrandbits(64), rng.getrandbits(64)) for _ in range(5000))
    for a, b in tests:
        aa, bb, carry = add64(a, b)
        if aa != a or bb != ((a + b) & mask) or carry != 0:
            raise AssertionError(
                f"adder failure a={a:016x} b={b:016x} -> {aa:016x},{bb:016x},c={carry}"
            )

    ops = gauss_ops(build_matrix())
    rowxor_count = sum(1 for op in ops if op[0] == "rowxor")
    if 2 * rowxor_count != 3540:
        raise AssertionError(f"unexpected two-column CNOT count {2*rowxor_count}")

    # Exhaustive basis-vector validation is sufficient for this linear map.
    for i in range(64):
        bits = [0]*64
        bits[i] = 1
        got = apply_linear(bits, ops)
        exp = bytes_to_bits(mix_column_bytes(bits_to_bytes(bits)))
        if got != exp:
            raise AssertionError(f"MDS basis mismatch at bit {i}")

    result = {
        "sbox": {
            "truth_table_cases": 4 * 256,
            "temporary_cleanup": "PASS",
            "optimized_layer_counts": costs["full_layer"],
        },
        "adder64": {
            "tests": len(tests),
            "addend_preserved": "PASS",
            "sum_mod_2_64": "PASS",
            "carry_cleanup": "PASS",
        },
        "mds": {
            "basis_vectors": 64,
            "linear_network_equivalence": "PASS",
            "one_column_cnot": rowxor_count,
            "two_column_cnot": 2 * rowxor_count,
        },
        "scope": (
            "Local component cleanup/equivalence only; this does not certify "
            "complete full-circuit live-ancilla cleanup or physical routing."
        ),
    }
    outdir = ROOT / "outputs" / "fullround_validation"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "local_component_cleanup.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
