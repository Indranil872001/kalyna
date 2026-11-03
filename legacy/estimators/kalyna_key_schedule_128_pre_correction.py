# ============================================================
# Kalyna-128/128 key schedule gate-count estimator
# Based on the component counts already obtained experimentally.
#
# This estimates the NCT cost:
#     X, CNOT, CCNOT
#
# Important:
# This is a formula-based estimator, not a ProjectQ full circuit.
# It avoids manually adding large numbers and prevents mistakes.
# ============================================================


from dataclasses import dataclass


@dataclass
class Cost:
    X: int = 0
    CX: int = 0
    CCX: int = 0

    def __add__(self, other):
        return Cost(
            self.X + other.X,
            self.CX + other.CX,
            self.CCX + other.CCX
        )

    def __mul__(self, n):
        return Cost(
            self.X * n,
            self.CX * n,
            self.CCX * n
        )

    __rmul__ = __mul__

    def show(self, label):
        print(f"{label:<45} X = {self.X:<8} CX = {self.CX:<10} CCX = {self.CCX}")


# ============================================================
# Component costs from our Kalyna-128 implementation
# ============================================================

ETA = Cost(X=0, CX=514, CCX=256)        # modulo 2^64 key addition
PI  = Cost(X=60, CX=524, CCX=82348)     # S-box layer
TAU = Cost(X=0, CX=0, CCX=0)            # ShiftRows, logical
PSI = Cost(X=0, CX=3540, CCX=0)         # MDS linear layer
KAPPA = Cost(X=0, CX=128, CCX=0)        # XOR round-key addition


# ============================================================
# 1. Intermediate key K_sigma generation
#
# For Kalyna-128/128:
#
# K_sigma = Θ(K)
#
# Θ = ψ τ π η(Kα) ψ τ π κ(Kω) ψ τ π η(Kα)
#
# Since k = l = 128:
#     Kα = Kω = K
#
# Therefore the cost is:
#     3π + 3τ + 3ψ + 2η + 1κ
# ============================================================

def cost_Ksigma_generation():
    return 3 * PI + 3 * TAU + 3 * PSI + 2 * ETA + KAPPA


# ============================================================
# 2. One even-indexed round key generation
#
# Even round keys:
#     K0, K2, K4, K6, K8, K10
#
# The main transformation Ξ has the form:
#
# Ξ = η(phi_i) ψ τ π κ(phi_i) ψ τ π η(phi_i)
#
# If phi_i(K_sigma) is assumed to be already available,
# one even-key generation costs:
#
#     2η + 2π + 2τ + 2ψ + 1κ
# ============================================================

def cost_one_even_key_core():
    return 2 * ETA + 2 * PI + 2 * TAU + 2 * PSI + KAPPA


# ============================================================
# 3. Optional explicit phi_i generation
#
# phi_i(K_sigma) = K_sigma + shifted_constant mod 2^64
#
# A simple baseline is to count phi_i generation as one ETA-like
# modulo-addition layer.
#
# This is optional because some papers may treat phi_i as part of
# the round-key material generation and some may fold it into the
# key update. We print both versions.
# ============================================================

def cost_phi_generation_baseline():
    return ETA


# ============================================================
# 4. Odd-indexed keys
#
# Odd keys are produced by rotation:
#
#     K_i = K_{i-1} <<< (l/4 + 24)
#
# For l=128:
#     l/4 + 24 = 56
#
# This is only a logical bit permutation.
# Gate cost = 0.
# ============================================================

def cost_odd_key_generation():
    return Cost(0, 0, 0)


# ============================================================
# Main summary
# ============================================================

def main():
    print("\n============================================================")
    print("Kalyna-128/128 key schedule gate-count estimator")
    print("============================================================\n")

    print("Component costs used:")
    ETA.show("eta: modulo 2^64 addition")
    PI.show("pi: S-box layer")
    TAU.show("tau: ShiftRows")
    PSI.show("psi: MDS layer")
    KAPPA.show("kappa: XOR key addition")

    print("\n------------------------------------------------------------")
    print("Intermediate key K_sigma generation")
    print("------------------------------------------------------------")

    Ksigma = cost_Ksigma_generation()
    Ksigma.show("K_sigma generation = 3pi+3tau+3psi+2eta+kappa")

    print("\n------------------------------------------------------------")
    print("Even round-key generation")
    print("------------------------------------------------------------")

    one_even = cost_one_even_key_core()
    one_even.show("One even key core Xi")

    num_even_keys = 6   # K0,K2,K4,K6,K8,K10
    all_even_core = num_even_keys * one_even
    all_even_core.show("Six even keys, core only")

    print("\nOdd round keys:")
    print("K1,K3,K5,K7,K9 are obtained by 56-bit rotations.")
    print("Rotation is treated as logical reindexing, so gate cost is zero.")

    odd = 5 * cost_odd_key_generation()
    odd.show("Five odd keys")

    print("\n------------------------------------------------------------")
    print("Key schedule total: core version")
    print("------------------------------------------------------------")

    total_core = Ksigma + all_even_core + odd
    total_core.show("Total key schedule, core version")

    print("\nThis core version assumes phi_i(K_sigma) is already available")
    print("inside the even-key transformation.")

    print("\n------------------------------------------------------------")
    print("Key schedule total: with explicit phi_i generation")
    print("------------------------------------------------------------")

    phi_one = cost_phi_generation_baseline()
    phi_all = num_even_keys * phi_one

    phi_one.show("One phi_i generation")
    phi_all.show("Six phi_i generations")

    total_with_phi = total_core + phi_all
    total_with_phi.show("Total key schedule with phi_i generation")

    print("\n------------------------------------------------------------")
    print("Summary table")
    print("------------------------------------------------------------")

    print(f"{'Part':<45} {'X':>10} {'CX':>12} {'CCX':>12}")
    print("-" * 85)
    print(f"{'K_sigma generation':<45} {Ksigma.X:>10} {Ksigma.CX:>12} {Ksigma.CCX:>12}")
    print(f"{'One even key core':<45} {one_even.X:>10} {one_even.CX:>12} {one_even.CCX:>12}")
    print(f"{'Six even keys, core only':<45} {all_even_core.X:>10} {all_even_core.CX:>12} {all_even_core.CCX:>12}")
    print(f"{'Five odd keys':<45} {odd.X:>10} {odd.CX:>12} {odd.CCX:>12}")
    print(f"{'Total key schedule, core only':<45} {total_core.X:>10} {total_core.CX:>12} {total_core.CCX:>12}")
    print(f"{'Six phi_i generations':<45} {phi_all.X:>10} {phi_all.CX:>12} {phi_all.CCX:>12}")
    print(f"{'Total key schedule, with phi_i':<45} {total_with_phi.X:>10} {total_with_phi.CX:>12} {total_with_phi.CCX:>12}")


if __name__ == "__main__":
    main()
