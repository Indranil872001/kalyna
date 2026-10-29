#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "kalyna.h"

/*
 * Full-round Kalyna oracle-multiplicity experiment.
 *
 * The candidate domain is a 2^u affine subspace obtained by XORing the low
 * u bits of the first 64-bit master-key word. For each deterministic trial
 * we choose a different true key inside that subspace and a different
 * 128-bit plaintext, encrypt with the pinned official Kalyna implementation,
 * and count how many candidate keys agree with the target on three nested
 * ciphertext windows: b=u-4, b=u, and b=u+4 bits.
 *
 * One full-round candidate encryption is reused for all three comparisons.
 * Matching only b ciphertext bits is an experimental surrogate that makes
 * the spurious-key occupancy transition observable in a tractable restricted
 * domain. Every encryption itself is full round and uses the full key
 * schedule. This program does not claim that a b-bit comparison is the
 * production key-recovery oracle.
 */

static const uint64_t KEY128_BASE[2] = {
    0x0706050403020100ULL, 0x0f0e0d0c0b0a0908ULL
};
static const uint64_t KEY256_BASE[4] = {
    0x0706050403020100ULL, 0x0f0e0d0c0b0a0908ULL,
    0x1716151413121110ULL, 0x1f1e1d1c1b1a1918ULL
};

static const uint64_t P128_KAT[2] = {
    0x1716151413121110ULL, 0x1f1e1d1c1b1a1918ULL
};
static const uint64_t C128_KAT[2] = {
    0x20ac9b777d1cbf81ULL, 0x06add2b439eac9e1ULL
};

static const uint64_t P256_KAT[2] = {
    0x2726252423222120ULL, 0x2f2e2d2c2b2a2928ULL
};
static const uint64_t C256_KAT[2] = {
    0x8a150010093eec58ULL, 0x144f336f16f74811ULL
};

static int eq128(const uint64_t a[2], const uint64_t b[2]) {
    return a[0] == b[0] && a[1] == b[1];
}

static uint64_t xs64(uint64_t *s) {
    uint64_t x = *s;
    x ^= x << 13;
    x ^= x >> 7;
    x ^= x << 17;
    *s = x;
    return x;
}

static void build_window_masks(int offset, int bits, uint64_t *m0, uint64_t *m1) {
    *m0 = 0;
    *m1 = 0;
    for (int i = 0; i < bits; ++i) {
        int p = (offset + i) & 127;
        if (p < 64) *m0 |= 1ULL << p;
        else *m1 |= 1ULL << (p - 64);
    }
}

static int masked_equal(const uint64_t a[2], const uint64_t b[2],
                        uint64_t m0, uint64_t m1) {
    return (((a[0] ^ b[0]) & m0) == 0ULL) &&
           (((a[1] ^ b[1]) & m1) == 0ULL);
}

static void encrypt128(kalyna_t *ctx, const uint64_t pt[2], uint64_t ct[2]) {
    uint64_t in[2] = {pt[0], pt[1]};
    KalynaEncipher(in, ctx, ct);
}

static int official_kat_ok(kalyna_t *ctx, int keybits) {
    uint64_t key[4] = {0,0,0,0};
    uint64_t ct[2] = {0,0};
    if (keybits == 128) {
        memcpy(key, KEY128_BASE, sizeof(KEY128_BASE));
        KalynaKeyExpand(key, ctx);
        encrypt128(ctx, P128_KAT, ct);
        return eq128(ct, C128_KAT);
    }
    memcpy(key, KEY256_BASE, sizeof(KEY256_BASE));
    KalynaKeyExpand(key, ctx);
    encrypt128(ctx, P256_KAT, ct);
    return eq128(ct, C256_KAT);
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr,
                "usage: %s <keybits:128|256> <unknown_bits:5..20> <trials:1..256>\n",
                argv[0]);
        return 2;
    }

    const int keybits = atoi(argv[1]);
    const int u = atoi(argv[2]);
    const int trials = atoi(argv[3]);

    if ((keybits != 128 && keybits != 256) ||
        u < 5 || u > 20 ||
        u + 4 > 128 ||
        trials < 1 || trials > 256) {
        fprintf(stderr, "invalid arguments\n");
        return 2;
    }

    const int compare_bits[3] = {u - 4, u, u + 4};

    kalyna_t *ctx = KalynaInit(128, (size_t)keybits);
    if (!ctx) {
        fprintf(stderr, "KalynaInit failed\n");
        return 3;
    }
    if (!official_kat_ok(ctx, keybits)) {
        fprintf(stderr, "official KAT mismatch\n");
        KalynaDelete(ctx);
        return 4;
    }

    const uint64_t N = 1ULL << u;
    uint64_t seed = 0x9e3779b97f4a7c15ULL
                  ^ ((uint64_t)keybits << 32)
                  ^ ((uint64_t)u << 16)
                  ^ 0x4b414c594e41554cULL;

    for (int t = 0; t < trials; ++t) {
        uint64_t true_index = xs64(&seed) & (N - 1);
        uint64_t pt[2] = {xs64(&seed), xs64(&seed)};
        int offset = (int)(xs64(&seed) & 127ULL);

        uint64_t true_key[4] = {0,0,0,0};
        if (keybits == 128) memcpy(true_key, KEY128_BASE, sizeof(KEY128_BASE));
        else memcpy(true_key, KEY256_BASE, sizeof(KEY256_BASE));
        true_key[0] ^= true_index;

        KalynaKeyExpand(true_key, ctx);
        uint64_t target[2] = {0,0};
        encrypt128(ctx, pt, target);

        uint64_t m0[3], m1[3];
        for (int z = 0; z < 3; ++z) {
            build_window_masks(offset, compare_bits[z], &m0[z], &m1[z]);
        }

        uint64_t marked[3] = {0,0,0};
        uint64_t first_wrong[3] = {~0ULL, ~0ULL, ~0ULL};

        for (uint64_t idx = 0; idx < N; ++idx) {
            uint64_t cand[4] = {0,0,0,0};
            if (keybits == 128) memcpy(cand, KEY128_BASE, sizeof(KEY128_BASE));
            else memcpy(cand, KEY256_BASE, sizeof(KEY256_BASE));
            cand[0] ^= idx;

            KalynaKeyExpand(cand, ctx);
            uint64_t ct[2] = {0,0};
            encrypt128(ctx, pt, ct);

            for (int z = 0; z < 3; ++z) {
                if (masked_equal(ct, target, m0[z], m1[z])) {
                    ++marked[z];
                    if (idx != true_index && first_wrong[z] == ~0ULL) {
                        first_wrong[z] = idx;
                    }
                }
            }
        }

        for (int z = 0; z < 3; ++z) {
            const uint64_t wrong = marked[z] - 1;
            printf("{");
            printf("\"variant\":\"128/%d\",", keybits);
            printf("\"key_bits\":%d,\"unknown_bits\":%d,", keybits, u);
            printf("\"compare_bits\":%d,\"trial\":%d,", compare_bits[z], t);
            printf("\"candidates\":%llu,", (unsigned long long)N);
            printf("\"true_index\":%llu,", (unsigned long long)true_index);
            printf("\"window_offset\":%d,", offset);
            printf("\"marked_count\":%llu,\"wrong_count\":%llu,",
                   (unsigned long long)marked[z], (unsigned long long)wrong);
            if (first_wrong[z] == ~0ULL) printf("\"first_wrong\":null,");
            else printf("\"first_wrong\":%llu,", (unsigned long long)first_wrong[z]);
            printf("\"official_kat_pass\":true");
            printf("}\n");
        }
    }

    KalynaDelete(ctx);
    return 0;
}
