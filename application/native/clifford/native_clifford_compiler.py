#!/usr/bin/env python3
"""Independent offline machine-instruction lowering for the native Clifford32 plane.
Emits a closed Linux ELF64 x86-64 executable and a provenance audit. The emitted
ELF contains no Python, C, language interpreter, or dynamic library dependencies.
This lowering tool is NOT itself a native self-hosting quantum-language compiler.
"""
import argparse
from pathlib import Path
import os, struct, subprocess, json, hashlib
CON=0xDBA79B0B91C21D57
MUL=0x7f4a7c15
ENTRY=0x401000
DATA=0x402000
DATA_LEN=128+768*3
EXE_LEN=0x2000+DATA_LEN
M32=(1<<32)-1

def compile_program(path):
    with Path(path).open('rb') as source:data=source.read(65537)
    if len(data)>65536:raise ValueError('oversized program')
    raw=data.decode('ascii')
    ops=[]; header=False; started=False
    if len(raw)>65536: raise ValueError("oversized program")
    for index,orig in enumerate(raw.splitlines(),1):
        line=orig.split('#',1)[0].strip()
        if not line:continue
        w=line.split(); cmd=w[0].upper()
        if not header:
            if w!=['sites','32']:raise ValueError(f"line {index}: sites 32 required before any gates")
            header=True;continue
        if cmd=='SITES':raise ValueError(f"line {index}: duplicate sites header")
        if cmd=='BARRIER' and len(w)==1:continue
        if cmd in ('H','S','SDG','X','Z','Y') and len(w)==2:
            try:q=int(w[1])
            except ValueError:raise ValueError(f"line {index}: invalid site")
            if str(q)!=w[1] or not 0<=q<32:raise ValueError(f"line {index}: invalid site")
            if cmd=='H':ops.append(('H',q))
            elif cmd=='S':ops.append(('S',q))
            elif cmd=='SDG':ops.extend([('S',q)]*3)
            elif cmd=='Z':ops.extend([('S',q)]*2)
            elif cmd=='X':ops.extend([('H',q),('S',q),('S',q),('H',q)])
            elif cmd=='Y':ops.extend([('H',q),('S',q),('S',q),('H',q),('S',q),('S',q)])
        elif cmd=='CX' and len(w)==3:
            try:a,b=map(int,w[1:])
            except ValueError:raise ValueError(f"line {index}: invalid CX operands")
            if not (0<=a<32 and 0<=b<32 and a!=b and list(map(str,(a,b)))==w[1:]):raise ValueError(f"line {index}: invalid CX operands")
            ops.append(('CX',a,b))
        else:raise ValueError(f"line {index}: unsupported gate or wrong arity")
        if len(ops)>70:raise ValueError("maximum 70 lowered elementary gates per image")
    if not header or not ops:raise ValueError("empty program")
    return ops

PROGRAM_SOURCE=__import__('sys').argv[1] if len(__import__('sys').argv)>1 else None
if not PROGRAM_SOURCE:raise SystemExit("usage: python3 native_clifford_compiler.py SOURCE.qcl OUTPUT.x86_64 [AUDIT.json]")
if len(__import__('sys').argv)>5:raise SystemExit('unexpected compiler arguments')
STATE_PATH=Path(__import__('sys').argv[4]) if len(__import__('sys').argv)>4 else None
class Bits:
 def __init__(self):self.code=bytearray();self.labels={};self.fix=[];self.audit=[]
 def op(self,descr,words):
  raw=bytes.fromhex(words);self.audit.append((len(self.code),descr,raw.hex()));self.code+=raw
 def u32(self,descr,pre,num):self.op(descr,pre+struct.pack('<I',num).hex())
 def u64(self,descr,pre,num):self.op(descr,pre+struct.pack('<Q',num).hex())
 def label(self,name):
  if name in self.labels:raise ValueError('duplicate '+name)
  self.labels[name]=len(self.code)
 def j(self,descr,target,opcode='0f85'):
  op=bytes.fromhex(opcode);off=len(self.code);self.code+=op+b'\0'*4
  self.fix.append((off,len(op),target,descr))
 def finalize(self):
  for off,n,target,descr in self.fix:
   if target not in self.labels:raise ValueError('missing '+target)
   d=self.labels[target]-(off+n+4);struct.pack_into('<i',self.code,off+n,d)
   self.audit.append((off,descr,bytes(self.code[off:off+n+4]).hex()))
  return bytes(self.code)
