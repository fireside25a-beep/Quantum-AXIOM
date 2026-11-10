#!/usr/bin/env python3
"""Source- and process-derived sandbox and binary permission acceptance.
No virtualization success is inferred from ordinary process isolation.
"""
import hashlib,json,os,re,subprocess, tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
OUT=R/'evidence'
def run(*argv, check=True):
 p=subprocess.run(list(map(str,argv)),capture_output=True,text=True,timeout=30)
 if check and p.returncode:raise AssertionError((argv,p.returncode,p.stderr,p.stdout[:350]))
 return p
rep={'status':'FAIL','platform':os.uname().sysname+' '+os.uname().machine,
     'bins':{},'security_probe':{},'virtualization':{},'bytecode_vm_required':False}
for name,path in {
 'native_self_emitter':R/'native/seed/native_seed_emitter.x86_64',
 'native_closed_seed':R/'native/seed/genesis.x86_64',
 'clifford32_direct':R/'native/clifford/ghz_32.x86_64',
 'native_dense_assembly':R/'native/dense/bin/native_q_execute',
 'native_text_compiler_assembly':R/'native/dense/bin/native_q_compile',
 'self_hosted_native_compiler':R/'native/selfhost/anf_stage3.x86_64',
 'native_quantum_guest_machine':R/'native/machine/quantum_machine.x86_64',
 'native_quantum_history_reverser':R/'native/machine/reverse_history.x86_64'
}.items():
 data=path.read_bytes();assert data[:4]==b'\x7fELF'
 elf=run('readelf','-W','-l',path).stdout
 load=[line.strip() for line in elf.splitlines() if line.strip().startswith('LOAD')]
 assert load
 assert all(not re.search(r'\bRWE\b',line) and not ('RWE' in line.replace(' ','')) for line in load),(name,load)
 assert any('R E ' in (' '+line+' ') or re.search(r'\bR\s+E\b',line) for line in load),(name,load)
 rep['bins'][name]={'sha256':hashlib.sha256(data).hexdigest(),'elf_program_headers':len(load),'wx_separation':'PASS','needs_libc_so':('libc.so.6' in run('readelf','-d',path,check=False).stdout),'path':str(path.relative_to(R))}
# SECURITY_PROBE is resolved by the assembler and causes a real forbidden getpid syscall
# after the kernel reports successful BPF installation. The syscall must be EPERM.
probe=R/'security/native_q_execute_bpf_probe.x86_64'
pkt=R/'native/dense/grover_2.qvb'
p=run(probe,pkt)
assert 'QVU_FINAL' in p.stdout
assert 'QVU_REFUSED' not in p.stdout
rep['security_probe']={'test':'deliberate getpid syscall after native seccomp BPF; success path only when kernel returned -EPERM','result':'PASS','probe_sha256':hashlib.sha256(probe.read_bytes()).hexdigest(), 'exit_code':p.returncode,'seccomp_source':'native/dense/source/native_q_execute.S'}
with tempfile.TemporaryDirectory(prefix='axiom-compiler-sandbox-') as folder:
 compiler_probe=R/'security/native_q_compile_bpf_probe.x86_64'
 p=run(compiler_probe,R/'examples/Dense/grover_2.ql',R/'native/dense/compiled.release_seed.qseed',Path(folder)/'probe.qvb')
 assert 'QVU_COMPILED' in p.stdout
 rep['compiler_probe']={'result':'PASS','forbidden_getpid_errno':'EPERM','binary_sha256':hashlib.sha256(compiler_probe.read_bytes()).hexdigest()}
# Report actual capability, never a fake virtualization pass.
rep['machine_virtualization']={'implementation':'native AXIOM quantum guest contexts',
 'evidence':'evidence/native_machine_acceptance.json','uses_os_guest_virtualization':False,
 'pe64_execution':'NOT_RUN','arm64_execution':'NOT_RUN'}
rep['constraints']=['unprivileged sandbox not proof against compromised kernel or hypervisor','native_dense_executor uses libc for I/O, glibc dynamic linkage is disclosed','cryptographic manifest signature is distribution layer, not runtime CPU attestation']
rep['status']='PASS'
(OUT/'security_platform_assurance.json').write_text(json.dumps(rep,indent=2)+'\n')
print(json.dumps(rep,indent=2))
