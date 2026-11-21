#!/usr/bin/env python3
"""Experimental full-Kalyna monomial-bank S-box compiler certificate.

The base src/kalyna_oracle/compiler.py is not edited. This program monkeypatches
the *functional* S-box constructor in this process only. It compares every round
key and ciphertext with the pinned independent C harness, checks phase marking
and coherent cleanup, and measures emitted full-circuit gate counts and widths.
Not a hardware or dense-statevector quantum simulation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
from pathlib import Path

from src.kalyna_oracle import compiler as c
from validation.run_full_oracle_certificate import reference_case

BASE_LAYER_CCX=24144
NEW_LAYER_CCX={2:11032,3:8104,4:7856}

def install(cutoff: int) -> None:
    assert cutoff in (2,3,4)
    def optimized_sbox(t,byte8,sbox_id,label):
        out=t.alloc(8,label+"/out")
        masks=[m for d in range(2,cutoff+1)
               for m in range(1,256) if m.bit_count()==d]
        bankreg=t.alloc(len(masks),label+"/monomial_bank")
        scratch=t.alloc(math.ceil(8/cutoff)-1,label+"/scratch")
        bank={1<<i:byte8[i] for i in range(8)}
        history=[]
        for mask,wire in zip(masks,bankreg.wires):
            bit=mask & -mask
            parent=mask^bit
            gate=(byte8[bit.bit_length()-1],bank[parent],wire)
            t.ccx(*gate)
            history.append(gate)
            bank[mask]=wire
        for mask,outs in c.sbox_occurrences(sbox_id):
            if mask==0:
                for ob in outs:t.x(out.wires[ob])
            elif mask.bit_count()<=cutoff:
                for ob in outs:t.cx(bank[mask],out.wires[ob])
            else:
                bits=[i for i in range(8) if mask&(1<<i)]
                fac=[bank[sum(1<<i for i in bits[j:j+cutoff])]
                     for j in range(0,len(bits),cutoff)]
                gates=[]
                cur=fac[0]
                for nxt,wire in zip(fac[1:],scratch.wires):
                    gate=(cur,nxt,wire)
                    t.ccx(*gate);gates.append(gate);cur=wire
                for ob in outs:t.cx(cur,out.wires[ob])
                for gate in reversed(gates):t.ccx(*gate)
        for gate in reversed(history):t.ccx(*gate)
        t.free_clean(scratch,"clean local AND scratch")
        t.free_clean(bankreg,"clean reusable monomial bank")
        return out
    c.sbox_to_fresh=optimized_sbox

def expected(k:int,h:int)->dict:
    diff=BASE_LAYER_CCX-NEW_LAYER_CCX[h]
    enc0=241952 if k==128 else 338528
    ks0=367280 if k==128 else 465392
    nr=10 if k==128 else 14
    # Key schedule uses 15 or 19 128-bit nonlinear layers.
    nks=15 if k==128 else 19
    n_pairs=2 if k==128 else 3
    enc=enc0-nr*diff
    ks=ks0-nks*diff
    eq=2*n_pairs*128-5
    diffuser=2*k-5
    it=2*ks+2*n_pairs*enc+eq+diffuser
    return dict(encryption_ccx=enc,key_schedule_ccx=ks,
                full_cipher_ccx=enc+ks,iteration_ccx=it,iteration_T7=7*it)

def validate_one(k:int,h:int,exe:Path,random_cases:int)->dict:
    prog=c.compile_cipher(k)
    exp=expected(k,h)
    actual=prog.tape.summary()
    if actual["CCX"] != exp["full_cipher_ccx"]:
        raise AssertionError(f"resource CCX mismatch for 128/{k}: {actual['CCX']} vs {exp}")
    rng=random.Random(20261103+k)
    cases=[(c.historical_key(k),c.known_pairs(k)[0][0],"official_KAT")]
    for i in range(random_cases):
        key=bytes(rng.randrange(256) for _ in range(k//8))
        pt=bytes(rng.randrange(256) for _ in range(16))
        cases.append((key,pt,f"random_{i}"))
    for key,pt,label in cases:
        ref=reference_case(exe,k,key,pt)
        ct,rks,clean=c.simulate_cipher_program(prog,key,pt)
        if not clean or ct.hex()!=ref["ciphertext"].lower():
            raise AssertionError(f"cipher mismatch for 128/{k} {label}")
        expected_rks=[bytes.fromhex(x) for x in ref["round_keys"]]
        if rks!=expected_rks:
            raise AssertionError(f"roundkey mismatch for 128/{k} {label}")
    del prog
    oracle=c.compile_phase_oracle(k,*c.known_pairs(k))
    truekey=c.historical_key(k)
    marked,clean=c.simulate_phase_oracle_basis(oracle,truekey)
    if not(marked and clean):raise AssertionError(f"historical-key marking/cleanup {k}")
    wrong_specs=[(0,1),(0,128),(k//16,4),(k//8-1,64)]
    for byteindex,mask in wrong_specs:
        wrong=bytearray(truekey);wrong[byteindex]^=mask
        wrongmarked,wrongclean=c.simulate_phase_oracle_basis(oracle,bytes(wrong))
        if wrongmarked or not wrongclean:raise AssertionError(f"wrong key/cleanup {k}")
    res=c.complete_iteration_nonclifford(oracle)
    if res["complete_iteration_CCX_equivalent"]!=exp["iteration_ccx"]:
        raise AssertionError(f"iteration CCX mismatch for 128/{k}")
    if res["complete_iteration_T_7_per_CCX"]!=exp["iteration_T7"]:
        raise AssertionError(f"iteration T mismatch for 128/{k}")
    return {
       "variant":f"128/{k}", "cutoff":h,"status":"PASS",
       "reference_cases_passed":len(cases),"wrong_key_cases_passed":len(wrong_specs),
       "pinned_reference":"22eafbcaf6635dc5e1f8a734b1f7c5ab84b5a5ea",
       "full_cipher_counts":dict(oracle.tape.counts),
       "forward_cipher_counts":actual,
       "forward_cipher_qubits":actual["physical_width"],
       "phase_oracle_qubits":res["compiled_physical_width"],
       "phase_oracle_dependency_depth":res["complete_phase_oracle_dependency_depth"],
       "complete_iteration_CCX_equivalent":res["complete_iteration_CCX_equivalent"],
       "complete_iteration_T7":res["complete_iteration_T_7_per_CCX"],
       "phase_forward_sha256":res["forward_gate_hash"],
       "phase_mark_sha256":res["mark_gate_hash"],
       "coherent_cleanup_reason":"All basis-preserving phase-mark operations are bracketed by the exact inverse gate sequence.",
       "limitations":"Unit-weight logical dependency depth, ideal connectivity, seven-T Toffoli convention. No routing/error correction/noisy execution; diffuser depth excluded."
    }

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--cutoff",type=int,choices=(2,3,4),required=True)
    pa.add_argument("--reference",type=Path,required=True)
    pa.add_argument("--random-cases",type=int,default=10)
    pa.add_argument("--out",type=Path,required=True)
    args=pa.parse_args()
    install(args.cutoff)
    results={}
    for k in (128,256):
        results[str(k)]=validate_one(k,args.cutoff,args.reference,args.random_cases)
        print(f"OPTIMIZED_ORACLE_{k}_PASS")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps({"status":"PASS","cutoff":args.cutoff,"results":results},indent=2)+"\n")
    print("FULL_OPTIMIZED_ORACLE_CERTIFICATE_PASS")

if __name__=="__main__": main()