A=Bits()
TABLE=DATA+128
TABLE1=TABLE+768
TABLE2=TABLE+1536
OPS=compile_program(PROGRAM_SOURCE)
# Decode per-record error correcting three-lane majority of 32 sites with
# pos/neg ternary bitplanes. No float, language AST, bytecode, or VM.
A.u64('RW logical-state base','48be',DATA)
A.u64('expected resident ABI magic','48b8',0x2136385844454553)
A.op('validate resident ABI magic','483906')
A.j('reject invalid resident header','fault')
A.op('validate 32 sites','48837e5020')
A.j('reject invalid resident site count','fault')
A.op('validate format generation 1','48837e5801')
A.j('reject unknown resident format','fault')
A.op('reject generation counter wraparound','48837e08ff')
A.j('reject saturated generation counter','fault','0f84')
A.op('read encoded 64-site bitplanes, three redundant lanes','4c8b66104c8b6e184c8b7620')
A.op('majority lane0&lane1 | lane0&lane2 | lane1&lane2',
 '4c89e04c21e84c89e34c21f34809d84c89eb4c21f34809d8')
A.op('keep corrected logical state in r15','4989c7')
# Authenticated within native state against *accidental* corruption; not cryptographic against adversaries.
A.op('read recorded generation epoch','4c8b4608')
A.op('begin syndrome-integrity accumulator','4c89c0')
A.u32('spread generation epoch to integrity tag','4869c0',MUL)
A.op('fold corrected physical state into accumulator','4c31f8')
A.u64('integrity constant','49bb',CON)
A.op('xor integrity constant','4c31d8')
A.op('check exact tag','483b4628')
A.j('reject corrupt integrity','fault')
A.op('complement accumulator','4889c248f7d2')
A.op('check complementary tag','483b5630')
A.j('reject corrupt complement','fault')
A.op('reject invalid ternary site with positive and negative both set',
 '4489fa4c89fb48c1eb2021da')
A.j('reject invalid ternary site','fault')


# Full-tableau *correction* BEFORE hash validation: 192 native 32-bit words
# in each of three independent SRAM-resident redundant memory lanes.
A.u64('ECC tableau replica A','48be',TABLE)
A.u64('ECC tableau replica B','48bf',TABLE1)
A.u64('ECC tableau replica C','48ba',TABLE2)
A.u32('64 rows x 3 fields = 192 word majority cycles','b9',192)
A.label('tableau_ecc_loop')
A.op('load a,b,c 32-bit full-tableau words','8b06448b07448b0a')
A.op('majority (a&b)|(a&c)|(b&c)',
     '4189c24521c24189c34521cb4509da4521c84509c2')
A.op('repair all three physical-memory tableau lanes','448916448917448912')
A.op('advance independent tableau word cursors','4883c6044883c7044883c20448ffc9')
A.j('ECC all 192 words','tableau_ecc_loop')

# Fault detection for full 32-site Pauli tableau (64 symplectic descriptor rows).
# Ternary state has triple-replica error correction; full tableau is checksum guarded.
A.u64('tableau input at machine resident state page','48be',TABLE)
A.u32('initial FNV hash for 64x3-word tableau','b8',0x811c9dc5)
A.u32('tableau byte count','b9',768)
A.label('check_tableau')
A.op('tableau next byte','0fb616')
A.op('xor and multiply FNV1a of tableau','31d069c093010001')
A.op('move to next state byte','48ffc6ffc9')
A.j('check all tableau bytes','check_tableau')
A.u64('record header address for tableau digest','48be',DATA)
A.op('compare full tableau integrity','3b4660')
A.j('reject corrupted tableau','fault')
A.op('validate inverse 32-bit digest','f7d03b4668')
A.j('reject corrupt complement tableau','fault')

