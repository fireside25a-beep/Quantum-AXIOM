#!/usr/bin/env python3
"""Executed native compiler+runtime evidence checked against a mathematically independent oracle.
The model is verification-only, never a runtime substitute. Uses fixed-seed replay for exact comparison.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,re,struct,subprocess,tempfile,time
R=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location('dense_independent',R/'tests/native_dense_regression.py')
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
B=R/'native/dense/bin'
OUTPUT=R/'evidence'

def run(*args):
 p=subprocess.run([str(x) for x in args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=45)
 assert p.returncode==0,(args,p.returncode,p.stdout[-250:],p.stderr[-250:])
 return p.stdout

def main():
 start=time.monotonic()
 report={'status':'PASS','independent_dense_program_verification':{},'physical_qubits_demonstrated':0,'measured_programs':0,'native_programs':0,'exact_replays':0,'native_compiler_machine_isa':'x86-64','note':'Q30 fixed-point mathematical statevector; not physical coherence'}
 try:
  for file in sorted((R/'examples/Dense').glob('*.ql')):
   name=file.stem
   packet=R/'native/dense'/(name+'.qvb')
   blob=packet.read_bytes()
   # Recompile every shipped source, not just the five algorithm examples.
   with tempfile.TemporaryDirectory(prefix='axiom-program-build-') as compiled:
    fresh=Path(compiled)/(name+'.qvb')
    run(B/'native_q_compile',file,R/'native/dense/compiled.release_seed.qseed',fresh)
    assert fresh.read_bytes()==blob,('source/packet mismatch',name)
   nq,nc,seedtag,ops=M.decode(blob)
   inspect=run(B/'native_q_inspect',packet)
   assert 'PASS' in inspect
   text=run(B/'native_q_execute',packet,'--trace')
   (OUTPUT/(name+'.native_trace.log')).write_text(text)
   hashes,draws,outcomes,final,amp=M.parse_output(text)
   assert final['qubits']==nq and final['operations']==len(ops)
   assert len(hashes)==len(ops)
   assert sum(op[0] in (11,12) for op in ops)==len(draws)
   example={'qubits':nq,'operations':len(ops),'measurement_events':len(draws),'native_runtime_exit':0,'native_source_recompiled_byte_exact':True,'packet_sha256':hashlib.sha256(blob).hexdigest(),'replay_match':False,'independent_full_amplitude_oracle':False}
   if nq<=16:
    expect_hash,classic,norm,expect_amp,expect_out=M.oracle(nq,ops,draws)
    assert hashes==expect_hash and final['classical']==classic and final['norm']==norm and amp==expect_amp and outcomes==expect_out
    example['independent_full_amplitude_oracle']=True
   else:
    assert nq==20
    assert all(0<=key<2**nq for key in amp)
    assert len(amp)<=2 # single Bell link on sites 0 and 19 followed by measurement
    assert final['norm']>0
    example['analytic_sparse_20_site_check']=True
   if name=='bell_measure':
    assert len(outcomes)==2 and outcomes[0]==outcomes[1]
   if name=='teleport_plus':
    assert len(outcomes)==2
    # Qubit 2 remains |+> in each measured classical branch, up to fixed-point rounding.
    qs=[(i,xy) for i,xy in amp.items()]
    assert len(qs)==2
    assert (qs[0][0]^qs[1][0])==4
    a,ai=qs[0][1];b,bi=qs[1][1]
    # Fidelity against |+> is 1 - ((a-b)^2+(ai-bi)^2)/(2*(a*a+ai*ai+b*b+bi*bi)).
    # Check a quantitative rational bound, not an arbitrarily exact amplitude equality.
    mismatch=(a-b)**2+(ai-bi)**2
    total=a*a+ai*ai+b*b+bi*bi
    assert total>0 and mismatch*10**10<=total
    example['teleport_plus_infidelity_upper_bound']=1e-10
    example['teleport_plus_actual_numerator']=mismatch
    example['teleport_plus_actual_denominator']=2*total
    example['teleport_plus_feedforward_verified']=True
   # Execute the exact same quantum code again with only the captured entropy stream.
   with tempfile.TemporaryDirectory(prefix='quantum-native-replay-') as tmp:
    recorded=Path(tmp)/'draws.u32le';recorded.write_bytes(b''.join(struct.pack('<I',i) for i in draws))
    replay=run(B/'native_q_execute',packet,recorded,'--trace')
    hh,dd,oo,ff,aa=M.parse_output(replay)
    assert (hh,dd,oo,ff,aa)==(hashes,draws,outcomes,final,amp)
   example['replay_match']=True
   report['native_programs']+=1;report['exact_replays']+=1;report['measured_programs']+=bool(draws)
   report['independent_dense_program_verification'][name]=example
  assert report['native_programs']==len(list((R/'examples/Dense').glob('*.ql')))
 except Exception as e:
  import traceback
  report['status']='FAIL';report['error']=repr(e);report['traceback']=traceback.format_exc()
 finally:
  report['elapsed_seconds']=round(time.monotonic()-start,3)
  (OUTPUT/'dense_program_validation.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report,indent=2))
 if report['status']!='PASS':raise SystemExit(1)

if __name__=='__main__':main()
