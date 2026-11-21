#!/usr/bin/env python3
"""Exhaustive independent check of the actual installed optimized Kalyna S-box adapter."""
from src.kalyna_oracle import compiler as c
from validation.optimized_oracle_experiment import install
COUNTS = {2:(690,688,688,692),3:(506,506,506,508),4:(492,490,490,492)}
ORIGINAL = c.sbox_to_fresh
def verify(h):
    c.sbox_to_fresh = ORIGINAL
    install(h)
    tests = 0
    for i in range(4):
        for x in range(256):
            tape = c.GateTape()
            inp = tape.alloc(8,'S/input')
            out = c.sbox_to_fresh(tape,inp.wires,i,'S/out')
            assert tape.counts['CCX'] == COUNTS[h][i], (h,i,tape.counts['CCX'])
            inp_set = set(inp.wires); out_set = set(out.wires); allowed=inp_set|out_set
            for y in (0,0xA5,0x5A):
                bits = bytearray(tape.physical_width)
                for b in range(8):
                    bits[inp.wires[b]] = (x>>b)&1
                    bits[out.wires[b]] = (y>>b)&1
                original = bytes(bits)
                assert c.simulate_forward(bits,tape.gates) == 0
                got=sum(bits[out.wires[b]]<<b for b in range(8))
                assert got == (y ^ c.PI[i][x]), (h,i,x,y,got)
                assert all(bits[q] == original[q] for q in inp.wires)
                assert all(bits[q] == 0 for q in range(tape.physical_width) if q not in allowed)
                assert c.simulate_reverse(bits,tape.gates) == 0
                assert bytes(bits) == original
                tests += 1
    print('SBOX_CUTOFF_%d_PASS: %d cases; 128-bit layer %d CCNOT' % (h,tests,4*sum(COUNTS[h])))
    return tests
if __name__ == '__main__':
    for h in (2,3,4): assert verify(h) == 4*256*3
    print('ALL_KALYNA_SBOX_LOCAL_CERTIFICATES_PASS')