# CPUID leaf 7 EBX bit18 checks actual silicon RDSEED (rather than pretending entropy).
A.op('require CPUID basic leaf 7','31c00fa283f807')
A.j('missing CPU feature leaf','no_entropy','0f82')
A.op('CPUID leaf 7 feature test','b80700000031c90fa2')
A.op('test hardware RDSEED availability','0fbae312')
A.j('require hardware RDSEED source','no_entropy','0f83')
A.op('max bounded hardware RDSEED retries','b940000000')
A.label('entropy_try')
A.op('hardware RDSEED rax, CF signals success','480fc7f8')
A.j('hardware entropy obtained','entropy_ok','0f82')
A.op('PAUSE between bounded silicon entropy retries','f390ffc9')
A.j('retry bounded entropy acquisition','entropy_try')
A.j('hardware entropy unavailable: fail closed','no_entropy','e9')
A.label('entropy_ok')
A.op('retain previous majority state in r10','4d89fa')
A.op('nonbyte state change mixing prior ternary site pattern','4c89fb4889d948d1c14831cb')
A.op('physical entropy 17-bit rotation coupling','4889c148c1c9114831cb4831c3')
A.op('spatial mixing 23-site ring rotation','4889da48c1c2174831d3')
# Positive cell plane and negative cell plane cannot overlap.
A.op('candidate positive sites from ring XOR','89da89d9c1c90b4189d1f7d121ca')
A.op('candidate negative sites disjoint via inverted candidate','89d9c1c10741f7d14421c9')
A.op('upper 32-site negative plane / lower 32-site positive plane','48c1e1204809ca')
A.op('new 32-site three-valued state','4989d7')
A.op('new syndrome (changed physical-site bitplanes)','4c89fa4c31d2')
A.op('write syndrome, hardware entropy, advance generation','488956404889463848ff4608')
A.op('repair all three lanes with agreed new state','4c897e104c897e184c897e20')
A.op('next generation integrity tag','488b46084869c0'+struct.pack('<I',MUL).hex()+'4c31f8')
A.u64('next integrity constant','49bb',CON)
A.op('next integrity tag and inverse','4c31d84889462848f7d048894630')
A.op('rolling lineage commit from current state, last sample and prior hash',
 '488b5e4848c1c3054c31fb48335e3848895e48')

# Compiled native 32-site Clifford bitplane engine integrated in EACH
# descendant. Gates correspond to specified H/S/CX conjugation semantics.
A.u64('canonical 64-row tableau resident base','48be',TABLE)
A.u32('64 canonical symplectic tableau rows','b9',64)
A.label('tableau_row')
A.op('load Pauli X Z and phase from same resident row','8b068b5e048b5608')
def bit_H(q):
 mask=1<<q
 A.op(f'H({q}) overlap x and z','4189c04121d8')
 A.u32(f'H({q}) target mask','4181e0',mask)
 A.op('overlap shifts row phase 2','4585c0410f95c0450fb6c04401c24401c283e203')
 A.op('swap X and Z at selected site','4189c04131d8')
 A.u32(f'H({q}) exchange mask','4181e0',mask)
 A.op('rewrite Pauli X,Z','4431c04431c3')
def bit_S(q):
 mask=1<<q
 A.op(f'S({q}) phase from X','4189c0')
 A.u32(f'S({q}) select X','4181e0',mask)
 A.op('increase Pauli phase mod4','4585c0410f95c0450fb6c04401c283e203')
 A.op('select Z update from X','4189c0')
 A.u32(f'S({q}) mask','4181e0',mask)
 A.op('Z xor X','4431c3')
def bit_CX(c,t):
 assert c!=t and 0<=c<32 and 0<=t<32
 A.op(f'CX({c},{t}) control X','4189c0')
 A.u32(f'CX({c},{t}) mask control X','4181e0',1<<c)
 A.op(f'CX({c},{t}) shift control X into target',('41c1e0' if c<t else '41c1e8')+bytes([abs(t-c)]).hex())
 A.op('X target xor control','4431c0')
 A.op(f'CX({c},{t}) target Z','4189d8')
 A.u32(f'CX({c},{t}) mask target Z','4181e0',1<<t)
 A.op(f'CX({c},{t}) shift target Z into control',('41c1e0' if t<c else '41c1e8')+bytes([abs(t-c)]).hex())
 A.op('Z control xor target','4431c3')
for gate in OPS:
 if gate[0]=='H':bit_H(gate[1])
 elif gate[0]=='S':bit_S(gate[1])
 else:bit_CX(*gate[1:])
A.op('store each transformed Pauli row','8906895e04895608')
A.op('next row of Pauli conjugation algebra','4883c60c48ffc9')
A.j('next of 64 independent Pauli rows','tableau_row')

