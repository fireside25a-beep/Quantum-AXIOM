#!/usr/bin/env python3
"""Run preserved SNN/quantum code and check admitted state through native ELF.

The C reference remains test-only. Production compiler/runtime use no neural
framework. This establishes a bounded state-transfer lineage, not a general
self-hosted compiler or physical quantum coherence.
"""
import hashlib
import json
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile

from native_clifford_independent import state, apply, CANONICAL, parse_file

R=Path(__file__).resolve().parents[1]
DONOR=R/'tests/reference/closed_routine'
COMPILER=R/'native/clifford/native_clifford_compiler.py'
FIXTURE=R/'examples/States/closed_routine.qstate.json'

def execute(*args, env=None):
    return subprocess.run(list(map(str,args)),capture_output=True,timeout=40,env=env)

def demand(result):
    if result.returncode:
        raise AssertionError((result.returncode,result.stdout[-1000:],result.stderr[-2000:]))
    return result

def main():
    report={'status':'FAIL','source_manifest_verified':False,'native_reference_builds':{},
            'native_import_sequences':0,'native_inverse_sequences':0,
            'malformed_snapshot_refusals':0,'scope':'executed source-linked state transfer; test-only preserved reference',
            'general_compiler_self_hosting':False,'physical_coherent_qubits':False}
    provenance=json.loads((DONOR/'PROVENANCE.json').read_text())
    for item in provenance['selected_files']:
        p=R/item['release_path']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
            raise AssertionError(('reference source mismatch',p))
    report['source_manifest_verified']=True
    fixture=FIXTURE.read_bytes()
    snapshot=json.loads(fixture)
    initial=list(CANONICAL)
    for i in range(5):
        initial[i]=tuple(snapshot['rows'][i]);initial[32+i]=tuple(snapshot['rows'][5+i])
    with tempfile.TemporaryDirectory(prefix='axiom-closed-lineage-') as folder:
        tmp=Path(folder)
        for flavor,flags in [('O0',['-O0']),('O2',['-O2']),
                             ('san',['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer'])]:
            target=tmp/('probe-'+flavor)
            cmd=['cc','-std=c11','-Wall','-Wextra','-Werror',*flags,'-I',DONOR,
                 R/'tests/closed_routine_probe.c',DONOR/'neuro_mantle.c',DONOR/'neuro_world.c',DONOR/'primitiveq.c','-o',target]
            demand(execute(*cmd))
            environment=dict(os.environ)
            environment['ASAN_OPTIONS']='detect_leaks=1:halt_on_error=1'
            environment['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
            result=execute(target,env=environment)
            leak_block=(flavor=='san' and result.returncode!=0 and
                        b'LeakSanitizer has encountered a fatal error' in result.stderr and
                        b'LeakSanitizer does not work under ptrace' in result.stderr)
            if result.returncode and not leak_block:demand(result)
            if result.stdout!=fixture:raise AssertionError(('source fixture mismatch',flavor))
            m=re.search(rb'CLOSED_ROUTINE_PASS cases=(\d+) feedback_spikes=(\d+) transactional_refusals=(\d+)',result.stderr)
            if not m or tuple(map(int,m.groups()))!=(195,195,195):raise AssertionError(result.stderr)
            report['native_reference_builds'][flavor]={'status':'BLOCKED_LEAKSANITIZER_HOST_PTRACE' if leak_block else 'PASS',
                'exit_code':result.returncode,'cases':195,'real_snn_feedback_spikes':195,
                'transactional_refusals':195,'exported_state_sha256':hashlib.sha256(result.stdout).hexdigest()}
            if leak_block:
                report['native_reference_builds'][flavor]['stderr']=result.stderr.decode(errors='replace')
                report['native_reference_builds'][flavor]['sanitizers_disabled']=False
                report['native_reference_builds'][flavor]['sanitizer_validation_complete']=False
        rng=random.Random(0xA810C10)
        for case in range(16):
            ops=[]
            for _ in range(rng.randrange(2,12)):
                kind=rng.choice(('H','S','CX'));q=rng.randrange(5)
                ops.append((kind,q,(q+rng.randrange(1,5))%5) if kind=='CX' else (kind,q))
            for inverse in (False,True):
                gates=list(ops)
                if inverse:
                    for gate in reversed(ops):gates.extend([gate]*3 if gate[0]=='S' else [gate])
                src=tmp/'source.qcl';out=tmp/'program.x86_64';audit=tmp/'audit.json'
                src.write_text('sites 32\n'+'\n'.join(' '.join(map(str,g)) for g in gates)+'\n')
                demand(execute('python3',COMPILER,src,out,audit,FIXTURE))
                if state(out.read_bytes())[1]!=initial:raise AssertionError('imported start state differs')
                result=demand(execute(out));epoch,observed=state(result.stdout)
                predicted=apply(initial,gates)
                if epoch!=1 or observed!=predicted:raise AssertionError(('native state transfer',case,inverse))
                if inverse:
                    if observed!=initial:raise AssertionError(('native inverse',case))
                    report['native_inverse_sequences']+=1
                else:report['native_import_sequences']+=1
        base={'format':'AXIOM_TABLEAU_STATE_1','sites':1,'rows':[[1,0,0],[0,1,0]]}
        invalid=[]
        for n in (0,33,True):invalid.append({**base,'sites':n})
        for rows in ([[1,0,0]],[[1,0,0],[1,0,0]],[[2,0,0],[0,1,0]],
                     [[1,0,1],[0,1,0]],[[True,0,0],[0,1,0]],[[1,0,4],[0,1,0]]):
            invalid.append({**base,'rows':rows})
        invalid.extend(({**base,'unknown':1},{**base,'format':'UNKNOWN'}))
        raw_inputs=[json.dumps(obj).encode() for obj in invalid]
        raw_inputs.extend((b'{"format":"AXIOM_TABLEAU_STATE_1","sites":1,"sites":2,"rows":[]}',b'{',b' '*16385))
        src=tmp/'bad-source.qcl';src.write_text('sites 32\nH 0\n')
        for index,raw in enumerate(raw_inputs):
            bad=tmp/'invalid.json';bad.write_bytes(raw);out=tmp/f'invalid-{index}.x86_64'
            result=execute('python3',COMPILER,src,out,tmp/'invalid.audit.json',bad)
            if result.returncode<=0 or out.exists():raise AssertionError(('snapshot accepted',index,result))
            report['malformed_snapshot_refusals']+=1
        imported=(R/'native/seed/closed_routine_seed.x86_64').read_bytes()
        if state(imported)[1]!=initial:raise AssertionError('shipped imported seed does not match fixture')
        report['imported_seed_sha256']=hashlib.sha256(imported).hexdigest()
    report['source_volume_sha256']=provenance['source_volume_sha256']
    report['fixture_sha256']=hashlib.sha256(fixture).hexdigest()
    report['status']='PASS'
    (R/'evidence/closed_routine_lineage.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
