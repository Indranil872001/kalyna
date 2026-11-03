/*
 * Independent reference harness for the exact reversible-oracle certificate.
 *
 * This file is compiled in CI against the pinned official Kalyna reference
 * implementation.  It prints the complete round-key bank and ciphertext for a
 * user-supplied key/plaintext pair so the Python reversible compiler can be
 * checked end-to-end.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#include "kalyna.h"

static int hexval(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return 10 + c - 'a';
    if (c >= 'A' && c <= 'F') return 10 + c - 'A';
    return -1;
}

static int parse_hex(const char *s, unsigned char *out, size_t n) {
    if (strlen(s) != 2 * n) return 0;
    for (size_t i = 0; i < n; ++i) {
        int hi = hexval(s[2*i]);
        int lo = hexval(s[2*i+1]);
        if (hi < 0 || lo < 0) return 0;
        out[i] = (unsigned char)((hi << 4) | lo);
    }
    return 1;
}

static void print_hex_bytes(const unsigned char *x, size_t n) {
    for (size_t i = 0; i < n; ++i) printf("%02X", x[i]);
}

int main(int argc, char **argv) {
    if (argc != 4) {
        fprintf(stderr, "usage: %s <keybits:128|256> <keyhex> <plaintexthex>\n", argv[0]);
        return 2;
    }

    int keybits = atoi(argv[1]);
    if (keybits != 128 && keybits != 256) {
        fprintf(stderr, "invalid key size\n");
        return 2;
    }

    size_t keybytes = (size_t)keybits / 8;
    unsigned char key_bytes[32] = {0};
    unsigned char pt_bytes[16] = {0};
    unsigned char ct_bytes[16] = {0};

    if (!parse_hex(argv[2], key_bytes, keybytes) ||
        !parse_hex(argv[3], pt_bytes, sizeof(pt_bytes))) {
        fprintf(stderr, "invalid hex input\n");
        return 2;
    }

    kalyna_t *ctx = KalynaInit(128, (size_t)keybits);
    if (!ctx) return 3;

    /*
     * The pinned reference is run on little-endian GitHub runners. Its word
     * representation maps the natural test-vector byte order directly to the
     * in-memory byte sequence used here.
     */
    KalynaKeyExpand((uint64_t *)key_bytes, ctx);
    KalynaEncipher((uint64_t *)pt_bytes, ctx, (uint64_t *)ct_bytes);

    printf("{\"ciphertext\":\"");
    print_hex_bytes(ct_bytes, 16);
    printf("\",\"round_keys\":[");
    for (size_t r = 0; r <= ctx->nr; ++r) {
        if (r) printf(",");
        printf("\"");
        print_hex_bytes((const unsigned char *)ctx->round_keys[r], 16);
        printf("\"");
    }
    printf("]}\n");

    KalynaDelete(ctx);
    return 0;
}
