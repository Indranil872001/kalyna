#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "kalyna.h"

static const uint64_t KEY128_TRUE[2] = {
    0x0706050403020100ULL, 0x0f0e0d0c0b0a0908ULL
};
static const uint64_t KEY256_TRUE[4] = {
    0x0706050403020100ULL, 0x0f0e0d0c0b0a0908ULL,
    0x1716151413121110ULL, 0x1f1e1d1c1b1a1918ULL
};

static const uint64_t P128_1[2] = {
    0x1716151413121110ULL, 0x1f1e1d1c1b1a1918ULL
};
static const uint64_t C128_1_EXPECT[2] = {
    0x20ac9b777d1cbf81ULL, 0x06add2b439eac9e1ULL
};

static const uint64_t P256_1[2] = {
    0x2726252423222120ULL, 0x2f2e2d2c2b2a2928ULL
};
static const uint64_t C256_1_EXPECT[2] = {
    0x8a150010093eec58ULL, 0x144f336f16f74811ULL
};

static const uint64_t P_COMMON_2[2] = {
    0x0706050403020100ULL, 0x0f0e0d0c0b0a0908ULL
};
static const uint64_t P_COMMON_3[2] = {
    0x1716151413121110ULL, 0x1f1e1d1c1b1a1918ULL
};

static void hex128(const uint64_t x[2], char out[33]) {
    const unsigned char *p = (const unsigned char *)x;
    for (int i = 0; i < 16; ++i) {
        sprintf(out + 2*i, "%02X", (unsigned)p[i]);
    }
    out[32] = '\0';
}

static int eq128(const uint64_t a[2], const uint64_t b[2]) {
    return a[0] == b[0] && a[1] == b[1];
}

static void encrypt128(kalyna_t *ctx, const uint64_t pt[2], uint64_t ct[2]) {
    uint64_t in[2] = {pt[0], pt[1]};
    KalynaEncipher(in, ctx, ct);
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <keybits:128|256> <unknown_bits:1..20> <pairs>\n", argv[0]);
        return 2;
    }

    const int keybits = atoi(argv[1]);
    const int u = atoi(argv[2]);
    const int pairs = atoi(argv[3]);
    if ((keybits != 128 && keybits != 256) || u < 1 || u > 20) {
        fprintf(stderr, "invalid keybits/u\n");
        return 2;
    }
    const int max_pairs = (keybits == 128) ? 2 : 3;
    if (pairs < 1 || pairs > max_pairs) {
        fprintf(stderr, "invalid pair count for selected variant\n");
        return 2;
    }

    kalyna_t *ctx = KalynaInit(128, (size_t)keybits);
    if (!ctx) {
        fprintf(stderr, "KalynaInit failed\n");
        return 3;
    }

    uint64_t true_key[4] = {0,0,0,0};
    const int key_words = keybits / 64;
    if (keybits == 128) memcpy(true_key, KEY128_TRUE, sizeof(KEY128_TRUE));
    else memcpy(true_key, KEY256_TRUE, sizeof(KEY256_TRUE));

    KalynaKeyExpand(true_key, ctx);

    uint64_t targets[3][2] = {{0,0},{0,0},{0,0}};
    const uint64_t *pts[3];
    if (keybits == 128) {
        pts[0] = P128_1;
        pts[1] = P_COMMON_2;
    } else {
        pts[0] = P256_1;
        pts[1] = P_COMMON_2;
        pts[2] = P_COMMON_3;
    }
    for (int j = 0; j < max_pairs; ++j) {
        encrypt128(ctx, pts[j], targets[j]);
    }

    const int kat_ok = (keybits == 128)
        ? eq128(targets[0], C128_1_EXPECT)
        : eq128(targets[0], C256_1_EXPECT);
    if (!kat_ok) {
        fprintf(stderr, "official KAT mismatch\n");
        KalynaDelete(ctx);
        return 4;
    }

    const uint64_t N = 1ULL << u;
    uint64_t marked = 0;
    uint64_t first_marked = ~0ULL;
    uint64_t last_marked = ~0ULL;

    for (uint64_t idx = 0; idx < N; ++idx) {
        uint64_t cand[4] = {0,0,0,0};
        memcpy(cand, true_key, (size_t)key_words * sizeof(uint64_t));
        cand[0] ^= idx;

        KalynaKeyExpand(cand, ctx);

        int good = 1;
        for (int j = 0; j < pairs; ++j) {
            uint64_t ct[2] = {0,0};
            encrypt128(ctx, pts[j], ct);
            if (!eq128(ct, targets[j])) {
                good = 0;
                break;
            }
        }
        if (good) {
            if (marked == 0) first_marked = idx;
            last_marked = idx;
            ++marked;
        }
    }

    char t0[33], t1[33], t2[33];
    hex128(targets[0], t0);
    if (max_pairs >= 2) hex128(targets[1], t1); else strcpy(t1, "");
    if (max_pairs >= 3) hex128(targets[2], t2); else strcpy(t2, "");

    printf("{");
    printf("\"variant\":\"128/%d\",", keybits);
    printf("\"key_bits\":%d,\"unknown_bits\":%d,\"pairs\":%d,", keybits, u, pairs);
    printf("\"candidates\":%llu,\"marked_count\":%llu,",
           (unsigned long long)N, (unsigned long long)marked);
    if (marked) {
        printf("\"first_marked\":%llu,\"last_marked\":%llu,",
               (unsigned long long)first_marked, (unsigned long long)last_marked);
    } else {
        printf("\"first_marked\":null,\"last_marked\":null,");
    }
    printf("\"official_kat_pass\":true,");
    printf("\"target_ciphertexts\":[\"%s\"", t0);
    if (max_pairs >= 2) printf(",\"%s\"", t1);
    if (max_pairs >= 3) printf(",\"%s\"", t2);
    printf("]}\n");

    KalynaDelete(ctx);
    return 0;
}