# Native 768-byte copies rebuild the two redundant tableau lanes from the
# newly transformed correct primary tableau; subsequent generations validate
# and correct any one lane before use.
A.u64('copy updated tableau to redundancy lane B: source','48be',TABLE)
A.u64('copy updated tableau to redundancy lane B: target','48bf',TABLE1)
A.u32('rep movsq 96 words for lane B','b9',96)
A.op('native duplicate lane B','f348a5')
A.u64('copy updated tableau to redundancy lane C: source','48be',TABLE)
A.u64('copy updated tableau to redundancy lane C: target','48bf',TABLE2)
A.u32('rep movsq 96 words for lane C','b9',96)
A.op('native duplicate lane C','f348a5')

# Recompute checksum after native 32-site operation, no library call.
A.u64('tableau hash source base','48be',TABLE)
A.u32('tableau FNV initial','b8',0x811c9dc5)
A.u32('tableau length','b9',768)
A.label('hash_next_tableau')
A.op('read current source-bitplane byte and FNV transform','0fb61631d069c09301000148ffc6ffc9')
A.j('finish Pauli state checksum','hash_next_tableau')
A.u64('header base of self','48be',DATA)
A.op('store committed checksum','894660f7d0894668')

# In the native instruction sequence the machine has no syscall except (later) write and exit.
# Stackable seccomp BPF: kill every syscall except write and exit.
# Strict mode cannot be installed when the host already has a seccomp filter.
A.op('PR_SET_NO_NEW_PRIVS 1','b89d000000bf26000000be0100000031d24531d24531c00f05')
A.op('check no-new-privileges result','85c0')
A.j('reject sandbox establishment failure','fault')
A.op('SECCOMP_SET_MODE_FILTER (stackable)','b83d010000bf0100000031f6')
A.u64('RX sock_fprog address','48ba',0x401f80)
A.op('install syscall allowlist','0f05')
A.op('check sandbox establishment','85c0')
A.j('reject sandbox establishment failure','fault')
A.op('write direct resident native instruction image syscall','b801000000bf01000000')
A.u64('mapped self executable image','48be',0x400000)
A.u32('resident machine-image length','ba',EXE_LEN)
A.op('write self next-generation native machine image','0f05')
A.u32('check exact native image emitted','483d',EXE_LEN)
A.j('refuse partial output','fault')
A.op('exit success','31ffb83c0000000f05')
A.label('no_entropy')
A.op('exit=66 hardware entropy unavailable','bf42000000b83c0000000f05')
A.label('fault')
A.op('exit=74 corrupted bit-state or unsupported sandbox','bf4a000000b83c0000000f05')
code=A.finalize()
if len(code)>0xf00:raise ValueError('native code too large for RX filter reserve')
code_length=len(code)
# Classic BPF: validate native arch, then allow only write(1)/exit(60).
# All other calls (including x32 and incompatible arches) kill this process.
def bpf(op,jt,jf,k):return struct.pack('<HBBI',op,jt,jf,k)
filter_bytes=b''.join([bpf(0x20,0,0,4),bpf(0x15,1,0,0xc000003e),
 bpf(0x06,0,0,0x80000000),bpf(0x20,0,0,0),bpf(0x15,2,0,1),
 bpf(0x15,1,0,60),bpf(0x06,0,0,0x80000000),bpf(0x06,0,0,0x7fff0000)])
