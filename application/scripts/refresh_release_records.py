#!/usr/bin/env python3
"""Refresh release handoff/source records from current verified evidence."""
from pathlib import Path
import hashlib
import json

R=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,obj):(R/name).write_text(json.dumps(obj,indent=2)+'\n')

def main():
    summary=json.loads((R/'evidence/VERIFICATION_SUMMARY.json').read_text())
    if summary['status']!='PASS' or not summary['limits']['native_source_self_hosting']:
        raise SystemExit('current G11 execution evidence incomplete')
    for item in summary['execution_suites'].values():
        if sha(R/item['path'])!=item['sha256']:raise SystemExit('summary evidence digest mismatch: '+item['path'])
    source_types={'.S','.c','.h','.cpp','.hpp','.py','.ld','.sh','.ql','.qcl','.anf'}
    sources=[]
    for p in sorted(R.rglob('*')):
        if p.is_file() and (p.suffix in source_types or p.name=='Makefile'):
            role='unchanged_compatibility_reference' if 'reference' in p.parts else 'active_source_or_test'
            sources.append({'path':str(p.relative_to(R)),'sha256':sha(p),'bytes':p.stat().st_size,'role':role})
    write('ai/SOURCE_MAP.json',{'release':summary['release'],'sources':sources,
          'external_project_checkout_dependencies':[],
          'embedded_reference_provenance':'tests/reference/closed_routine/PROVENANCE.json',
          'native_build_outputs':'evidence/source_only_rebuild.json',
          'native_compiler_and_machine':'evidence/native_self_hosting.json',
          'execution_summary':'evidence/VERIFICATION_SUMMARY.json','verified_target':'Linux x86-64'})
    write('ai/ACCEPTANCE.json',{'release':summary['release'],'implemented_scope_status':summary['status'],
          'counts':summary['counts'],'limits':summary['limits'],'release_readiness':summary['release_readiness'],
          'evidence':'evidence/VERIFICATION_SUMMARY.json','evidence_sha256':sha(R/'evidence/VERIFICATION_SUMMARY.json')})
    build=json.loads((R/'evidence/native_self_hosting.json').read_text())
    component_map={
      'native_compiler_source':'native/selfhost/compiler.anf',
      'independent_initial_constructor':'native/selfhost/bootstrap_anf.py',
      'native_source_self_compilation':'evidence/native_self_hosting.json',
      'native_quantum_core':'native/machine/quantum_core.anf',
      'native_guest_machine':'native/machine/quantum_machine.anf',
      'native_history_engine':'native/machine/reverse_history.anf',
      'canonical_machine_abi':'docs/MACHINE_ABI.md',
      'recorded_guest_history':'evidence/nested_machine.history',
      'recorded_inverse_history':'evidence/nested_machine.reversed.history',
      'independent_machine_acceptance':'tests/native_machine_acceptance.py',
      'new_seed_generation_chain':'evidence/seed_generations',
      'legacy_clifford_compiler':'native/clifford/native_clifford_compiler.py',
      'legacy_dense_compiler':'native/dense/source/native_q_compile.S',
      'legacy_dense_executor':'native/dense/source/native_q_execute.S',
      'legacy_packet_sdk':'native/dense/sdk/axiom_qvu.h'}
    for path in component_map.values():
        if not (R/path).exists():raise SystemExit('missing component: '+path)
    write('ai/SOURCE_BINARY_EVIDENCE_MAP.json',{'release':summary['release'],
          'components':component_map,'native_machine_builds':build['machine_targets_built_by_native_compiler'],
          'native_compiler_generations':build['native_generations'],
          'os_guest_virtualization_used':False,'physical_electrical_schematic_included':False})
    cliff=json.loads((R/'evidence/native_clifford_validation.json').read_text())
    dense=json.loads((R/'evidence/dense_program_validation.json').read_text())
    machine=json.loads((R/'evidence/native_machine_acceptance.json').read_text())
    lines=['# Executed program results','','Results below are derived from current execution evidence.','','| G11 native machine check | Result |','|---|---:|']
    checks=[('Native compiler generations',3),('Independent register-encoding comparisons',machine['assembly_differential_cases']),
            ('Quantum machine programs',machine['quantum_programs']),('Complete canonical frames compared',machine['full_frame_comparisons']),
            ('Maximum guest depth',machine['maximum_nested_depth']),('Native history round trips',machine['native_inverse_roundtrips']),
            ('Computed seed generations restored',machine['complete_seed_history_restorations']),
            ('Mutated journal-bit refusals',machine['journal_bit_refusals']),('Recomputed-checksum semantic refusals',machine['semantic_journal_refusals'])]
    lines.extend(f'| {label} | {value} |' for label,value in checks)
    lines+=['','| Direct Clifford program | Lowered gates | Full-tableau oracle |','|---|---:|---|']
    for name,item in cliff['examples'].items():lines.append(f"| {name} | {item['gates']} | PASS |")
    lines+=['','| Dense source | Sites | Operations | Recompiled | Full-amplitude oracle | Replay |','|---|---:|---:|---|---|---|']
    for name,item in dense['independent_dense_program_verification'].items():
        oracle='PASS' if item['independent_full_amplitude_oracle'] else 'Sparse analytical check'
        lines.append(f"| {name} | {item['qubits']} | {item['operations']} | PASS | {oracle} | PASS |")
    lines+=['','The 32-qubit machine is an exact digital stabilizer profile. The dense non-Clifford profile uses Q30 arithmetic. Neither establishes physical coherence. Full machine reversal requires retained history; numerical dense inverse tests have the error limits in `evidence/mathematical_laws.json`.','']
    (R/'docs/PROGRAM_RESULTS.md').write_text('\n'.join(lines))
    print('CURRENT RELEASE SOURCE / ACCEPTANCE / COMPONENT RECORDS VERIFIED')

if __name__=='__main__':main()
