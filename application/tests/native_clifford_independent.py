#!/usr/bin/env python3
"""Offline independent verification: executes generated native machine images, then verifies
complete 64-row symplectic output against a separately written oracle.
No executable in this project invokes this test harness.
"""
import hashlib, json, os, random, re, struct, subprocess, tempfile, time, traceback
from pathlib import Path
R=Path(__file__).resolve().parents[1]
C=R/'native/clifford/native_clifford_compiler.py'
EMITTER=R/'native/seed/native_seed_emitter.x86_64'
MASK32=(1<<32)-1
D=0x2000
ENTRY=0x401000

def sha(x):return hashlib.sha256(x).hexdigest()
def fnv(v):
 h=0x811c9dc5
 for b in v:h=((h^b)*0x1000193)&MASK32
 return h

def parse_file(path):
 # Deliberately independent from source-to-opcode compiler parser.
 lines=[re.sub(r'#.*$', '', s).strip() for s in path.read_text().splitlines()]
 lines=[s.split() for s in lines if s.strip()]
 assert lines.pop(0)==['sites','32']
 ops=[]
 for parts in lines:
  name=parts[0]
  if name=='BARRIER': assert len(parts)==1;continue
  if name=='CX':
   assert len(parts)==3; a,b=map(int,parts[1:]);assert a!=b and 0<=a<32 and 0<=b<32
   ops.append(('CX',a,b));continue
  assert len(parts)==2
  q=int(parts[1]);assert 0<=q<32
  if name in ('H','S'):ops.append((name,q))
  elif name=='SDG':ops += [('S',q)]*3
  elif name=='Z':ops += [('S',q)]*2
  elif name=='X':ops += [('H',q),('S',q),('S',q),('H',q)]
  elif name=='Y':ops += [('H',q),('S',q),('S',q),('H',q),('S',q),('S',q)]
  else:raise AssertionError(name)
 return ops

def apply(rows,ops):
 rows=[list(t) for t in rows]
 for gate in ops:
  for row in rows:
   x,z,p=row
   if gate[0]=='H':
    m=1<<gate[1]
    if (x&m) and (z&m):p=(p+2)&3
    if bool(x&m)!=bool(z&m):x^=m;z^=m
   elif gate[0]=='S':
    m=1<<gate[1]
    if x&m:p=(p+1)&3;z^=m
   else:
    c,t=gate[1:];cm=1<<c;tm=1<<t
    if x&cm:x^=tm
    if z&tm:z^=cm
   row[:]=x,z,p
 return list(map(tuple,rows))

CANONICAL=[(1<<i,0,0) for i in range(32)]+[(0,1<<i,0) for i in range(32)]

def state(image):
 assert len(image)==10624 and image[:4]==b'\x7fELF'
 assert struct.unpack_from('<Q',image,24)[0]==ENTRY
 assert struct.unpack_from('<I',image,68)[0]==5
 assert struct.unpack_from('<I',image,124)[0]==6
 assert image[D:D+8]==b'SEEDX86!'
 epoch=struct.unpack_from('<Q',image,D+8)[0]
 a,b,c=struct.unpack_from('<QQQ',image,D+16)
 assert a==b==c and not ((a&MASK32)&(a>>32))
 table=[image[D+128+j*768:D+128+(j+1)*768] for j in range(3)]
 assert table[0]==table[1]==table[2]
 h=struct.unpack_from('<I',image,D+96)[0]
 assert h==fnv(table[0])
 assert struct.unpack_from('<I',image,D+104)[0]==(~h)&MASK32
 rows=list(struct.iter_unpack('<III',table[0]))
 assert len(rows)==64 and all(0<=x<=MASK32 and 0<=z<=MASK32 and p<=3 for x,z,p in rows)
 return epoch,rows

def preserves_symplectic(rows):
 # Both halves commute separately; complementary generators have canonical anti-commutation.
 for i in range(64):
  a,b,_=rows[i]
  for j in range(i+1,64):
   c,d,_=rows[j]
   observed=((a&d).bit_count()+(b&c).bit_count())&1
   expected=int(i<32 and j==i+32)
   assert observed==expected,(i,j,observed,expected)

