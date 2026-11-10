#!/usr/bin/env python3
"""Independent NativeQuantum/QVU native assembly regression; Python is test-only.

Neither the compiler, runtime nor desktop Studio imports or invokes this file.
"""
import ctypes
from math import isqrt
import os
from pathlib import Path
import random
import re
import struct
import subprocess
import tempfile
import unittest
from math import isqrt

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / 'native/dense/bin'
SDK = ROOT / 'native/dense/sdk/libnative_quantum_abi.so'
FNV_INIT = 0xcbf29ce484222325
FNV_P = 0x100000001b3
MASK = (1 << 64) - 1
Q30 = 1 << 30
SQRT_HALF = 759250125

def call(*args, check=True):
    r = subprocess.run(list(map(str,args)), text=True, capture_output=True, timeout=20)
    if check and r.returncode:
        raise AssertionError(f'exit={r.returncode} args={args}: {r.stdout} {r.stderr}')
    return r

def fnv64(data):
    h=FNV_INIT
    for b in data: h=((h^b)*FNV_P)&MASK
    return h

def qmul(x): return (x*SQRT_HALF)>>30

def decode(blob):
    assert len(blob)>=64
    magic,version,nq,nc,nops,flags,seedtag,checksum,reserved = struct.unpack('<4sIIIIIQQQ',blob[:48])
    assert magic==b'QVU1' and version==1 and flags==1 and reserved==0
    assert len(blob)==48+16*nops
    assert checksum==fnv64(blob[48:])
    records=[]
    for i in range(nops):
        op,q0,q1,c0,p,f,r=struct.unpack('<BBBBiII',blob[48+16*i:64+16*i])
        records.append((op,q0,q1,c0,p,f,r))
    return nq,nc,seedtag,records

def statehash(state):
    return f'{fnv64(b"".join(struct.pack("<qq",r,i) for r,i in state)):016x}'

