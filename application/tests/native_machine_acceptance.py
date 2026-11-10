#!/usr/bin/env python3
"""Execute native self-hosting, quantum guests and complete journal reversal.

The reference below models canonical quantum/control state independently.
No Python component is invoked by the compiler, machine or reverse executable.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import struct
import subprocess
import tempfile

R=Path(__file__).resolve().parents[1]
C=R/'native/selfhost/anf_stage3.x86_64'
VM=R/'native/machine/quantum_machine.x86_64'
UNDO=R/'native/machine/reverse_history.x86_64'
MASK=(1<<64)-1
spec=importlib.util.spec_from_file_location('anf_constructor',R/'native/selfhost/bootstrap_anf.py')
bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)

def sha(b):return hashlib.sha256(b).hexdigest()
def fnv(b,h=0xcbf29ce484222325):
    for v in b:h=((h^v)*0x100000001b3)&MASK
    return h
def run(exe,data,*args):
    return subprocess.run([str(exe),*map(str,args)],input=data,capture_output=True,timeout=30)
def good(p):
    if p.returncode:raise AssertionError((p.returncode,p.stderr[-1000:]))
    return p.stdout
def rows_state(rows=None):
    if rows is None:rows=[(1<<i,0,0) for i in range(32)]+[(0,1<<i,0) for i in range(32)]
    state=bytearray(4096)
    for i,row in enumerate(rows):struct.pack_into('<3Q',state,1024+24*i,*row)
    return state
def seed(records,gas=1024,rows=None):
    payload=bytes(rows_state(rows))+b''.join(struct.pack('<4Q',*record) for record in records)
    return b'AXQVM11\0'+struct.pack('<7Q',1,32,len(records),gas,fnv(payload),0,0)+payload
def quantum_source(records,gas=1024,rows=None):
    lines=['qubits32',f'qgas {gas}']
    if rows:
        lines.extend(f'qrow {i} {x} {z} {p}' for i,(x,z,p) in enumerate(rows))
    names={0:'qhalt',1:'qh',2:'qs',3:'qsdg',4:'qcx',5:'qx',6:'qy',7:'qz',8:'qentropy',9:'qephase',16:'vmcall',17:'vmreturn'}
    for op,a,b,c in records:
        args=[] if op in (0,8,17) else [a,b,c] if op==16 else [a,b] if op==4 else [a]
        lines.append(' '.join(map(str,[names[op],*args])))
    return ('\n'.join(lines)+'\n').encode()
def unpack_journal(raw):
    magic,version,count,width,nbytes,digest,direction,reserved=struct.unpack('<8s7Q',raw[:64])
    if magic!=b'AXHST11\0' or version!=1 or width!=4096 or reserved or direction not in (0,1):raise AssertionError('journal ABI')
    if len(raw)!=64+nbytes+count*width or fnv(raw[64:])!=digest:raise AssertionError('journal size/hash')
    return raw[64:64+nbytes],[raw[64+nbytes+i*width:64+nbytes+(i+1)*width] for i in range(count)],direction

def reference(packet,observed_frames):
    count,gas=struct.unpack_from('<2Q',packet,24)
    ops=[struct.unpack_from('<4Q',packet,4160+32*i) for i in range(count)]
    state=bytearray(packet[64:4160]);struct.pack_into('<Q',state,72,count);struct.pack_into('<Q',state,80,gas)
    expected=[bytes(state)]
    def get(off):return struct.unpack_from('<Q',state,off)[0]
    def put(off,value):struct.pack_into('<Q',state,off,value)
    while not get(88):
        pc=get(8);start,end=get(64),get(72)
        if not start<=pc<end or not get(80):raise AssertionError('reference bounds/fuel')
        op,a,b,c=ops[pc];put(80,get(80)-1);put(8,pc+1)
        put(40,op);put(48,a);put(56,b)
        if 1<=op<=7 or op==9:
            if op==9:effective=2 if get(32)&(1<<a) else 3
            else:effective=op
            for i in range(64):
                x,z,p=struct.unpack_from('<3Q',state,1024+24*i)
                if effective==1:
                    if x&(1<<a) and z&(1<<a):p+=2
                    change=(x^z)&(1<<a);x^=change;z^=change
                elif effective in (2,3):
                    if x&(1<<a):p+=1 if effective==2 else 3;z^=1<<a
                elif effective==4:
                    if x&(1<<a):x^=1<<b
                    if z&(1<<b):z^=1<<a
                else:
                    flip=z&(1<<a) if effective==5 else (x^z)&(1<<a) if effective==6 else x&(1<<a)
                    if flip:p+=2
                struct.pack_into('<3Q',state,1024+24*i,x,z,p%4)
        elif op==8:
            # Use only the actual native sample as the oracle's entropy input.
            put(32,struct.unpack_from('<Q',observed_frames[len(expected)],32)[0])
        elif op==16:
            depth=get(24)
            if depth>=16 or not start<=b<b+c<=end:raise AssertionError('reference guest capability')
            active=[get(16)]+[get(128+32*i) for i in range(depth)]
            if a in active:raise AssertionError('reference guest cycle')
            struct.pack_into('<4Q',state,128+32*depth,get(16),pc+1,start,end)
            put(24,depth+1);put(16,a);put(8,b);put(64,b);put(72,b+c)
        elif op==17:
            depth=get(24)-1
            if depth<0:raise AssertionError('reference return')
            owner,returnpc,start,end=struct.unpack_from('<4Q',state,128+32*depth)
            state[128+32*depth:160+32*depth]=bytes(32)
            put(24,depth);put(16,owner);put(8,returnpc);put(64,start);put(72,end)
        elif op==0:
            if get(24) or get(16):raise AssertionError('reference guest halt')
            put(88,1)
        else:raise AssertionError('unknown reference opcode')
        put(0,get(0)+1);expected.append(bytes(state))
    return expected

def nested_program(depth):
    records=[(1,0,0,0)]
    def block(level):
        if level==depth:return [(2,31,0,0),(4,0,31,0),(17,0,0,0)]
        return [(16,level+1,0,0),(7,level%32,0,0),(17,0,0,0)]
    records.extend([(16,1,0,0),(5,30,0,0),(0,0,0,0)])
    starts=[]
    for level in range(1,depth+1):starts.append(len(records));records.extend(block(level))
    records[1]=(16,1,starts[0],len(records)-starts[0])
    for level in range(1,depth):records[starts[level-1]]=(16,level+1,starts[level],len(records)-starts[level])
    return records

def main():
    report={'status':'FAIL','selfhost_generations':3,'assembly_differential_cases':0,'changed_source_compilation':False,
            'quantum_programs':0,'native_inverse_roundtrips':0,'maximum_nested_depth':0,'machine_refusals':0,
            'journal_bit_refusals':0,'semantic_journal_refusals':0,'full_frame_comparisons':0,
            'uses_kvm':False,'uses_os_guest_virtualization':False,'hx89_code_reused':False}
    rng=random.Random(0xA81011)
    baseline=(R/'native/selfhost/anf_stage0.x86_64').read_bytes()
    for i in (1,2,3):
        if (R/f'native/selfhost/anf_stage{i}.x86_64').read_bytes()!=baseline:raise AssertionError('self-host generation differs')
    with tempfile.TemporaryDirectory(prefix='axiom-native-machine-') as folder:
        tmp=Path(folder)
        for i in range(100):
            r1,r2=rng.randrange(16),rng.randrange(16)
            op=rng.choice(('mov','add','sub','xor','and','or','cmp','test','mul','load','load8','store','store8'))
            program=f'code\nlabel start\nimm 0 60\nimm 7 {i%64}\n{op} {r1} {r2}\nret\nbss\nlabel data\nspace 64\n'
            actual=good(run(C,program.encode()));expected=bootstrap.assemble(program)
            if actual!=expected:raise AssertionError(('native encoding',op,r1,r2))
            report['assembly_differential_cases']+=1
        for value in (0,1,42,127):
            image=good(run(C,f'imm 0 60\nimm 7 {value}\nsyscall\n'.encode()))
            exe=tmp/'exit';exe.write_bytes(image);exe.chmod(0o755)
            if run(exe,b'').returncode!=value:raise AssertionError('unseen native program execution')
        source=(R/'native/selfhost/compiler.anf').read_text()
        old='imm 0 60\nimm 7 0\nsyscall\nlabel refuse'
        if old not in source:raise AssertionError('source mutation anchor absent')
        changed=source.replace(old,'imm 0 60\nimm 7 7\nsyscall\nlabel refuse',1)
        image=good(run(C,changed.encode()))
        if image==baseline or image!=bootstrap.assemble(changed):raise AssertionError('compiler source change ignored')
        exe=tmp/'changed-compiler';exe.write_bytes(image);exe.chmod(0o755)
        result=run(exe,b'imm 0 60\nimm 7 42\nsyscall\n')
        if result.returncode!=7 or result.stdout!=bootstrap.assemble('imm 0 60\nimm 7 42\nsyscall\n'):raise AssertionError('compiled source behavior did not change')
        report['changed_source_compilation']=True
        for malformed in (b'imm 16 0',b'imm 0 18446744073709551616',b'imm 0 -9223372036854775809',
                          b'label x\nlabel x\nret',b'jmp absent',b'unknown',b'db 256',b'bss\nspace 8388609',
                          b'imm 0 1\0ret',b'a'*64,b'qubits32\nqh 32',b'qubits32\nimm 0 1',b'qh 0'):
            result=run(C,malformed)
            if result.returncode<=0 or result.stdout:raise AssertionError(('compiler failed refusal',malformed,result))
        programs=[]
        for depth in (1,2,4,8,16):programs.append(nested_program(depth))
        for _ in range(45):
            ops=[]
            for _ in range(rng.randint(1,24)):
                op=rng.randrange(1,8);a=rng.randrange(32);b=(a+rng.randrange(1,32))%32 if op==4 else 0
                ops.append((op,a,b,0))
            programs.append(ops+[(0,0,0,0)])
        programs.append([(1,0,0,0),(8,0,0,0),(16,1,5,3),(7,0,0,0),(0,0,0,0),(8,0,0,0),(9,31,0,0),(17,0,0,0)])
        for index,ops in enumerate(programs):
            packet=good(run(C,quantum_source(ops)))
            if packet!=seed(ops):raise AssertionError('native quantum compilation differs from independent format')
            journal=good(run(VM,packet));original,frames,direction=unpack_journal(journal)
            if original!=packet or direction or reference(packet,frames)!=frames:raise AssertionError(('canonical machine oracle',index))
            report['quantum_programs']+=1;report['full_frame_comparisons']+=len(frames)
            report['maximum_nested_depth']=max(report['maximum_nested_depth'],max(struct.unpack_from('<Q',f,24)[0] for f in frames))
            reversed_history=good(run(UNDO,journal));restored,backward,flag=unpack_journal(reversed_history)
            if restored!=packet or flag!=1 or backward!=frames[::-1]:raise AssertionError('complete reverse journal differs')
            if good(run(UNDO,reversed_history))!=journal:raise AssertionError('native history involution')
            if good(run(UNDO,reversed_history,'seed'))!=packet:raise AssertionError('native complete seed restoration')
            if good(run(UNDO,reversed_history,'state'))!=frames[0]:raise AssertionError('native initial machine restoration')
            report['native_inverse_roundtrips']+=1
            if index==1:
                (R/'evidence/nested_machine.seed').write_bytes(packet)
                (R/'evidence/nested_machine.history').write_bytes(journal)
                (R/'evidence/nested_machine.reversed.history').write_bytes(reversed_history)
                report['recorded_example']={'seed_sha256':sha(packet),'history_sha256':sha(journal),'reverse_sha256':sha(reversed_history)}
                sample_journal=journal
            if any(op[0]==8 for op in ops):
                (R/'evidence/entropy_machine.seed').write_bytes(packet)
                (R/'evidence/entropy_machine.history').write_bytes(journal)
                (R/'evidence/entropy_machine.reversed.history').write_bytes(reversed_history)
                report['hardware_entropy_transitions_recorded']=sum(op[0]==8 for op in ops)
        # Preserve the actual original-source quantum state through the new compiler.
        snapshot=json.loads((R/'examples/States/closed_routine.qstate.json').read_text())
        rows=[(1<<i,0,0) for i in range(32)]+[(0,1<<i,0) for i in range(32)]
        for i in range(5):rows[i]=tuple(snapshot['rows'][i]);rows[32+i]=tuple(snapshot['rows'][5+i])
        ops=[(1,0,0,0),(4,0,31,0),(2,31,0,0),(0,0,0,0)]
        packet=good(run(C,quantum_source(ops,rows=rows)));journal=good(run(VM,packet))
        _,frames,_=unpack_journal(journal)
        if packet!=seed(ops,rows=rows) or reference(packet,frames)!=frames:raise AssertionError('source-linked quantum admission')
        if good(run(UNDO,journal,'seed'))!=packet:raise AssertionError('source-linked seed restore')
        (R/'examples/States/closed_routine_machine.anf').write_bytes(quantum_source(ops,rows=rows))
        (R/'examples/States/closed_routine_machine.seed').write_bytes(packet)
        report['preserved_source_state_admission']=True
        # Execute fresh hardware-coupled quantum seeds through twelve actual
        # generations, then restore the complete recorded history back to seed 0.
        loop_ops=[(1,0,0,0),(4,0,31,0),(8,0,0,0),(9,31,0,0),(0,0,0,0)]
        first=good(run(C,quantum_source(loop_ops)))
        seeds=[first];histories=[];chain=[]
        directory=R/'evidence/seed_generations';directory.mkdir(exist_ok=True)
        for generation in range(12):
            history=good(run(VM,seeds[-1]));packet,frames,_=unpack_journal(history)
            if reference(packet,frames)!=frames:raise AssertionError('seed generation oracle differs')
            next_seed=good(run(UNDO,history,'next'))
            if next_seed==packet:raise AssertionError('computed next seed did not change')
            final=frames[-1]
            if next_seed[64+1024:64+2560]!=final[1024:2560] or next_seed[96:104]!=final[32:40]:raise AssertionError('next seed lost quantum/entropy state')
            histories.append(history);seeds.append(next_seed)
            (directory/f'generation_{generation:02}.history').write_bytes(history)
            chain.append({'generation':generation,'seed_sha256':sha(packet),'history_sha256':sha(history),'next_seed_sha256':sha(next_seed)})
        for generation in reversed(range(12)):
            reversed_history=good(run(UNDO,histories[generation]))
            if good(run(UNDO,reversed_history,'seed'))!=seeds[generation]:raise AssertionError('complete cross-generation seed restoration failed')
        (directory/'seed_00.seed').write_bytes(seeds[0]);(directory/'seed_12.seed').write_bytes(seeds[-1])
        report['native_seed_generations']=12;report['complete_seed_history_restorations']=12
        report['seed_generation_chain']=chain
        # Deny invalid code views, parent escape, duplicate ownership, excessive
        # nesting, fuel exhaustion, illegal operands and malformed seed state.
        invalid=[[(17,0,0,0)],[(99,0,0,0)],[(1,32,0,0)],[(4,0,0,0)],[(0,1,0,0)],
                 [(16,1,1,1),(0,0,0,0)],[(16,1,2,2),(0,0,0,0),(16,1,2,2),(17,0,0,0)],
                 [(16,1,2,2),(0,0,0,0),(16,2,1,1),(17,0,0,0)],nested_program(17)]
        for ops in invalid:
            result=run(VM,seed(ops))
            if result.returncode!=74 or result.stdout:raise AssertionError(('machine accepted invalid program',ops,result.returncode))
            report['machine_refusals']+=1
        result=run(VM,seed([(1,0,0,0),(0,0,0,0)],gas=1))
        if result.returncode!=74 or result.stdout:raise AssertionError('fuel exhaustion accepted')
        report['machine_refusals']+=1
        bad=bytearray(seed([(0,0,0,0)]));struct.pack_into('<Q',bad,64+1024,1<<32);struct.pack_into('<Q',bad,40,fnv(bad[64:]))
        result=run(VM,bad)
        if result.returncode!=74 or result.stdout:raise AssertionError('out-of-range state accepted')
        report['machine_refusals']+=1
        for _ in range(256):
            corrupt=bytearray(sample_journal);pos=rng.randrange(len(corrupt));corrupt[pos]^=1<<rng.randrange(8)
            result=run(UNDO,corrupt)
            if result.returncode!=74 or result.stdout:raise AssertionError(('history corruption accepted',pos))
            report['journal_bit_refusals']+=1
        # A recomputed checksum cannot hide an invalid quantum predecessor or a
        # transition whose recorded opcode differs from its seed instruction.
        packet,frames,_=unpack_journal(sample_journal);frame0=64+len(packet)
        for offset in (frame0+4096+1024,frame0+4096+40):
            corrupt=bytearray(sample_journal);corrupt[offset]^=1
            struct.pack_into('<Q',corrupt,40,fnv(corrupt[64:]))
            result=run(UNDO,corrupt)
            if result.returncode!=74 or result.stdout:raise AssertionError('invalid inverse proof accepted')
            report['semantic_journal_refusals']+=1
    report['status']='PASS'
    (R/'evidence/native_machine_acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