def run(image,tmp):
 path=tmp/'kernel';path.write_bytes(image);path.chmod(0o700)
 p=subprocess.run([str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=8)
 return p.returncode,p.stdout

def compile_case(src,tmp,name):
 source=tmp/(name+'.qcl');target=tmp/(name+'.x86_64');audit=tmp/(name+'.json')
 source.write_text(src)
 p=subprocess.run(['python3',str(C),str(source),str(target),str(audit)],capture_output=True,text=True,timeout=12)
 assert p.returncode==0,(name,p.stdout,p.stderr)
 return source,target.read_bytes(),json.loads(audit.read_text())

def bitseed(raw):
 h=fnv(raw)
 encoded=bytes(int(f'{(b^0xa5):08b}'[::-1],2) for b in raw)
 return b'BSTBIT01'+struct.pack('<II',len(raw),h)+encoded*3

def native_emitter_roundtrip(raw):
 payload=bitseed(raw)
 with tempfile.TemporaryFile() as f:
  f.write(payload);f.seek(0)
  p=subprocess.run([str(EMITTER)],stdin=f,capture_output=True,timeout=8)
 assert p.returncode==0 and p.stdout==raw,(p.returncode,len(p.stdout))
 return True

def validate(src,image,ops,tmp):
 old_epoch,old=state(image)
 assert old_epoch==0 and old==CANONICAL
 rc,new=run(image,tmp)
 assert rc==0 and len(new)==len(image),(rc,len(new))
 epoch,actual=state(new)
 assert epoch==1
 predicted=apply(CANONICAL,ops)
 assert actual==predicted
 preserves_symplectic(actual)
 return new

def inverse_ops(ops):
 result=[]
 for op in reversed(ops):
  if op[0]=='S':result.extend([('S',op[1])]*3)
  else:result.append(op)
 return result

def emit_text(ops):
 return 'sites 32\n'+'\n'.join(' '.join(map(str,gate)) for gate in ops)+'\n'

def main():
 t0=time.monotonic()
 report={'status':'IN_PROGRESS','suite':'native code generation + independent symplectic oracle + physical CPU execution',
 'platform':os.uname().sysname+' '+os.uname().machine,'examples':{},'failures':[],
 'native_emitter_self_compilation':False,'randomized_programs':0,'reversal_proofs':0,
 'single_replica_injections':0,'double_replica_refusals':0,'parser_refusals':0,'hostile_syscall_killed':False}
 try:
  with tempfile.TemporaryDirectory(prefix='native-clifford-run-') as d:
   tmp=Path(d)
   child_seed=EMITTER.read_bytes()
   with (R/'native/seed/compiler_self_seed.bits').open('rb') as file:
    p=subprocess.run([str(EMITTER)],stdin=file,capture_output=True,timeout=8)
   assert p.returncode==0 and p.stdout==child_seed
   report['native_emitter_self_compilation']=True
   print('self emitter PASS',flush=True)
   for path in sorted((R/'examples/Clifford32').glob('*.qcl')):
    name=path.stem;print('example',name,flush=True);compiled=(R/'native/clifford'/(name+'.x86_64')).read_bytes()
    audit=json.loads((R/'evidence'/(name+'.lowering.json')).read_text())
    ops=parse_file(path)
    assert [tuple(x) for x in audit['gate_trace']]==ops
    new=validate(path,compiled,ops,tmp)
    native_emitter_roundtrip(compiled)
    report['examples'][name]={'native_compilation':True,'gates':len(ops),'input_sha256':sha(compiled),'generation1_sha256':sha(new),'complete_tableau_oracle':True,'symplectic_pair_invariants':True,'emitter_roundtrip':True}
   rng=random.Random(0xC1A55D)
   for j in range(35):
    if j % 5 == 0:print('randomized',j,flush=True)
    gates=[]
    for k in range(rng.randrange(1,22)):
     kind=rng.choice(['H','S','S','CX','CX','H','X','SDG','Z','Y'])
     q=rng.randrange(32)
     if kind=='CX':
      t=(q+rng.randrange(1,32))%32;gates.append((kind,q,t))
     else:gates.append((kind,q))
    if j>=39:print('random',j,'gates',len(gates),'begin compile',time.monotonic()-t0,flush=True)
    src,image,audit=compile_case(emit_text(gates),tmp,'random_'+str(j))
    if j>=39:print('random',j,'lowered',len(audit['gate_trace']),'begin check',time.monotonic()-t0,flush=True)
    lowered=parse_file(src)
    assert len(lowered)<=70
    assert [tuple(x) for x in audit['gate_trace']]==lowered
    validate(src,image,lowered,tmp)
    if j>=39:print('random',j,'validated',time.monotonic()-t0,flush=True)
    report['randomized_programs']+=1
    if j<10:
     # Clifford gate algebra, including native reversed program (not just oracle inversion).
     inverse=inverse_ops(lowered)
     # Most long random circuits exceed the single-page instruction budget; choose short ones.
     if len(lowered)+len(inverse) <= 60:
      revsource,revimage,_=compile_case(emit_text(lowered+inverse),tmp,'reverse_'+str(j))
      _,out=run(revimage,tmp)
      assert out and state(out)[1]==CANONICAL
      report['reversal_proofs']+=1
   print('randomized done',flush=True)
   # Canonical reverse demonstration for a long 32-site entangling circuit.
   gates=[('H',0)]+[('CX',i,i+1) for i in range(31)]
   reverse=inverse_ops(gates)
   src,rev,_=compile_case(emit_text(gates+reverse),tmp,'ghz_reverse_all')
   _,back=run(rev,tmp)
   assert back and state(back)[1]==CANONICAL
   report['reversal_proofs']+=1
   native_emitter_roundtrip(rev)
   original=(R/'native/seed/genesis.x86_64').read_bytes()
   baseline_rc,baseline_out=run(original,tmp)
   assert baseline_rc==0
   baseline_table=state(baseline_out)[1]
   # Test each replica's single-bit protection across state and full tableau, both ends.
   sample_offsets=[0,7,111,421,767]
   print('start fault injections',flush=True)
   for replica in range(3):
    for offset in sample_offsets:
     for bit in (0,7):
      damaged=bytearray(original)
      damaged[D+128+replica*768+offset] ^= 1<<bit
      rc,new=run(damaged,tmp)
      assert rc==0 and state(new)[1]==baseline_table
      report['single_replica_injections']+=1
   for offset in (0,7,111,421,767):
    damaged=bytearray(original)
    damaged[D+128+offset]^=1
    damaged[D+128+768+offset]^=1
    rc,out=run(damaged,tmp)
    assert rc==74 and out==b'',(rc,len(out))
    report['double_replica_refusals']+=1
   for malformed in ['sites 33\nH 0\n','sites 32\nH 32\n','sites 32\nCX 1 1\n','sites 32\nT 0\n','sites 32\n','sites 32\nCX 0 -1\n','sites 32\nBARRIER x\n','sites 32\nS -2\n']:
    inp=tmp/'invalid.qcl';inp.write_text(malformed)
    res=subprocess.run(['python3',str(C),str(inp),str(tmp/'invalid.native')],capture_output=True,timeout=8)
    assert res.returncode!=0
    report['parser_refusals']+=1
   syscall=bytes.fromhex('b801000000bf01000000')
   assert original.count(syscall)==1
   m=bytearray(original);m[m.index(syscall)+1]=39
   rc,out=run(m,tmp)
   assert rc in (-9,-31) and not out
   report['hostile_syscall_killed']=True
  report['status']='PASS'
 except Exception as exc:
  report['status']='FAIL';report['failures'].append(traceback.format_exc())
 finally:
  report['elapsed_seconds']=round(time.monotonic()-t0,3)
  (R/'evidence/native_clifford_validation.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report,indent=2))
 if report['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
