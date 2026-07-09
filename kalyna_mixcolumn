import numpy as np

from projectq import MainEngine
from projectq.ops import CNOT
from projectq.backends import ResourceCounter
from projectq.cengines import BasicEngine



class DepthEstimator(BasicEngine):
    def __init__(self):
        super().__init__()
        self.depths = {}
        self.max_depth = 0

    def is_available(self, cmd):
        return True

    def receive(self, command_list):
        ignore_gates = {
            "AllocateQubitGate",
            "DeallocateQubitGate",
            "FlushGate"
        }

        for cmd in command_list:
            gate_name = cmd.gate.__class__.__name__

            if gate_name in ignore_gates:
                continue

            qids = []
            for qureg in cmd.all_qubits:
                for qb in qureg:
                    qids.append(qb.id)

            if not qids:
                continue

            start = max(self.depths.get(qid, 0) for qid in qids)
            new_depth = start + 1

            for qid in qids:
                self.depths[qid] = new_depth

            self.max_depth = max(self.max_depth, new_depth)

    def __str__(self):
        return str(self.max_depth)


# ============================================================
# Kalyna-128 state layout
# State = 8 rows × 2 columns of bytes
# byte(row,col) = state[8*(8*col + row) : 8*(8*col + row)+8]
# ============================================================

ROWS = 8
COLS = 2


def byte_index(row, col):
    return 8 * (8 * col + row)


def get_byte(state128, row, col):
    p = byte_index(row, col)
    return state128[p:p + 8]


def set_byte(state128, row, col, byte8):
    p = byte_index(row, col)
    state128[p:p + 8] = byte8


def get_column64(state128, col):
    out = []
    for row in range(ROWS):
        out += get_byte(state128, row, col)
    return out


def set_column64(state128, col, col64):
    for row in range(ROWS):
        set_byte(state128, row, col, col64[8*row:8*row+8])


# ============================================================
# GF(2^8) arithmetic for Kalyna
# Polynomial: x^8 + x^4 + x^3 + x^2 + 1 = 0x11D
# In multiplication reduction, use low byte 0x1D.
# ============================================================

GF_POLY_LOW = 0x1D

KALYNA_V = [
    0x01, 0x01, 0x05, 0x01,
    0x08, 0x06, 0x07, 0x04
]


def gf_mul(a, b):
    """
    Multiplication in GF(2^8) with polynomial 0x11D.
    """
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


def byte_to_bits(x):
    """
    LSB-first byte bits.
    """
    return [(x >> i) & 1 for i in range(8)]


def bits_to_byte(bits):
    """
    LSB-first bits to byte.
    """
    return sum((bits[i] & 1) << i for i in range(8))


def kalyna_mix_column_bytes(col_bytes):
    """
    Classical Kalyna MixColumns on one 8-byte column.

    Input:
        col_bytes = [g0, g1, ..., g7]

    Output:
        w_i = (v >>> i) dot column over GF(2^8)
    """
    out = []

    for i in range(8):
        acc = 0

        for j in range(8):
            # v >>> i means right circular shift by i.
            # Row i coefficient at position j is v[(j - i) mod 8].
            coeff = KALYNA_V[(j - i) % 8]
            acc ^= gf_mul(coeff, col_bytes[j])

        out.append(acc)

    return out


# ============================================================
# Build the 64×64 binary matrix for one Kalyna column
# ============================================================

def build_mixcol_matrix_64():
    """
    Builds binary matrix A such that:
        output_bits = A * input_bits
    over GF(2), for one 64-bit Kalyna column.
    """
    A = np.zeros((64, 64), dtype=np.uint8)

    for i in range(64):
        bits = [0] * 64
        bits[i] = 1

        col_bytes = []
        for row in range(8):
            col_bytes.append(bits_to_byte(bits[8*row:8*row+8]))

        out_bytes = kalyna_mix_column_bytes(col_bytes)

        out_bits = []
        for b in out_bytes:
            out_bits += byte_to_bits(b)

        for r in range(64):
            A[r, i] = out_bits[r]

    return A


# ============================================================
# CNOT synthesis by Gaussian elimination
# Row operation row_dst ^= row_src corresponds to CNOT src -> dst
# Row swaps are treated as logical swaps, so they cost 0 gates.
# ============================================================

def gauss_jordan_ops_to_I(A):
    A = A.copy().astype(np.uint8)
    n = A.shape[0]
    ops = []

    for p in range(n):
        piv = None
        for r in range(p, n):
            if A[r, p]:
                piv = r
                break

        if piv is None:
            raise ValueError("Matrix is singular. Check MixColumns matrix.")

        if piv != p:
            A[[p, piv]] = A[[piv, p]]
            ops.append(("swap", p, piv))

        for r in range(n):
            if r != p and A[r, p]:
                A[r] ^= A[p]
                ops.append(("rowxor", p, r))

    return ops


_MIXCOL64_OPS = gauss_jordan_ops_to_I(build_mixcol_matrix_64())


def apply_linear_ops_inplace(eng, qubits, ops):
    """
    Apply linear map using reversed row-reduction operations.
    """
    q = list(qubits)

    for op in reversed(ops):
        if op[0] == "swap":
            i, j = op[1], op[2]
            q[i], q[j] = q[j], q[i]       # logical swap, no gate
        else:
            src, dst = op[1], op[2]
            CNOT | (q[src], q[dst])

    return q


# ============================================================
# Kalyna-128 ψ: MixColumns
# Apply same 64-bit column map to both columns.
# ============================================================

def kalyna_mixcolumns_128(eng, state128):
    state = list(state128)

    for col in range(COLS):
        c = get_column64(state, col)
        c2 = apply_linear_ops_inplace(eng, c, _MIXCOL64_OPS)
        set_column64(state, col, c2)

    return state


# ============================================================
# Run gate count and depth for ψ only
# ============================================================

def run_mixcolumns_counts():
    one_col_cnot = sum(1 for op in _MIXCOL64_OPS if op[0] == "rowxor")
    one_col_swaps = sum(1 for op in _MIXCOL64_OPS if op[0] == "swap")

    print("=== Kalyna-128 ψ: MixColumns setup ===")
    print("One-column synthesized CNOT count:", one_col_cnot)
    print("One-column logical swaps:", one_col_swaps)
    print("Expected two-column CNOT count:", 2 * one_col_cnot)

    # Gate count
    rc = ResourceCounter()
    eng1 = MainEngine(backend=rc)

    state = eng1.allocate_qureg(128)
    _ = kalyna_mixcolumns_128(eng1, state)

    eng1.flush()

    print("\n=== Kalyna-128 ψ: MixColumns gate counts ===")
    print(rc)

    # Depth
    dc = DepthEstimator()
    eng2 = MainEngine(backend=dc)

    state2 = eng2.allocate_qureg(128)
    _ = kalyna_mixcolumns_128(eng2, state2)

    eng2.flush()

    print("Circuit depth:", dc)


if __name__ == "__main__":
    run_mixcolumns_counts()
