
# Optimized Kalyna S-box using shared nonlinear ANF monomials

from collections import defaultdict, Counter


def sbox_monomial_occurrences(sbox_id):
    """
    Return dictionary:
        monomial_mask -> list of output bits in which it appears.
    """
    occ = defaultdict(list)

    for out_bit in range(8):
        for mask in cached_anf(sbox_id, out_bit):
            occ[mask].append(out_bit)

    return dict(occ)


def direct_ccx_cost(mask):
    """
    CCX cost when a monomial is applied directly to one output bit.
    """
    d = monomial_degree(mask)

    if d <= 1:
        return 0
    elif d == 2:
        return 1
    else:
        return 2 * d - 3


def shared_ccx_cost(mask):
    """
    Clean computation of product monomial into an ancilla,
    copy to output bits by CNOT, then uncompute.

    For degree d >= 2:
        compute cost   = d - 1 Toffoli
        uncompute cost = d - 1 Toffoli
        total          = 2d - 2 Toffoli
    """
    d = monomial_degree(mask)
    assert d >= 2
    return 2 * d - 2


def should_share_monomial(mask, occurrences):
    """
    Decide whether to compute the monomial once and reuse it.

    We share only when the clean shared computation reduces CCX count.
    """
    d = monomial_degree(mask)

    if d < 2:
        return False

    direct_total = occurrences * direct_ccx_cost(mask)
    shared_total = shared_ccx_cost(mask)

    return shared_total < direct_total


def optimized_sbox_cost(sbox_id):
    """
    Formula-based optimized cost for one Kalyna S-box.
    """
    occ = sbox_monomial_occurrences(sbox_id)
    total = Counter()

    shared_count = 0
    direct_count = 0

    for mask, outs in occ.items():
        d = monomial_degree(mask)
        n = len(outs)

        if d == 0:
            total["X"] += n
            direct_count += 1

        elif d == 1:
            total["CX"] += n
            direct_count += 1

        else:
            if should_share_monomial(mask, n):
                # compute product once, CNOT to all required outputs, uncompute
                total["CCX"] += shared_ccx_cost(mask)
                total["CX"] += n
                shared_count += 1
            else:
                # use the old direct method for each occurrence
                c = monomial_gate_cost(mask)
                total["X"] += n * c["X"]
                total["CX"] += n * c["CX"]
                total["CCX"] += n * c["CCX"]
                direct_count += 1

    return total, shared_count, direct_count



# ProjectQ implementation of shared monomial

def compute_product_to_ancilla(eng, controls):
    """
    Compute product of controls into a clean ancilla chain.

    Input:
        controls = [x_i1, x_i2, ..., x_id]

    Output:
        temps[-1] contains product of all controls.

    The caller must uncompute using uncompute_product_from_ancilla().
    """
    d = len(controls)
    assert d >= 2

    temps = eng.allocate_qureg(d - 1)

    # temps[0] = controls[0] * controls[1]
    Toffoli_gate(eng, controls[0], controls[1], temps[0])

    # temps[i-1] = temps[i-2] * controls[i]
    for i in range(2, d):
        Toffoli_gate(eng, temps[i - 2], controls[i], temps[i - 1])

    return list(temps)


def uncompute_product_from_ancilla(eng, controls, temps):
    """
    Reverse of compute_product_to_ancilla().
    """
    d = len(controls)
    assert d >= 2

    for i in reversed(range(2, d)):
        Toffoli_gate(eng, temps[i - 2], controls[i], temps[i - 1])

    Toffoli_gate(eng, controls[0], controls[1], temps[0])


def apply_shared_monomial_xor_clean(eng, controls, targets):
    """
    Compute product(controls) once, XOR it into all target output bits,
    then uncompute the product ancillas.
    """
    temps = compute_product_to_ancilla(eng, controls)
    prod = temps[-1]

    for t in targets:
        CNOT | (prod, t)

    uncompute_product_from_ancilla(eng, controls, temps)

    del prod
    del temps


