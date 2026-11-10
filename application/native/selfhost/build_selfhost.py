#!/usr/bin/env python3
"""Construct stage zero, then run the actual native source self-compilations."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
from bootstrap_anf import assemble

R=Path(__file__).resolve().parents[2]
D=R/'native/selfhost'
M=R/'native/machine'

def sha(data):return hashlib.sha256(data).hexdigest()
def run(exe,data):
    p=subprocess.run([str(exe)],input=data,capture_output=True,timeout=30)
    if p.returncode:raise RuntimeError((str(exe),p.returncode,p.stderr[-1000:]))
    return p.stdout
def install(path,data):
    path.write_bytes(data);path.chmod(0o755)

def main():
    source=(D/'compiler.anf').read_bytes()
    initial=assemble(source.decode('ascii'))
    install(D/'anf_stage0.x86_64',initial)
    spec=importlib.util.spec_from_file_location('encode',R/'native/seed/encode_bitseed.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    encoded=module.encode(initial)
    (D/'compiler_seed.bits').write_bytes(encoded)
    # Bootstrap from the native encoded seed, then compile actual source.
    decoded=run(R/'native/seed/native_seed_emitter.x86_64',encoded)
    if decoded!=initial:raise AssertionError('native seed reconstruction differs')
    install(D/'anf_seed_compiler.x86_64',decoded)
    previous=D/'anf_seed_compiler.x86_64'
    generations=[]
    for generation in range(1,4):
        image=run(previous,source)
        if image!=initial:raise AssertionError(('native source self-compilation mismatch',generation))
        target=D/f'anf_stage{generation}.x86_64';install(target,image)
        generations.append({'generation':generation,'image_sha256':sha(image),'source_sha256':sha(source),
                            'byte_identical_to_independent_constructor':True})
        previous=target
    machine=[]
    for stem in ('quantum_machine','reverse_history'):
        parts=[M/(stem+'.anf'),M/'quantum_core.anf']
        text='\n'.join(p.read_text() for p in parts)
        image=run(previous,text.encode('ascii'))
        if image!=assemble(text):raise AssertionError(('native machine construction mismatch',stem))
        install(M/(stem+'.x86_64'),image)
        machine.append({'target':str((M/(stem+'.x86_64')).relative_to(R)),
                        'source_parts':[str(p.relative_to(R)) for p in parts],
                        'combined_source_sha256':sha(text.encode('ascii')),'image_sha256':sha(image)})
    examples=[]
    for source_path in sorted((R/'examples').rglob('*.anf')):
        packet=run(previous,source_path.read_bytes())
        if packet[:8]!=b'AXQVM11\0':raise AssertionError(('example is not a quantum seed',source_path))
        target=source_path.with_suffix('.seed');target.write_bytes(packet)
        examples.append({'source':str(source_path.relative_to(R)),'seed':str(target.relative_to(R)),
                         'source_sha256':sha(source_path.read_bytes()),'seed_sha256':sha(packet)})
    result={'status':'PASS','native_source_self_hosting':True,'native_generations':generations,
            'bootstrap_constructor':'native/selfhost/bootstrap_anf.py (initial construction only)',
            'native_seed_emitter_sha256':sha((R/'native/seed/native_seed_emitter.x86_64').read_bytes()),
            'encoded_compiler_seed_sha256':sha(encoded),'compiler_image_bytes':len(initial),
            'machine_targets_built_by_native_compiler':machine,'uses_kvm_or_os_guest_virtualization':False}
    result['quantum_examples_compiled_natively']=examples
    (R/'evidence/native_self_hosting.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