def oracle(nq,records,draws):
    state=[(0,0)]*(1<<nq)
    state[0]=(Q30,0)
    classic=0;dpos=0;hashes=[];outcomes=[]
    def single(op,q):
        nonlocal state
        mask=1<<q
        if op<=3:
            for i in range(len(state)):
                if i&mask:continue
                j=i|mask
                ar,ai=state[i];br,bi=state[j]
                if op==1:state[i]=(qmul(ar+br),qmul(ai+bi));state[j]=(qmul(ar-br),qmul(ai-bi))
                elif op==2:state[i]=(br,bi);state[j]=(ar,ai)
                else:state[i]=(bi,-br);state[j]=(-ai,ar)
        else:
            for i in range(len(state)):
                if not i&mask:continue
                ar,ai=state[i]
                if op==4:state[i]=(-ar,-ai)
                elif op==5:state[i]=(-ai,ar)
                elif op==6:state[i]=(ai,-ar)
                elif op==7:state[i]=(qmul(ar-ai),qmul(ar+ai))
                elif op==8:state[i]=(qmul(ar+ai),qmul(ai-ar))
                else:raise AssertionError(op)
    for op,q,q1,c,p,flags,reserved in records:
        assert not flags and not reserved
        if 1<=op<=8:single(op,q)
        elif op==9:
            for i in range(len(state)):
                if i&(1<<q) and not i&(1<<q1):
                    j=i|(1<<q1)
                    state[i],state[j]=state[j],state[i]
        elif op==10:
            for i in range(len(state)):
                if i&(1<<q) and i&(1<<q1):
                    a,b=state[i];state[i]=(-a,-b)
        elif op in (11,12):
            draw=draws[dpos];dpos+=1
            p0=sum(a*a+b*b for i,(a,b) in enumerate(state) if not i&(1<<q))
            p1=sum(a*a+b*b for i,(a,b) in enumerate(state) if i&(1<<q))
            outcome=int(draw < (p1<<32)//(p0+p1))
            selected=p1 if outcome else p0
            assert selected>0
            scale=(1<<60)//isqrt(selected)
            state=[((a*scale)>>30,(b*scale)>>30) if int(bool(i&(1<<q)))==outcome else (0,0) for i,(a,b) in enumerate(state)]
            if op==11:classic=(classic&~(1<<c))|(outcome<<c)
            elif outcome:single(2,q)
            outcomes.append(outcome)
        elif op in (13,14):
            if ((classic>>c)&1)==int(op==13):single(p,q)
        elif op==15:
            for _ in range(p&7):single(7,q)
        elif op!=16:raise AssertionError(op)
        hashes.append(statehash(state))
    assert dpos==len(draws)
    amplitudes={i:(a,b) for i,(a,b) in enumerate(state) if a or b}
    norm=sum(a*a+b*b for a,b in state)
    return hashes,classic,norm,amplitudes,outcomes

def parse_output(text):
    step=[];draws=[];outcomes=[];amplitudes={};last=None
    for line in text.splitlines():
        if line.startswith('QVU_STEP '):step.append(re.search(r'hash=([0-9a-f]{16})',line).group(1))
        if line.startswith('QVU_MEASURE '):
            draws.append(int(re.search(r'draw=(\d+)',line).group(1)))
            outcomes.append(int(re.search(r'outcome=(\d+)',line).group(1)))
        if line.startswith('QVU_FINAL '):
            last=dict((k,int(v)) for k,v in re.findall(r'(qubits|operations|classical|norm)=(\d+)',line))
        if line.startswith('QVU_AMP '):
            m=re.search(r'index=(\d+) re=(-?\d+) im=(-?\d+)',line)
            amplitudes[int(m.group(1))]=(int(m.group(2)),int(m.group(3)))
    assert last is not None
    return step,draws,outcomes,last,amplitudes

class NativeNativeQuantum(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dll=ctypes.CDLL(str(SDK))
        for fn in ('qvu_abi_packet_validate','qvu_abi_seed_validate'):
            f=getattr(cls.dll,fn)
            f.argtypes=[ctypes.c_void_p,ctypes.c_uint64]
            f.restype=ctypes.c_int
        cls.tmp=tempfile.TemporaryDirectory(prefix='native_quantum-native-test-')
        cls.root=Path(cls.tmp.name)
        cls.seed=cls.root/'seed.qseed'
        call(BIN/'native_q_seed',cls.seed)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    @classmethod
    def check_blob(cls,blob):
        b=ctypes.create_string_buffer(bytes(blob))
        return cls.dll.qvu_abi_packet_validate(b,len(blob))
    def compile(self,source):
        ix=next(self.counter)
        src=self.root/f'case_{ix}.ql';pkt=self.root/f'case_{ix}.qvb'
        src.write_text(source)
        result=call(BIN/'native_q_compile',src,self.seed,pkt)
        return pkt,pkt.read_bytes()
    counter=iter(range(20000))
    def test_01_seed_provenance_exclusive_create(self):
        blob=self.seed.read_bytes()
        self.assertEqual(len(blob),64)
        v=ctypes.create_string_buffer(blob)
        self.assertEqual(self.dll.qvu_abi_seed_validate(v,64),0)
        self.assertNotEqual(call(BIN/'native_q_seed',self.seed,check=False).returncode,0)
        self.assertEqual(self.seed.read_bytes(),blob)
        self.assertEqual(blob[:7], b'QSEED01')
        vendor=next(line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('vendor_id'))
        self.assertEqual(blob[48:60].decode('ascii'),vendor)
        altered=bytearray(blob);altered[12]=0
        self.assertNotEqual(self.dll.qvu_abi_seed_validate(ctypes.create_string_buffer(bytes(altered)),64),0)
    def test_02_comptime_repeat_and_resource_guards(self):
        src='qubits 7\ncbits 2\nCOMPTIME REQUIRE_QUBITS 7\nCOMPTIME REQUIRE_CBITS 2\nCOMPTIME REPEAT 4 H 0\nT 6\nCX 0 6\nMEASURE 6 1\n'
        packet,blob=self.compile(src)
        nq,nc,tag,records=decode(blob)
        self.assertEqual((nq,nc,len(records)),(7,2,7))
        self.assertEqual([r[0] for r in records],[1,1,1,1,7,9,11])
        self.assertEqual(self.check_blob(blob),0)
        self.assertIn('QVU_INSPECT_PASS',call(BIN/'native_q_inspect',packet).stdout)
        for bad in ('COMPTIME REPEAT 1 H 0','COMPTIME REPEAT 65 H 0','COMPTIME REQUIRE_QUBITS 8','COMPTIME REQUIRE_CBITS 3','COMPTIME REPEAT 5 UNKNOWN 0'):
            r=call(BIN/'native_q_compile',self._temp_source('qubits 7\ncbits 2\n'+bad+'\n'),self.seed,self.root/f'fail_{next(self.counter)}.qvb',check=False)
            self.assertNotEqual(r.returncode,0,bad)
    def _temp_source(self,text):
        p=self.root/f'source_{next(self.counter)}.ql';p.write_text(text);return p
    def test_03_native_assembly_packet_ir_mutations(self):
        packet,blob=self.compile('qubits 7\ncbits 2\nH 0\nT 1\nCX 0 6\nMEASURE 6 1\nIF1 1 X 2\nRZ8 3 -4\nBARRIER\n')
        self.assertEqual(self.check_blob(blob),0)
        self.assertEqual(call(BIN/'native_q_inspect',packet).returncode,0)
        for off in (0,4,8,12,16,20,32,40,48,49,50,51,52,56,60):
            corrupted=bytearray(blob);corrupted[off]^=(0x80 if off==12 else 1)
            path=self.root/f'corrupt_{off}.qvb';path.write_bytes(corrupted)
            self.assertEqual(self.check_blob(corrupted),-1,off)
            self.assertNotEqual(call(BIN/'native_q_inspect',path,check=False).returncode,0,off)
            self.assertNotEqual(call(BIN/'native_q_execute',path,check=False).returncode,0,off)
        # Semantic mutation WITH recomputed FNV checksum to bypass simple corruption detection.
        for mod in ('bad_op','bad_pair','bad_flags','bad_cbit','bad_reserved'):
            bad=bytearray(blob)
            if mod=='bad_op':bad[48]=99
            elif mod=='bad_pair':bad[48+16*2+2]=0 # CX 0,0
            elif mod=='bad_flags':bad[48+8]=1
            elif mod=='bad_cbit':bad[48+16*3+3]=3
            else:bad[48+12]=1
            struct.pack_into('<Q',bad,32,fnv64(bad[48:]))
            self.assertEqual(self.check_blob(bad),-1,mod)
            p=self.root/f'{mod}.qvb';p.write_bytes(bad)
            self.assertNotEqual(call(BIN/'native_q_execute',p,check=False).returncode,0,mod)
        self.assertEqual(self.check_blob(blob+b'0'),-1)
    def test_04_capacity_target_separation(self):
        p,blob=self.compile('qubits 20\ncbits 2\nH 0\nT 19\nCX 0 19\nMEASURE 19 0\nIF1 0 X 1\n')
        self.assertEqual(self.check_blob(blob),0)
        self.assertIn('QVU_FINAL qubits=20',call(BIN/'native_q_execute',p).stdout)
        p,blob=self.compile('qubits 256\ncbits 32\nH 255\n')
        self.assertEqual(self.check_blob(blob),0)
        self.assertNotEqual(call(BIN/'native_q_execute',p,check=False).returncode,0)
        bad=call(BIN/'native_q_compile',self._temp_source('qubits 257\nH 0\n'),self.seed,self.root/'bad_q.qvb',check=False)
        self.assertNotEqual(bad.returncode,0)
    def test_05_entropic_replay_and_exhaustion(self):
        pkt,blob=self.compile('qubits 8\ncbits 2\nH 0\nT 0\nCX 0 7\nMEASURE 7 1\nIF1 1 X 3\nRESET 0\n')
        live=call(BIN/'native_q_execute',pkt,'--trace').stdout
        t,draws,outs,last,amps=parse_output(live)
        self.assertEqual(len(draws),2)
        replay_path=self.root/'draws.bin'
        replay_path.write_bytes(struct.pack('<2I',*draws))
        replay=call(BIN/'native_q_execute',pkt,replay_path,'--trace').stdout
        tt,dd,oo,ll,aa=parse_output(replay)
        self.assertEqual((tt,dd,oo,ll,aa),(t,draws,outs,last,amps))
        replay_path.write_bytes(struct.pack('<I',draws[0]))
        self.assertNotEqual(call(BIN/'native_q_execute',pkt,replay_path,'--trace',check=False).returncode,0)
        replay_path.write_bytes(struct.pack('<3I',*draws,0))
        self.assertNotEqual(call(BIN/'native_q_execute',pkt,replay_path,'--trace',check=False).returncode,0)
    def test_06_randomized_independent_q30_oracle(self):
        rng=random.Random(20261103)
        shapes=set();total_ops=0;total_meas=0
        for case in range(110):
            nq=rng.randint(2,9);nc=rng.randint(1,4)
            src=[f'qubits {nq}',f'cbits {nc}',f'COMPTIME REQUIRE_QUBITS {nq}','COMPTIME REPEAT 2 H 0']
            for _ in range(rng.randint(9,25)):
                op=rng.choice(['H','X','Y','Z','S','SDG','T','TDG','CX','CZ','MEASURE','RESET','IF1','IF0','RZ8','BARRIER'])
                q=rng.randrange(nq)
                if op in ('CX','CZ'):src.append(f'{op} {q} {(q+rng.randrange(1,nq))%nq}')
                elif op=='MEASURE':src.append(f'MEASURE {q} {rng.randrange(nc)}')
                elif op=='RESET':src.append(f'RESET {q}')
                elif op in ('IF1','IF0'):src.append(f'{op} {rng.randrange(nc)} {rng.choice(("H","X","T","SDG","Y"))} {q}')
                elif op=='RZ8':src.append(f'RZ8 {q} {rng.randint(-5,5)}')
                elif op=='BARRIER':src.append('BARRIER')
                else:src.append(f'{op} {q}')
            packet,blob=self.compile('\n'.join(src)+'\n')
            self.assertEqual(self.check_blob(blob),0,case)
            nq,nc,tag,records=decode(blob)
            native=call(BIN/'native_q_execute',packet,'--trace').stdout
            step,draws,outs,final,amplitudes=parse_output(native)
            hashes,classic,norm,expect_amp,expected_outcomes=oracle(nq,records,draws)
            self.assertEqual(step,hashes,case)
            self.assertEqual(final['classical'],classic,case)
            self.assertEqual(final['norm'],norm,case)
            self.assertEqual(amplitudes,expect_amp,case)
            self.assertEqual(outs,expected_outcomes,case)
            shapes.add(fnv64(blob[48:]))
            total_ops+=len(records);total_meas+=len(draws)
        self.assertEqual(len(shapes),110)
        print(f'QVU_INDEPENDENT_ORACLE_PASS programs=110 operations={total_ops} measurement_events={total_meas}')

if __name__=='__main__':unittest.main(verbosity=2)