code=code.ljust(0xf00,b'\0')+filter_bytes
code=code.ljust(0xf80,b'\0')+struct.pack('<H6xQ',len(filter_bytes)//8,0x401f00)
print('machine instruction region',len(code))
# Two segment, ELF64 x86-64 Linux. RW segment may only modify state.
def tag(state,epoch):return (state^((epoch*MUL)&((1<<64)-1))^CON) & ((1<<64)-1)
def fnv(bs):
 h=0x811c9dc5
 for b in bs:h=((h^b)*0x01000193)&0xffffffff
 return h
def load_initial_rows(path):
 canonical=[(1<<i,0,0) for i in range(32)]+[(0,1<<i,0) for i in range(32)]
 if path is None:return canonical,None
 with path.open('rb') as source:raw=source.read(16385)
 if len(raw)>16384:raise ValueError('tableau snapshot exceeds 16384 bytes')
 def object_pairs(pairs):
  obj={}
  for key,value in pairs:
   if key in obj:raise ValueError('duplicate tableau snapshot key')
   obj[key]=value
  return obj
 obj=json.loads(raw,object_pairs_hook=object_pairs)
 if type(obj) is not dict or set(obj)!={'format','sites','rows'} or obj['format']!='AXIOM_TABLEAU_STATE_1':raise ValueError('unknown tableau snapshot format')
 n=obj['sites'];rows=obj['rows']
 if type(n) is not int or not 1<=n<=32 or type(rows) is not list or len(rows)!=2*n:raise ValueError('invalid tableau dimensions')
 for row in rows:
  if type(row) is not list or len(row)!=3 or any(type(v) is not int for v in row):raise ValueError('noninteger tableau row')
  x,z,p=row
  if not (0<=x<1<<n and 0<=z<1<<n and 0<=p<=3):raise ValueError('tableau field out of range')
  if p%2!=(x&z).bit_count()%2:raise ValueError('non-Hermitian tableau generator')
 for i,(x,z,_) in enumerate(rows):
  for j in range(i+1,2*n):
   a,b,_=rows[j]
   if ((x&b).bit_count()+(z&a).bit_count())%2!=int(i<n and j==i+n):raise ValueError('invalid tableau symplectic basis')
 for i in range(n):
  canonical[i]=tuple(rows[i]);canonical[32+i]=tuple(rows[n+i])
 return canonical,{'format':obj['format'],'source_file':path.name,'sha256':hashlib.sha256(raw).hexdigest(),'source_sites':n,'extension_sites':32-n,'validation':'bounded canonical JSON, integer bounds, Hermiticity, all symplectic pairs'}
INITIAL_ROWS,STATE_IMPORT=load_initial_rows(STATE_PATH)
def pack_state(epoch,state,entropy=0,syndrome=0,lineage=0,corrupt=None):
 assert (state&0xffffffff)&(state>>32)==0
 b=bytearray(DATA_LEN)
 # Source-defined tableau core: 32 X generators + 32 Z generators.
 canonical=INITIAL_ROWS
 for lane in range(3):
  for i,row in enumerate(canonical):struct.pack_into('<III',b,128+lane*768+12*i,*row)
 v=fnv(b[128:128+768]);struct.pack_into('<I',b,96,v);struct.pack_into('<I',b,104,(~v)&0xffffffff)
 b[:8]=b'SEEDX86!'
 struct.pack_into('<Q',b,8,epoch)
 for off in (16,24,32):struct.pack_into('<Q',b,off,state)
 t=tag(state,epoch)
 struct.pack_into('<QQQQQ',b,40,t,(~t)&((1<<64)-1),entropy,syndrome,lineage)
 struct.pack_into('<QQ',b,80,32,1) # number of ternary physical-history sites, format generation
 if corrupt:
  for offset,mask in corrupt: b[offset]^=mask
 return b

def elf(imagecode,databytes):
 full=bytearray(EXE_LEN)
 full[:16]=b'\x7fELF'+bytes([2,1,1,0,0])+b'\0'*7
 struct.pack_into('<HHIQQQIHHHHHH',full,16,2,62,1,ENTRY,64,0,0,64,56,2,0,0,0)
 struct.pack_into('<IIQQQQQQ',full,64,1,5,0,0x400000,0x400000,0x1000+len(imagecode),0x1000+len(imagecode),4096)
 struct.pack_into('<IIQQQQQQ',full,120,1,6,0x2000,DATA,DATA,len(databytes),0x1000,4096)
 full[0x1000:0x1000+len(imagecode)]=imagecode
 full[0x2000:0x2000+len(databytes)]=databytes
 return bytes(full)

INITIAL=0x01f8e18600051649
image=elf(code,pack_state(0,INITIAL))
assert len(image)==EXE_LEN
out=Path(__import__('sys').argv[2]);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(image);out.chmod(0o700)
report={"source_file":Path(PROGRAM_SOURCE).name,"source_sha256":hashlib.sha256(Path(PROGRAM_SOURCE).read_bytes()).hexdigest(),"native_image_sha256":hashlib.sha256(image).hexdigest(),"code_region_length":code_length,"executable_size":len(image),"lowered_gate_count":len(OPS),"gate_trace":OPS,"instruction_audit":[{"offset":o,"operation":label,"opcode_hex":hx} for o,label,hx in sorted(A.audit)],"format":"ELF64 x86-64, native instruction plane, RX text / RW state; self-emitting via write syscall"}
audit=Path(__import__('sys').argv[3]) if len(__import__('sys').argv)>3 else out.with_suffix('.audit.json')
report['initial_tableau_import']=STATE_IMPORT
audit.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='instruction_audit'}))
