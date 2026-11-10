#!/usr/bin/env python3
"""Executed 3-site computational-basis repetition/majority test; not a quantum-coherence QEC claim."""
from pathlib import Path
import json,subprocess,re,time,tempfile
ROOT=Path(__file__).resolve().parents[1]
S=ROOT/'examples/Dense/Repetition';S.mkdir(parents=True,exist_ok=True)
P=ROOT/'native/dense/repetition_compiled';P.mkdir(parents=True,exist_ok=True)
E=ROOT/'evidence/repetition';E.mkdir(parents=True,exist_ok=True)
B=ROOT/'native/dense/bin'
seed=ROOT/'native/dense/compiled.release_seed.qseed'
report={'status':'PASS','basis_cases':[],'basis_weight_0_or_1_corrected':0,'weight_2_or_3_rejected_by_majority':0,'fidelity_model':{},'no_physical_coherence_claim':True}
def run(*args):
 p=subprocess.run([str(x) for x in args],capture_output=True,text=True,timeout=15)
 assert p.returncode==0,(args,p.returncode,p.stderr)
 return p.stdout
try:
 for logical in (0,1):
  for pattern in range(8):
   name=f'logical{logical}_errors{pattern:03b}'
   src='qubits 3\ncbits 3\n'
   if logical:src+='X 0\n'
   src+='CX 0 1\nCX 0 2\n'
   for q in range(3):
    if pattern&(1<<q):src+=f'X {q}\n'
   src+='MEASURE 0 0\nMEASURE 1 1\nMEASURE 2 2\n'
   file=S/(name+'.ql');file.write_text(src)
   pkt=P/(name+'.qvb')
   # The native compiler deliberately uses exclusive output creation; compile
   # into a new temporary filename, then demand byte-exact correspondence with
   # the archived release packet. This permits repeatable verification.
   with tempfile.TemporaryDirectory(prefix='axiom-repetition-') as scratch:
    fresh=Path(scratch)/(name+'.qvb')
    run(B/'native_q_compile',file,seed,fresh)
    assert pkt.is_file(),('missing release packet',name)
    assert fresh.read_bytes()==pkt.read_bytes(),('native compiler packet mismatch',name)
    out=run(B/'native_q_execute',fresh,'--trace')
   (E/(name+'.native.log')).write_text(out)
   classical=int(re.search(r'QVU_FINAL[^\n]*classical=(\d+)',out).group(1))
   measured=[(classical>>q)&1 for q in range(3)]
   corrected=int(sum(measured)>=2)
   count=pattern.bit_count();success=corrected==logical
   assert success==(count<=1),(name,measured,corrected,logical)
   report['basis_cases'].append({'name':name,'logical':logical,'fault_count':count,'classical_output':classical,'majority':corrected,'restored':success})
   if success:report['basis_weight_0_or_1_corrected']+=1
   else:report['weight_2_or_3_rejected_by_majority']+=1
 for p in (0.001,0.01,0.05,0.1,0.2):
  error=3*p*p-2*p*p*p
  report['fidelity_model'][str(p)]={'uncoded_basis_fidelity':1-p,'repetition_majority_basis_fidelity':1-error,'independent_bitflip_assumption':True}
except Exception as e:
 report['status']='FAIL';report['error']=repr(e)
finally:
 (ROOT/'evidence/basis_repetition_validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='basis_cases'},indent=2))
if report['status']!='PASS':raise SystemExit(1)
