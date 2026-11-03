#!/usr/bin/env python3
"""
Exact logical reversible compiler for Kalyna-128/128 and Kalyna-128/256.

This module is intentionally independent of the older ProjectQ depth-estimator
scripts in the repository.  It compiles the *functional* Kalyna key schedule
and encryption into a reversible X/CNOT/CCNOT gate tape, retaining intermediate
out-of-place S-box state as Bennett garbage until the complete phase oracle is
uncomputed.

Design goals
------------
1. Preserve the exact DSTU 7624 / pinned-reference key schedule, including:
   * the K_t initial constant,
   * the selected/rotated master-key words used for even round keys,
   * the tmv constants in KeyExpandEven,
   * the 56-bit odd-round-key rotation.
2. Keep every nonlinear/state-history register that is required for exact
   reversibility.  No width number silently assumes those registers vanish.
3. Compile a clean known-plaintext phase oracle:
       key schedule -> r encryptions -> equality phase -> inverse encryptions
       -> inverse key schedule.
   Because the inverse is the exact gate reversal, every work qubit returns to
   |0> for every computational-basis input, and therefore coherently for an
   arbitrary key superposition.
4. Supply a compact classical simulator for basis-state verification against
   the pinned independent C reference implementation.

The compiler uses out-of-place ANF S-boxes because that is the construction
underlying the manuscript's shared-monomial CCNOT counts.  This keeps the
non-Clifford accounting consistent, but it exposes the true retained-garbage
width of that construction.  The resulting phase oracle is clean globally
after forward-mark-inverse uncomputation; it is not an in-place S-box claim.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
import math
from typing import Iterable, Sequence


# ---------------------------------------------------------------------------
# Kalyna substitution tables (DSTU 7624; copied from the pinned reference).
# ---------------------------------------------------------------------------

PI0_HEX = """
A8 43 5F 06 6B 75 6C 59 71 DF 87 95 17 F0 D8 09
6D F3 1D CB C9 4D 2C AF 79 E0 97 FD 6F 4B 45 39
3E DD A3 4F B4 B6 9A 0E 1F BF 15 E1 49 D2 93 C6
92 72 9E 61 D1 63 FA EE F4 19 D5 AD 58 A4 BB A1
DC F2 83 37 42 E4 7A 32 9C CC AB 4A 8F 6E 04 27
2E E7 E2 5A 96 16 23 2B C2 65 66 0F BC A9 47 41
34 48 FC B7 6A 88 A5 53 86 F9 5B DB 38 7B C3 1E
22 33 24 28 36 C7 B2 3B 8E 77 BA F5 14 9F 08 55
9B 4C FE 60 5C DA 18 46 CD 7D 21 B0 3F 1B 89 FF
EB 84 69 3A 9D D7 D3 70 67 40 B5 DE 5D 30 91 B1
78 11 01 E5 00 68 98 A0 C5 02 A6 74 2D 0B A2 76
B3 BE CE BD AE E9 8A 31 1C EC F1 99 94 AA F6 26
2F EF E8 8C 35 03 D4 7F FB 05 C1 5E 90 20 3D 82
F7 EA 0A 0D 7E F8 50 1A C4 07 57 B8 3C 62 E3 C8
AC 52 64 10 D0 D9 13 0C 12 29 51 B9 CF D6 73 8D
81 54 C0 ED 4E 44 A7 2A 85 25 E6 CA 7C 8B 56 80
"""

PI1_HEX = """
CE BB EB 92 EA CB 13 C1 E9 3A D6 B2 D2 90 17 F8
42 15 56 B4 65 1C 88 43 C5 5C 36 BA F5 57 67 8D
31 F6 64 58 9E F4 22 AA 75 0F 02 B1 DF 6D 73 4D
7C 26 2E F7 08 5D 44 3E 9F 14 C8 AE 54 10 D8 BC
1A 6B 69 F3 BD 33 AB FA D1 9B 68 4E 16 95 91 EE
4C 63 8E 5B CC 3C 19 A1 81 49 7B D9 6F 37 60 CA
E7 2B 48 FD 96 45 FC 41 12 0D 79 E5 89 8C E3 20
30 DC B7 6C 4A B5 3F 97 D4 62 2D 06 A4 A5 83 5F
2A DA C9 00 7E A2 55 BF 11 D5 9C CF 0E 0A 3D 51
7D 93 1B FE C4 47 09 86 0B 8F 9D 6A 07 B9 B0 98
18 32 71 4B EF 3B 70 A0 E4 40 FF C3 A9 E6 78 F9
8B 46 80 1E 38 E1 B8 A8 E0 0C 23 76 1D 25 24 05
F1 6E 94 28 9A 84 E8 A3 4F 77 D3 85 E2 52 F2 82
50 7A 2F 74 53 B3 61 AF 39 35 DE CD 1F 99 AC AD
72 2C DD D0 87 BE 5E A6 EC 04 C6 03 34 FB DB 59
B6 C2 01 F0 5A ED A7 66 21 7F 8A 27 C7 C0 29 D7
"""

PI2_HEX = """
93 D9 9A B5 98 22 45 FC BA 6A DF 02 9F DC 51 59
4A 17 2B C2 94 F4 BB A3 62 E4 71 D4 CD 70 16 E1
49 3C C0 D8 5C 9B AD 85 53 A1 7A C8 2D E0 D1 72
A6 2C C4 E3 76 78 B7 B4 09 3B 0E 41 4C DE B2 90
25 A5 D7 03 11 00 C3 2E 92 EF 4E 12 9D 7D CB 35
10 D5 4F 9E 4D A9 55 C6 D0 7B 18 97 D3 36 E6 48
56 81 8F 77 CC 9C B9 E2 AC B8 2F 15 A4 7C DA 38
1E 0B 05 D6 14 6E 6C 7E 66 FD B1 E5 60 AF 5E 33
87 C9 F0 5D 6D 3F 88 8D C7 F7 1D E9 EC ED 80 29
27 CF 99 A8 50 0F 37 24 28 30 95 D2 3E 5B 40 83
B3 69 57 1F 07 1C 8A BC 20 EB CE 8E AB EE 31 A2
73 F9 CA 3A 1A FB 0D C1 FE FA F2 6F BD 96 DD 43
52 B6 08 F3 AE BE 19 89 32 26 B0 EA 4B 64 84 82
6B F5 79 BF 01 5F 75 63 1B 23 3D 68 2A 65 E8 91
F6 FF 13 58 F1 47 0A 7F C5 A7 E7 61 5A 06 46 44
42 04 A0 DB 39 86 54 AA 8C 34 21 8B F8 0C 74 67
"""

PI3_HEX = """
68 8D CA 4D 73 4B 4E 2A D4 52 26 B3 54 1E 19 1F
22 03 46 3D 2D 4A 53 83 13 8A B7 D5 25 79 F5 BD
58 2F 0D 02 ED 51 9E 11 F2 3E 55 5E D1 16 3C 66
70 5D F3 45 40 CC E8 94 56 08 CE 1A 3A D2 E1 DF
B5 38 6E 0E E5 F4 F9 86 E9 4F D6 85 23 CF 32 99
31 14 AE EE C8 48 D3 30 A1 92 41 B1 18 C4 2C 71
72 44 15 FD 37 BE 5F AA 9B 88 D8 AB 89 9C FA 60
EA BC 62 0C 24 A6 A8 EC 67 20 DB 7C 28 DD AC 5B
34 7E 10 F1 7B 8F 63 A0 05 9A 43 77 21 BF 27 09
C3 9F B6 D7 29 C2 EB C0 A4 8B 8C 1D FB FF C1 B2
97 2E F8 65 F6 75 07 04 49 33 E4 D9 B9 D0 42 C7
6C 90 00 8E 6F 50 01 C5 DA 47 3F CD 69 A2 E2 7A
A7 C6 93 0F 0A 06 E6 2B 96 A3 1C AF 6A 12 84 39
E7 B0 82 F7 FE 9D 87 5C 81 35 DE B4 A5 FC 80 EF
CB BB 6B 76 BA 5A 7D 78 0B 95 E3 AD 74 98 3B 36
64 6D DC F0 59 A9 4C 17 7F 91 B8 C9 57 1B E0 61
"""


def _parse_sbox(text: str) -> tuple[int, ...]:
    vals = tuple(int(x, 16) for x in text.split())
    if len(vals) != 256:
        raise AssertionError("invalid Kalyna S-box table")
    return vals


PI = tuple(_parse_sbox(x) for x in (PI0_HEX, PI1_HEX, PI2_HEX, PI3_HEX))


# ---------------------------------------------------------------------------
# Compact reversible gate tape.
# ---------------------------------------------------------------------------

XG = 1
CXG = 2
CCXG = 3
CCZG = 4  # phase-only three-wire gate; counted as one CCX equivalent


@dataclass
class Register:
    wires: list[int]
    label: str


class GateTape:
    """Reversible gate tape with recyclable clean workspace wires."""

    def __init__(self) -> None:
        self.gates: list[tuple[int, int, int, int]] = []
        self.counts = Counter()
        self.depth: list[int] = []
        self.max_depth = 0

        self._next_wire = 0
        self._free_pool: list[int] = []
        self._live: set[int] = set()
        self.peak_live = 0
        self.allocations: list[dict] = []
        self.frees: list[dict] = []

    @property
    def physical_width(self) -> int:
        return self._next_wire

    @property
    def live_width(self) -> int:
        return len(self._live)

    def alloc(self, n: int, label: str) -> Register:
        wires: list[int] = []
        for _ in range(n):
            if self._free_pool:
                q = self._free_pool.pop()
            else:
                q = self._next_wire
                self._next_wire += 1
                self.depth.append(0)
            if q in self._live:
                raise AssertionError("allocator reused a live wire")
            self._live.add(q)
            wires.append(q)
        self.peak_live = max(self.peak_live, len(self._live))
        self.allocations.append(
            {"label": label, "size": n, "gate_index": len(self.gates), "live_after": len(self._live)}
        )
        return Register(wires, label)

    def free_clean(self, reg: Register, reason: str) -> None:
        for q in reg.wires:
            if q not in self._live:
                raise AssertionError(f"double free or unknown wire in {reg.label}")
            self._live.remove(q)
            self._free_pool.append(q)
        self.frees.append(
            {
                "label": reg.label,
                "size": len(reg.wires),
                "gate_index": len(self.gates),
                "live_after": len(self._live),
                "reason": reason,
            }
        )

    def _touch_depth(self, wires: Sequence[int]) -> None:
        start = max((self.depth[q] for q in wires), default=0)
        d = start + 1
        for q in wires:
            self.depth[q] = d
        self.max_depth = max(self.max_depth, d)

    def x(self, q: int) -> None:
        self.gates.append((XG, q, -1, -1))
        self.counts["X"] += 1
        self._touch_depth((q,))

    def cx(self, c: int, t: int) -> None:
        self.gates.append((CXG, c, t, -1))
        self.counts["CNOT"] += 1
        self._touch_depth((c, t))

    def ccx(self, a: int, b: int, t: int) -> None:
        self.gates.append((CCXG, a, b, t))
        self.counts["CCX"] += 1
        self._touch_depth((a, b, t))

    def ccz(self, a: int, b: int, c: int) -> None:
        # Phase-only; for logical accounting one CCZ is one CCX-equivalent
        # under H-target / CCX / H.
        self.gates.append((CCZG, a, b, c))
        self.counts["CCZ"] += 1
        self._touch_depth((a, b, c))

    def hash_gate_slice(self, start: int = 0, end: int | None = None) -> str:
        if end is None:
            end = len(self.gates)
        h = hashlib.sha256()
        for g in self.gates[start:end]:
            h.update(("%d,%d,%d,%d;" % g).encode())
        return h.hexdigest()

    def summary(self) -> dict:
        return {
            "X": self.counts["X"],
            "CNOT": self.counts["CNOT"],
            "CCX": self.counts["CCX"],
            "CCZ": self.counts["CCZ"],
            "total_recorded_gates": len(self.gates),
            "dependency_depth": self.max_depth,
            "physical_width": self.physical_width,
            "peak_live_width": self.peak_live,
        }


# ---------------------------------------------------------------------------
# Basis-state tape simulator.
# ---------------------------------------------------------------------------


def _apply_gate(bits: bytearray, gate: tuple[int, int, int, int]) -> int:
    typ, a, b, c = gate
    if typ == XG:
        bits[a] ^= 1
        return 0
    if typ == CXG:
        if bits[a]:
            bits[b] ^= 1
        return 0
    if typ == CCXG:
        if bits[a] and bits[b]:
            bits[c] ^= 1
        return 0
    if typ == CCZG:
        return 1 if (bits[a] and bits[b] and bits[c]) else 0
    raise ValueError(f"unknown gate type {typ}")


def simulate_forward(bits: bytearray, gates: Sequence[tuple[int, int, int, int]]) -> int:
    phase = 0
    for g in gates:
        phase ^= _apply_gate(bits, g)
    return phase


def simulate_reverse(bits: bytearray, gates: Sequence[tuple[int, int, int, int]]) -> int:
    phase = 0
    for g in reversed(gates):
        phase ^= _apply_gate(bits, g)
    return phase


# ---------------------------------------------------------------------------
# Bit/byte helpers.
# ---------------------------------------------------------------------------


def byte_index(row: int, col: int) -> int:
    return 8 * (8 * col + row)


def get_byte(state: Sequence[int], row: int, col: int) -> list[int]:
    p = byte_index(row, col)
    return list(state[p:p + 8])


def set_byte(state: list[int], row: int, col: int, value: Sequence[int]) -> None:
    p = byte_index(row, col)
    state[p:p + 8] = list(value)


def get_column64(state: Sequence[int], col: int) -> list[int]:
    out: list[int] = []
    for row in range(8):
        out.extend(get_byte(state, row, col))
    return out


def set_column64(state: list[int], col: int, value: Sequence[int]) -> None:
    for row in range(8):
        set_byte(state, row, col, value[8 * row:8 * row + 8])


def wires_to_bytes(bits: bytearray, wires: Sequence[int]) -> bytes:
    if len(wires) % 8:
        raise ValueError("wire count is not byte aligned")
    out = bytearray(len(wires) // 8)
    for i in range(len(out)):
        v = 0
        for j in range(8):
            v |= (bits[wires[8 * i + j]] & 1) << j
        out[i] = v
    return bytes(out)


def load_bytes(bits: bytearray, wires: Sequence[int], data: bytes) -> None:
    if len(wires) != 8 * len(data):
        raise ValueError("input length mismatch")
    for i, value in enumerate(data):
        for j in range(8):
            bits[wires[8 * i + j]] = (value >> j) & 1


def hex_to_bytes_exact(text: str, nbytes: int) -> bytes:
    data = bytes.fromhex(text)
    if len(data) != nbytes:
        raise ValueError(f"expected {nbytes} bytes, got {len(data)}")
    return data


# ---------------------------------------------------------------------------
# ANF S-box compiler.
# ---------------------------------------------------------------------------


def anf_coefficients_for_bit(sbox: Sequence[int], out_bit: int) -> tuple[int, ...]:
    a = [((sbox[x] >> out_bit) & 1) for x in range(256)]
    for i in range(8):
        step = 1 << i
        for mask in range(256):
            if mask & step:
                a[mask] ^= a[mask ^ step]
    return tuple(mask for mask, coeff in enumerate(a) if coeff)


@lru_cache(maxsize=None)
def cached_anf(sbox_id: int, out_bit: int) -> tuple[int, ...]:
    return anf_coefficients_for_bit(PI[sbox_id], out_bit)


def monomial_degree(mask: int) -> int:
    return mask.bit_count()


@lru_cache(maxsize=None)
def sbox_occurrences(sbox_id: int) -> tuple[tuple[int, tuple[int, ...]], ...]:
    occ: dict[int, list[int]] = defaultdict(list)
    for out_bit in range(8):
        for mask in cached_anf(sbox_id, out_bit):
            occ[mask].append(out_bit)
    return tuple(
        (mask, tuple(outs))
        for mask, outs in sorted(occ.items(), key=lambda kv: (monomial_degree(kv[0]), kv[0]))
    )


def direct_ccx_cost(mask: int) -> int:
    d = monomial_degree(mask)
    if d <= 1:
        return 0
    if d == 2:
        return 1
    return 2 * d - 3


def shared_ccx_cost(mask: int) -> int:
    d = monomial_degree(mask)
    if d < 2:
        raise ValueError("nonlinear mask required")
    return 2 * d - 2


def should_share(mask: int, occurrences: int) -> bool:
    if monomial_degree(mask) < 2:
        return False
    return shared_ccx_cost(mask) < occurrences * direct_ccx_cost(mask)


def monomial_xor_direct(t: GateTape, controls: Sequence[int], target: int, label: str) -> None:
    d = len(controls)
    if d == 0:
        t.x(target)
    elif d == 1:
        t.cx(controls[0], target)
    elif d == 2:
        t.ccx(controls[0], controls[1], target)
    else:
        tmp = t.alloc(d - 2, label + "/direct_tmp")
        t.ccx(controls[0], controls[1], tmp.wires[0])
        for i in range(2, d - 1):
            t.ccx(tmp.wires[i - 2], controls[i], tmp.wires[i - 1])
        t.ccx(tmp.wires[d - 3], controls[d - 1], target)
        for i in reversed(range(2, d - 1)):
            t.ccx(tmp.wires[i - 2], controls[i], tmp.wires[i - 1])
        t.ccx(controls[0], controls[1], tmp.wires[0])
        t.free_clean(tmp, "direct monomial compute/uncompute")


def shared_monomial_xor(
    t: GateTape, controls: Sequence[int], targets: Sequence[int], label: str
) -> None:
    d = len(controls)
    tmp = t.alloc(d - 1, label + "/shared_tmp")
    t.ccx(controls[0], controls[1], tmp.wires[0])
    for i in range(2, d):
        t.ccx(tmp.wires[i - 2], controls[i], tmp.wires[i - 1])
    prod = tmp.wires[-1]
    for target in targets:
        t.cx(prod, target)
    for i in reversed(range(2, d)):
        t.ccx(tmp.wires[i - 2], controls[i], tmp.wires[i - 1])
    t.ccx(controls[0], controls[1], tmp.wires[0])
    t.free_clean(tmp, "shared monomial compute/copy/uncompute")


def sbox_to_fresh(
    t: GateTape, byte8: Sequence[int], sbox_id: int, label: str
) -> Register:
    out = t.alloc(8, label + "/out")
    for mask, outs in sbox_occurrences(sbox_id):
        d = monomial_degree(mask)
        if d == 0:
            for ob in outs:
                t.x(out.wires[ob])
        elif d == 1:
            src = next(i for i in range(8) if (mask >> i) & 1)
            for ob in outs:
                t.cx(byte8[src], out.wires[ob])
        else:
            controls = [byte8[i] for i in range(8) if (mask >> i) & 1]
            if should_share(mask, len(outs)):
                shared_monomial_xor(
                    t, controls, [out.wires[ob] for ob in outs], label + f"/m{mask:02x}"
                )
            else:
                for ob in outs:
                    monomial_xor_direct(
                        t, controls, out.wires[ob], label + f"/m{mask:02x}/o{ob}"
                    )
    return out


def subbytes_128_to_fresh(t: GateTape, state: Sequence[int], label: str) -> list[int]:
    out: list[int | None] = [None] * 128
    for col in range(2):
        for row in range(8):
            b = get_byte(state, row, col)
            sb = sbox_to_fresh(t, b, row % 4, f"{label}/c{col}r{row}")
            set_byte(out, row, col, sb.wires)
    if any(x is None for x in out):
        raise AssertionError("incomplete S-box output")
    return [int(x) for x in out]


# ---------------------------------------------------------------------------
# ShiftRows and MixColumns.
# ---------------------------------------------------------------------------

GF_POLY_LOW = 0x1D
KALYNA_V = (0x01, 0x01, 0x05, 0x01, 0x08, 0x06, 0x07, 0x04)


def gf_mul(a: int, b: int) -> int:
    res = 0
    aa = a & 0xFF
    bb = b & 0xFF
    for _ in range(8):
        if bb & 1:
            res ^= aa
        carry = aa & 0x80
        aa = (aa << 1) & 0xFF
        if carry:
            aa ^= GF_POLY_LOW
        bb >>= 1
    return res & 0xFF


def _bits_to_byte(v: Sequence[int]) -> int:
    return sum((v[i] & 1) << i for i in range(8))


def _byte_to_bits(x: int) -> list[int]:
    return [(x >> i) & 1 for i in range(8)]


def mix_column_bytes(col: Sequence[int]) -> list[int]:
    out: list[int] = []
    for i in range(8):
        acc = 0
        for j in range(8):
            acc ^= gf_mul(KALYNA_V[(j - i) % 8], col[j])
        out.append(acc)
    return out


def _mixcol_rows_as_ints() -> list[int]:
    rows = [0] * 64
    for input_bit in range(64):
        bits = [0] * 64
        bits[input_bit] = 1
        col = [_bits_to_byte(bits[8*r:8*r+8]) for r in range(8)]
        out = mix_column_bytes(col)
        out_bits: list[int] = []
        for b in out:
            out_bits.extend(_byte_to_bits(b))
        for r, value in enumerate(out_bits):
            if value:
                rows[r] |= 1 << input_bit
    return rows


@lru_cache(maxsize=1)
def mixcol_ops() -> tuple[tuple[str, int, int], ...]:
    rows = _mixcol_rows_as_ints()
    n = 64
    ops: list[tuple[str, int, int]] = []
    for p in range(n):
        piv = next((r for r in range(p, n) if (rows[r] >> p) & 1), None)
        if piv is None:
            raise AssertionError("singular Kalyna MDS matrix")
        if piv != p:
            rows[p], rows[piv] = rows[piv], rows[p]
            ops.append(("swap", p, piv))
        for r in range(n):
            if r != p and ((rows[r] >> p) & 1):
                rows[r] ^= rows[p]
                ops.append(("rowxor", p, r))
    if rows != [1 << i for i in range(64)]:
        raise AssertionError("MDS reduction failed")
    return tuple(ops)


def shiftrows_128(state: Sequence[int]) -> list[int]:
    out: list[int | None] = [None] * 128
    for row in range(8):
        shift = row // 4
        for col in range(2):
            src_col = (col - shift) % 2
            set_byte(out, row, col, get_byte(state, row, src_col))
    return [int(x) for x in out]


def mixcolumns_128(t: GateTape, state: Sequence[int]) -> list[int]:
    q = list(state)
    ops = mixcol_ops()
    for col in range(2):
        c = get_column64(q, col)
        # Reversed row-reduction operations implement the forward map.
        for kind, a, b in reversed(ops):
            if kind == "swap":
                c[a], c[b] = c[b], c[a]
            else:
                t.cx(c[a], c[b])
        set_column64(q, col, c)
    return q


def pi_tau_psi(t: GateTape, state: Sequence[int], label: str) -> list[int]:
    s = subbytes_128_to_fresh(t, state, label + "/pi")
    s = shiftrows_128(s)
    s = mixcolumns_128(t, s)
    return s


# ---------------------------------------------------------------------------
# AddRoundKey layers.
# ---------------------------------------------------------------------------


def maj(t: GateTape, a: int, b: int, c: int) -> None:
    t.cx(a, b)
    t.cx(a, c)
    t.ccx(b, c, a)


def uma(t: GateTape, a: int, b: int, c: int) -> None:
    t.ccx(b, c, a)
    t.cx(a, c)
    t.cx(c, b)


def add_mod_2n_inplace(
    t: GateTape, addend: Sequence[int], target: Sequence[int], label: str
) -> None:
    if len(addend) != len(target):
        raise ValueError("adder width mismatch")
    n = len(addend)
    carry = t.alloc(1, label + "/carry")
    c = carry.wires[0]
    maj(t, addend[0], target[0], c)
    for i in range(1, n):
        maj(t, addend[i], target[i], addend[i - 1])
    for i in reversed(range(1, n)):
        uma(t, addend[i], target[i], addend[i - 1])
    uma(t, addend[0], target[0], c)
    t.free_clean(carry, "Cuccaro carry restored by UMA sweep")


def eta_add(t: GateTape, state: Sequence[int], key: Sequence[int], label: str) -> list[int]:
    s = list(state)
    for col in range(2):
        add_mod_2n_inplace(
            t, get_column64(key, col), get_column64(s, col), f"{label}/col{col}"
        )
    return s


def kappa_xor(t: GateTape, state: Sequence[int], key: Sequence[int]) -> list[int]:
    s = list(state)
    for a, b in zip(key, s):
        t.cx(a, b)
    return s


def prepare_constant(t: GateTape, nbits: int, value: int, label: str) -> Register:
    r = t.alloc(nbits, label)
    for i in range(nbits):
        if (value >> i) & 1:
            t.x(r.wires[i])
    return r


def unprepare_constant(t: GateTape, reg: Register, value: int) -> None:
    for i in range(len(reg.wires)):
        if (value >> i) & 1:
            t.x(reg.wires[i])
    t.free_clean(reg, "known classical constant unprepared")


def add_same_const_to_two_words(
    t: GateTape, target128: Sequence[int], const64: int, label: str
) -> None:
    c = prepare_constant(t, 64, const64 & ((1 << 64) - 1), label + "/const")
    add_mod_2n_inplace(t, c.wires, target128[:64], label + "/word0")
    add_mod_2n_inplace(t, c.wires, target128[64:], label + "/word1")
    unprepare_constant(t, c, const64 & ((1 << 64) - 1))


def copy_bits(t: GateTape, src: Sequence[int], dst: Sequence[int]) -> None:
    if len(src) != len(dst):
        raise ValueError("copy width mismatch")
    for a, b in zip(src, dst):
        t.cx(a, b)


def prepare_phi(
    t: GateTape, kt: Sequence[int], tmv64: int, label: str
) -> list[int]:
    """Prepare phi = kt + (tmv, tmv) in a fresh 128-bit register."""
    phi = t.alloc(128, label + "/phi")
    copy_bits(t, kt, phi.wires)
    add_same_const_to_two_words(t, phi.wires, tmv64, label + "/tmv")
    # phi is retained as schedule garbage.  It is globally cleaned by the
    # exact inverse of the whole key schedule after oracle phase marking.
    return phi.wires


# ---------------------------------------------------------------------------
# Exact key schedule.
# ---------------------------------------------------------------------------


@dataclass
class KeyScheduleResult:
    round_keys: list[list[int]]
    kt: list[int]
    history_labels: list[str]


def _word_view(bits: Sequence[int]) -> list[list[int]]:
    if len(bits) % 64:
        raise ValueError("word alignment")
    return [list(bits[64*i:64*(i+1)]) for i in range(len(bits)//64)]


def _flatten(words: Sequence[Sequence[int]]) -> list[int]:
    return [q for w in words for q in w]


def rotate_words_left(words: Sequence[Sequence[int]], amount: int = 1) -> list[list[int]]:
    w = [list(x) for x in words]
    amount %= len(w)
    return w[amount:] + w[:amount]


def rotate_bytes_left_128(bits: Sequence[int], nbytes: int) -> list[int]:
    if len(bits) != 128:
        raise ValueError("expected 128-bit round key")
    shift = (8 * nbytes) % 128
    return list(bits[shift:]) + list(bits[:shift])


def key_expand_kt(
    t: GateTape, master: Sequence[int], key_bits: int, label: str
) -> list[int]:
    nb = 2
    nk = key_bits // 64
    words = _word_view(master)
    k0 = _flatten(words[:2])
    k1 = k0 if nk == nb else _flatten(words[2:4])

    state_reg = t.alloc(128, label + "/state0")
    state = state_reg.wires

    # Reference: state[0] += nb + nk + 1.
    initial_const = nb + nk + 1
    for i in range(64):
        if (initial_const >> i) & 1:
            t.x(state[i])

    state = eta_add(t, state, k0, label + "/eta0")
    state = pi_tau_psi(t, state, label + "/E0")
    state = kappa_xor(t, state, k1)
    state = pi_tau_psi(t, state, label + "/E1")
    state = eta_add(t, state, k0, label + "/eta1")
    state = pi_tau_psi(t, state, label + "/E2")
    return state


def generate_even_round_key(
    t: GateTape,
    selected_master_word128: Sequence[int],
    kt: Sequence[int],
    tmv64: int,
    round_index: int,
    label: str,
) -> list[int]:
    phi = prepare_phi(t, kt, tmv64, label + f"/K{round_index}")

    # Exact quantum copy of initial_data into the fresh state.
    state_reg = t.alloc(128, label + f"/K{round_index}/state0")
    copy_bits(t, selected_master_word128, state_reg.wires)
    state = state_reg.wires

    state = eta_add(t, state, phi, label + f"/K{round_index}/eta0")
    state = pi_tau_psi(t, state, label + f"/K{round_index}/E0")
    state = kappa_xor(t, state, phi)
    state = pi_tau_psi(t, state, label + f"/K{round_index}/E1")
    state = eta_add(t, state, phi, label + f"/K{round_index}/eta1")
    return state


def key_schedule(
    t: GateTape, master: Sequence[int], key_bits: int, label: str = "KS"
) -> KeyScheduleResult:
    if key_bits not in (128, 256):
        raise ValueError("only Kalyna-128/128 and Kalyna-128/256 are supported")
    nr = 10 if key_bits == 128 else 14
    kt = key_expand_kt(t, master, key_bits, label + "/Kt")

    initial_words = _word_view(master)
    tmv = 0x0001000100010001
    roundkeys: list[list[int] | None] = [None] * (nr + 1)
    round_index = 0

    while True:
        selected = _flatten(initial_words[:2])
        rk = generate_even_round_key(
            t, selected, kt, tmv, round_index, label + "/Even"
        )
        roundkeys[round_index] = rk

        if nr == round_index:
            break

        if key_bits == 256:
            round_index += 2
            tmv = (tmv << 1) & ((1 << 64) - 1)
            selected = _flatten(initial_words[2:4])
            rk = generate_even_round_key(
                t, selected, kt, tmv, round_index, label + "/Even"
            )
            roundkeys[round_index] = rk
            if nr == round_index:
                break

        round_index += 2
        tmv = (tmv << 1) & ((1 << 64) - 1)
        initial_words = rotate_words_left(initial_words, 1)

    # Odd round keys are byte rotations of the previous even key.  They are
    # logical aliases, not copied registers.
    for i in range(1, nr, 2):
        even = roundkeys[i - 1]
        if even is None:
            raise AssertionError("missing even round key")
        roundkeys[i] = rotate_bytes_left_128(even, 7)

    out = [rk for rk in roundkeys if rk is not None]
    if len(out) != nr + 1:
        raise AssertionError("incomplete round-key schedule")
    return KeyScheduleResult(out, kt, [])


# ---------------------------------------------------------------------------
# Encryption core.
# ---------------------------------------------------------------------------


def encipher_round(t: GateTape, state: Sequence[int], label: str) -> list[int]:
    return pi_tau_psi(t, state, label)


def encryption_core(
    t: GateTape, plaintext: Sequence[int], roundkeys: Sequence[Sequence[int]], label: str
) -> list[int]:
    nr = len(roundkeys) - 1
    state = eta_add(t, plaintext, roundkeys[0], label + "/ARK0")
    for r in range(1, nr):
        state = encipher_round(t, state, label + f"/R{r}")
        state = kappa_xor(t, state, roundkeys[r])
    state = encipher_round(t, state, label + f"/R{nr}")
    state = eta_add(t, state, roundkeys[nr], label + f"/ARK{nr}")
    return state


@dataclass
class CipherProgram:
    tape: GateTape
    key_bits: int
    master: Register
    plaintext: Register
    ciphertext: list[int]
    round_keys: list[list[int]]
    forward_gate_count: int


def compile_cipher(key_bits: int) -> CipherProgram:
    t = GateTape()
    master = t.alloc(key_bits, "master_key")
    plaintext = t.alloc(128, "plaintext")
    ks = key_schedule(t, master.wires, key_bits)
    ciphertext = encryption_core(t, plaintext.wires, ks.round_keys, "ENC")
    return CipherProgram(
        tape=t,
        key_bits=key_bits,
        master=master,
        plaintext=plaintext,
        ciphertext=ciphertext,
        round_keys=ks.round_keys,
        forward_gate_count=len(t.gates),
    )


# ---------------------------------------------------------------------------
# Equality phase marker and full known-plaintext oracle accounting.
# ---------------------------------------------------------------------------


def normalize_to_one(t: GateTape, wires: Sequence[int], target: bytes) -> None:
    if len(wires) != 8 * len(target):
        raise ValueError("target size mismatch")
    for i, byte in enumerate(target):
        for j in range(8):
            if ((byte >> j) & 1) == 0:
                t.x(wires[8*i + j])


def joint_equality_phase(
    t: GateTape,
    ciphertexts: Sequence[Sequence[int]],
    targets: Sequence[bytes],
    label: str = "EQ",
) -> dict:
    if len(ciphertexts) != len(targets):
        raise ValueError("pair count mismatch")
    wires: list[int] = []
    for ct, target in zip(ciphertexts, targets):
        normalize_to_one(t, ct, target)
        wires.extend(ct)

    m = len(wires)
    if m < 3:
        raise ValueError("need at least three equality bits")

    # Compute AND of first m-2 equality bits into m-3 clean ancillas,
    # apply CCZ with the final two data bits, and uncompute.
    anc = t.alloc(m - 3, label + "/and_chain")
    if m - 2 == 1:
        raise AssertionError("unreachable for Kalyna")
    t.ccx(wires[0], wires[1], anc.wires[0])
    for i in range(2, m - 2):
        t.ccx(anc.wires[i - 2], wires[i], anc.wires[i - 1])
    root = anc.wires[m - 4]
    t.ccz(root, wires[m - 2], wires[m - 1])
    for i in reversed(range(2, m - 2)):
        t.ccx(anc.wires[i - 2], wires[i], anc.wires[i - 1])
    t.ccx(wires[0], wires[1], anc.wires[0])
    t.free_clean(anc, "equality AND tree/chain uncomputed")

    # Undo target normalization.
    for ct, target in reversed(list(zip(ciphertexts, targets))):
        normalize_to_one(t, ct, target)

    return {"condition_bits": m, "ccx_equiv": 2 * m - 5}


@dataclass
class OracleProgram:
    tape: GateTape
    key_bits: int
    pair_count: int
    master: Register
    plaintext_regs: list[Register]
    ciphertexts: list[list[int]]
    targets: list[bytes]
    forward_end: int
    mark_start: int
    mark_end: int


def compile_phase_oracle(
    key_bits: int,
    plaintexts: Sequence[bytes],
    targets: Sequence[bytes],
) -> OracleProgram:
    if len(plaintexts) != len(targets):
        raise ValueError("pair count mismatch")
    expected_pairs = 2 if key_bits == 128 else 3
    if len(plaintexts) != expected_pairs:
        raise ValueError(
            f"historical-key baseline for {key_bits}-bit key uses {expected_pairs} pairs"
        )

    t = GateTape()
    master = t.alloc(key_bits, "master_key")
    ks = key_schedule(t, master.wires, key_bits, "KS")

    p_regs: list[Register] = []
    ciphertexts: list[list[int]] = []
    for i, p in enumerate(plaintexts):
        preg = t.alloc(128, f"pair{i}/plaintext")
        load_bits = p
        for bi, byte in enumerate(load_bits):
            for j in range(8):
                if (byte >> j) & 1:
                    t.x(preg.wires[8*bi + j])
        p_regs.append(preg)
        ciphertexts.append(
            encryption_core(t, preg.wires, ks.round_keys, f"pair{i}/ENC")
        )

    forward_end = len(t.gates)
    mark_start = forward_end
    joint_equality_phase(t, ciphertexts, targets, "JOINT_EQ")
    mark_end = len(t.gates)

    # We do not append the inverse copy: the certificate records that the
    # oracle executes gates[0:forward_end], then the clean equality marker,
    # then the exact reverse of gates[0:forward_end].  This avoids doubling the
    # stored tape while retaining an exact gate-level inverse definition.
    return OracleProgram(
        tape=t,
        key_bits=key_bits,
        pair_count=len(plaintexts),
        master=master,
        plaintext_regs=p_regs,
        ciphertexts=ciphertexts,
        targets=list(targets),
        forward_end=forward_end,
        mark_start=mark_start,
        mark_end=mark_end,
    )


def _dependency_depth_for_oracle(program: OracleProgram) -> int:
    """Dependency depth of forward -> mark -> exact reverse-forward.

    This is the depth of the concrete emitted logical schedule under unlimited
    connectivity and unit depth for X/CNOT/CCNOT/CCZ. It is a schedule-specific
    upper bound, not an optimized-depth claim.
    """
    width = program.tape.physical_width
    depths = [0] * width
    max_depth = 0

    def apply(gate):
        nonlocal max_depth
        typ, a, b, c = gate
        if typ == XG:
            wires = (a,)
        elif typ == CXG:
            wires = (a, b)
        elif typ in (CCXG, CCZG):
            wires = (a, b, c)
        else:
            raise ValueError(f"unknown gate type {typ}")
        d = max(depths[q] for q in wires) + 1
        for q in wires:
            depths[q] = d
        if d > max_depth:
            max_depth = d

    for g in program.tape.gates[: program.forward_end]:
        apply(g)
    for g in program.tape.gates[program.mark_start : program.mark_end]:
        apply(g)
    for g in reversed(program.tape.gates[: program.forward_end]):
        apply(g)
    return max_depth


def oracle_resource_summary(program: OracleProgram) -> dict:
    t = program.tape
    f = Counter()
    for typ, *_ in t.gates[: program.forward_end]:
        if typ == XG:
            f["X"] += 1
        elif typ == CXG:
            f["CNOT"] += 1
        elif typ == CCXG:
            f["CCX"] += 1
        elif typ == CCZG:
            f["CCZ"] += 1

    m = Counter()
    for typ, *_ in t.gates[program.mark_start : program.mark_end]:
        if typ == XG:
            m["X"] += 1
        elif typ == CXG:
            m["CNOT"] += 1
        elif typ == CCXG:
            m["CCX"] += 1
        elif typ == CCZG:
            m["CCZ"] += 1

    total = {
        "X": 2 * f["X"] + m["X"],
        "CNOT": 2 * f["CNOT"] + m["CNOT"],
        "CCX": 2 * f["CCX"] + m["CCX"],
        "CCZ": m["CCZ"],
    }
    total["CCX_equivalent"] = total["CCX"] + total["CCZ"]
    total["T_7_per_CCX_equivalent"] = 7 * total["CCX_equivalent"]

    return {
        "key_bits": program.key_bits,
        "pairs": program.pair_count,
        "forward": dict(f),
        "mark": dict(m),
        "phase_oracle_compute_mark_uncompute": total,
        "compiled_physical_width": t.physical_width,
        "peak_live_width_during_compilation": t.peak_live,
        "compute_plus_mark_dependency_depth": max(
            (t.depth[q] for q in range(t.physical_width)), default=0
        ),
        "complete_phase_oracle_dependency_depth": _dependency_depth_for_oracle(program),
        "forward_gate_hash": t.hash_gate_slice(0, program.forward_end),
        "mark_gate_hash": t.hash_gate_slice(program.mark_start, program.mark_end),
        "inverse_definition": "exact reverse of forward gate slice",
    }


def diffuser_ccx_equivalent(key_bits: int) -> int:
    return 2 * key_bits - 5


def complete_iteration_nonclifford(program: OracleProgram) -> dict:
    oracle = oracle_resource_summary(program)
    phase_ccx = oracle["phase_oracle_compute_mark_uncompute"]["CCX_equivalent"]
    diff = diffuser_ccx_equivalent(program.key_bits)
    total = phase_ccx + diff
    return {
        **oracle,
        "diffuser_CCX_equivalent": diff,
        "complete_iteration_CCX_equivalent": total,
        "complete_iteration_T_7_per_CCX": 7 * total,
    }


# ---------------------------------------------------------------------------
# Certificate helpers.
# ---------------------------------------------------------------------------


def simulate_cipher_program(
    program: CipherProgram, key: bytes, plaintext: bytes
) -> tuple[bytes, list[bytes], bool]:
    if len(key) * 8 != program.key_bits:
        raise ValueError("key size mismatch")
    if len(plaintext) != 16:
        raise ValueError("plaintext must be 16 bytes")

    bits = bytearray(program.tape.physical_width)
    load_bytes(bits, program.master.wires, key)
    load_bytes(bits, program.plaintext.wires, plaintext)
    initial = bytes(bits)

    phase = simulate_forward(bits, program.tape.gates)
    if phase:
        raise AssertionError("cipher tape contains an unexpected phase gate")

    ct = wires_to_bytes(bits, program.ciphertext)
    rks = [wires_to_bytes(bits, rk) for rk in program.round_keys]

    simulate_reverse(bits, program.tape.gates)
    clean = bytes(bits) == initial
    return ct, rks, clean


def simulate_phase_oracle_basis(
    program: OracleProgram, key: bytes
) -> tuple[bool, bool]:
    """Return (phase_marked, exact_cleanup) for one basis key."""
    if len(key) * 8 != program.key_bits:
        raise ValueError("key size mismatch")
    bits = bytearray(program.tape.physical_width)
    load_bytes(bits, program.master.wires, key)
    initial = bytes(bits)

    # Forward compute.
    phase = simulate_forward(bits, program.tape.gates[: program.forward_end])
    if phase:
        raise AssertionError("forward compute contains phase gate")

    # Mark.
    phase ^= simulate_forward(
        bits, program.tape.gates[program.mark_start : program.mark_end]
    )

    # Exact inverse of forward compute.
    phase ^= simulate_reverse(bits, program.tape.gates[: program.forward_end])
    cleanup = bytes(bits) == initial
    return bool(phase), cleanup


def structural_inverse_certificate(program: OracleProgram) -> dict:
    forward = program.tape.gates[: program.forward_end]
    h_f = hashlib.sha256()
    h_inverse = hashlib.sha256()
    for g in forward:
        h_f.update(("%d,%d,%d,%d;" % g).encode())
    for g in reversed(forward):
        h_inverse.update(("%d,%d,%d,%d;" % g).encode())

    return {
        "forward_gate_count": len(forward),
        "mark_gate_count": program.mark_end - program.mark_start,
        "forward_sha256": h_f.hexdigest(),
        "inverse_sha256": h_inverse.hexdigest(),
        "inverse_gate_count": len(forward),
        "inverse_rule": "reverse gate order; X/CNOT/CCNOT are self-inverse",
        "phase_marker_basis_preserving": True,
        "cleanup_statement": (
            "For every input state, U_f^{-1} M U_f restores every work wire "
            "because M is diagonal/basis-preserving and U_f^{-1} is the exact "
            "gate reversal. Basis-state tests additionally verify the compiled "
            "functional mapping against the pinned independent Kalyna reference."
        ),
    }


def known_pairs(key_bits: int) -> tuple[list[bytes], list[bytes]]:
    if key_bits == 128:
        ps = [
            bytes.fromhex("101112131415161718191A1B1C1D1E1F"),
            bytes.fromhex("000102030405060708090A0B0C0D0E0F"),
        ]
        cs = [
            bytes.fromhex("81BF1C7D779BAC20E1C9EA39B4D2AD06"),
            bytes.fromhex("F0D8A02B550FEEF87CA857BE8BC0B813"),
        ]
    elif key_bits == 256:
        ps = [
            bytes.fromhex("202122232425262728292A2B2C2D2E2F"),
            bytes.fromhex("000102030405060708090A0B0C0D0E0F"),
            bytes.fromhex("101112131415161718191A1B1C1D1E1F"),
        ]
        cs = [
            bytes.fromhex("58EC3E091000158A1148F7166F334F14"),
            bytes.fromhex("0F383F396720B784BC83211C608C9A61"),
            bytes.fromhex("658F1C0E6A8737E8AEAD3156B34074B3"),
        ]
    else:
        raise ValueError(key_bits)
    return ps, cs


def historical_key(key_bits: int) -> bytes:
    if key_bits == 128:
        return bytes(range(0x00, 0x10))
    if key_bits == 256:
        return bytes(range(0x00, 0x20))
    raise ValueError(key_bits)


if __name__ == "__main__":
    # Lightweight self-audit.  Full independent-reference tests are executed
    # by validation/run_full_oracle_certificate.py.
    for kb in (128, 256):
        p = compile_cipher(kb)
        print(
            json.dumps(
                {
                    "variant": f"128/{kb}",
                    "cipher_forward": p.tape.summary(),
                    "gate_hash": p.tape.hash_gate_slice(),
                },
                sort_keys=True,
            )
        )
