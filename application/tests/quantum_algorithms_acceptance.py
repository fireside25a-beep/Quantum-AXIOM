#!/usr/bin/env python3
"""Independent offline conformance against the native compiler and x86-64 amplitude executor.
No test harness is linked into or invoked from the shipped native binaries.
"""
import hashlib, json, os, subprocess, sys, tempfile, struct, random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_dense_regression import decode, oracle, parse_output, Q30
R=Path(__file__).resolve().parents[1]
BIN=R/'native/dense/bin'
PROGRAMS=R/'examples/Dense'
OUT=R/'evidence'
SAMPLES=('grover_2','bernstein_vazirani_4','ghz_16','inverse_12','teleport_verified')
EXPECTED={'grover_2':3,'bernstein_vazirani_4':10,'inverse_12':0}
def run(*args):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=30)
 if p.returncode:raise AssertionError((p.returncode,args,p.stdout[-800:],p.stderr[-800:]))
 return p.stdout
def main():
 summary={'status':'FAIL','environment':{'machine':os.uname().machine,'system':os.uname().sysname},'programs':{},'measurement_replays':0,'operation_count':0,'native_compilations':0,'corruption_detection':{},'numerical_claim':'fixed-Q30 classical amplitude calculation; not hardware coherence'}
 with tempfile.TemporaryDirectory(prefix='axiom-acceptance-') as d:
  root=Path(d)
  seed=R/'native/dense/compiled.release_seed.qseed'
  for name in SAMPLES:
   source=PROGRAMS/(name+'.ql'); packet=root/(name+'.qvb')
   run(BIN/'native_q_compile',source,seed,packet)
   data=packet.read_bytes();nq,nc,tag,records=decode(data)
   native=run(BIN/'native_q_execute',packet,'--trace')
   hashes,draws,outcomes,final,amps=parse_output(native)
   exp_hashes,exp_classic,exp_norm,exp_amps,exp_outcomes=oracle(nq,records,draws)
   assert (hashes,final['classical'],final['norm'],amps,outcomes)==(exp_hashes,exp_classic,exp_norm,exp_amps,exp_outcomes),name
   assert abs(final['norm']-Q30**2)<=Q30**2//1000000,(name,final['norm'])
   if name in EXPECTED:assert final['classical']==EXPECTED[name],(name,final)
   if name=='ghz_16':assert final['classical'] in (0,3),final
   if name=='teleport_verified':assert not (final['classical']&4),final
   replay=root/(name+'.draws.u32le');replay.write_bytes(struct.pack('<'+'I'*len(draws),*draws))
   rtext=run(BIN/'native_q_execute',packet,replay,'--trace')
   rh,rd,ro,rf,ra=parse_output(rtext)
   assert (rh,rd,ro,rf,ra)==(hashes,draws,outcomes,final,amps),name
   assert 'QVU_INSPECT_PASS' in run(BIN/'native_q_inspect',packet)
   (OUT/(name+'.native_trace.log')).write_text(native)
   (OUT/(name+'.packet.sha256')).write_text(hashlib.sha256(data).hexdigest()+'  '+name+'.qvb\n')
   # Final no-branch residual is a direct normalized fixed-Q30 numerical invariant.
   summary['programs'][name]={'sites':nq,'operations':len(records),'classical_result':final['classical'],'measurement_events':len(draws),'norm_q60':final['norm'],'absolute_norm_error_q60':abs(final['norm']-Q30**2),'native_vs_independent_oracle':'PASS','bit_exact_entropy_replay':'PASS','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'packet_sha256':hashlib.sha256(data).hexdigest()}
   summary['measurement_replays']+=1;summary['operation_count']+=len(records);summary['native_compilations']+=1
  # All eight bits of every payload byte for a semantically rich 7-op program.
  source=PROGRAMS/'teleport_verified.ql'; packet=root/'mutant_original.qvb'
  run(BIN/'native_q_compile',source,seed,packet)
  raw=packet.read_bytes();assert len(raw)>48
  bitmap=0;runtime_rejected=0
  for off in range(48,len(raw)):
   for bit in range(8):
    b=bytearray(raw);b[off]^=1<<bit;f=root/'faulted.qvb';f.write_bytes(b)
    res=subprocess.run([str(BIN/'native_q_inspect'),str(f)],capture_output=True,timeout=10)
    assert res.returncode!=0,(off,bit,'inspector incorrectly accepted')
    bitmap+=1
    if bit in (0,7) and (off-48)%2==0:
     res=subprocess.run([str(BIN/'native_q_execute'),str(f)],capture_output=True,timeout=10)
     assert res.returncode!=0,(off,bit,'executor incorrectly accepted')
     runtime_rejected+=1
  summary['corruption_detection']={'all_payload_bits_flipped_and_refused_by_native_inspector':bitmap,'mutated_packets_refused_by_native_executor':runtime_rejected,'note':'FNV detects tested accidental changes but is not a cryptographic MAC'}
  summary['status']='PASS'
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/'quantum_algorithms_acceptance.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