def apply_kalyna_sbox_optimized_to_new_byte(eng, byte8, sbox_id):
    """
    Optimized ANF S-box implementation:
        |x>|0> -> |x>|pi_i(x)>

    Optimization:
        repeated nonlinear monomials are computed once and reused.
    """
    out = eng.allocate_qureg(8)
    occ = sbox_monomial_occurrences(sbox_id)

    for mask in sorted(occ.keys(), key=lambda m: (monomial_degree(m), m)):
        outs = occ[mask]
        d = monomial_degree(mask)

        if d == 0:
            for out_bit in outs:
                X | out[out_bit]

        elif d == 1:
            idx = [i for i in range(8) if (mask >> i) & 1][0]
            for out_bit in outs:
                CNOT | (byte8[idx], out[out_bit])

        else:
            controls = [byte8[i] for i in range(8) if (mask >> i) & 1]

            if should_share_monomial(mask, len(outs)):
                targets = [out[out_bit] for out_bit in outs]
                apply_shared_monomial_xor_clean(eng, controls, targets)
            else:
                for out_bit in outs:
                    apply_monomial_xor(eng, controls, out[out_bit])

    return list(out)


def kalyna_subbytes_128_optimized(eng, state128):
    """
    Optimized Kalyna-128 S-box layer.
    """
    out = [None] * 128

    for col in range(COLS):
        for row in range(ROWS):
            b = get_byte(state128, row, col)
            sbox_id = row % 4
            b2 = apply_kalyna_sbox_optimized_to_new_byte(eng, b, sbox_id)
            set_byte(out, row, col, b2)

    return out


# ============================================================
# Run optimized S-box analysis
# ============================================================

def run_optimized_sbox_analysis():
    print("=== Optimized Kalyna S-box analysis ===")

    baseline_layer = Counter()
    optimized_layer = Counter()

    for sid in range(4):
        old = expected_sbox_cost(sid)
        new, shared_count, direct_count = optimized_sbox_cost(sid)

        print(f"\npi{sid}:")
        print(f"    Old  : X = {old['X']}, CX = {old['CX']}, CCX = {old['CCX']}")
        print(f"    New  : X = {new['X']}, CX = {new['CX']}, CCX = {new['CCX']}")
        print(f"    Saved CCX = {old['CCX'] - new['CCX']}")
        print(f"    Shared nonlinear monomials = {shared_count}")

        for k in ["X", "CX", "CCX"]:
            baseline_layer[k] += 4 * old[k]
            optimized_layer[k] += 4 * new[k]

    print("\n============================================================")
    print("One full Kalyna-128 S-box layer")
    print("============================================================")

    print("Baseline ANF layer:")
    print(f"    X   = {baseline_layer['X']}")
    print(f"    CX  = {baseline_layer['CX']}")
    print(f"    CCX = {baseline_layer['CCX']}")

    print("\nOptimized shared-monomial ANF layer:")
    print(f"    X   = {optimized_layer['X']}")
    print(f"    CX  = {optimized_layer['CX']}")
    print(f"    CCX = {optimized_layer['CCX']}")

    print("\nImprovement:")
    print(f"    Saved CCX = {baseline_layer['CCX'] - optimized_layer['CCX']}")
    print(f"    Extra CX  = {optimized_layer['CX'] - baseline_layer['CX']}")

    # New round/core estimates using optimized pi layer
    opt_pi_X = optimized_layer["X"]
    opt_pi_CX = optimized_layer["CX"]
    opt_pi_CCX = optimized_layer["CCX"]

    inner_X = opt_pi_X
    inner_CX = opt_pi_CX + 3540 + 128
    inner_CCX = opt_pi_CCX

    final_X = opt_pi_X
    final_CX = opt_pi_CX + 3540 + 514
    final_CCX = opt_pi_CCX + 256

    core_X = 0 + 9 * inner_X + final_X
    core_CX = 514 + 9 * inner_CX + final_CX
    core_CCX = 256 + 9 * inner_CCX + final_CCX

    print("\n============================================================")
    print("Updated Kalyna-128/128 encryption core without key schedule")
    print("============================================================")

    print("Optimized one inner round:")
    print(f"    X   = {inner_X}")
    print(f"    CX  = {inner_CX}")
    print(f"    CCX = {inner_CCX}")

    print("\nOptimized final round:")
    print(f"    X   = {final_X}")
    print(f"    CX  = {final_CX}")
    print(f"    CCX = {final_CCX}")

    print("\nOptimized encryption core:")
    print(f"    X   = {core_X}")
    print(f"    CX  = {core_CX}")
    print(f"    CCX = {core_CCX}")



def run_optimized_pi_layer_projectq_count():
    print("\n=== ProjectQ count: optimized Kalyna-128 pi layer ===")

    rc = ResourceCounter()
    eng = MainEngine(backend=rc)

    state = eng.allocate_qureg(128)
    _ = kalyna_subbytes_128_optimized(eng, state)

    eng.flush()

    print(rc)


if __name__ == "__main__":
    run_optimized_sbox_analysis()

