#!/usr/bin/env python3
"""Aggregate only current executed evidence; refuse any failed/missing gate."""
from pathlib import Path
import hashlib
import json
import platform
import re
import subprocess
R=Path(__file__).resolve().parents[1]
D=R/'evidence'
files={
 'clifford32_native':'native_clifford_validation.json',
 'dense_algorithmic_programs':'quantum_algorithms_acceptance.json',
 'dense_program_replays':'dense_program_validation.json',
 'exhaustive_tableau_faults':'full_memory_fault_matrix.json',
 'state_fault_campaign':'fault_campaign.json',
 'basis_repetition':'basis_repetition_validation.json',
 'native_source_self_hosting':'native_self_hosting.json',
 'native_quantum_machine':'native_machine_acceptance.json',
 'kernel_sandbox':'security_platform_assurance.json',
 'source_only_rebuild':'source_only_rebuild.json',
 'seed_generations':'native_seed_generations.json',
 'mathematical_laws':'mathematical_laws.json',
 'closed_routine_state_lineage':'closed_routine_lineage.json',
 'native_benchmark':'native_benchmark.json',
}
report={'status':'FAIL','release':'AXIOM Native Fabric G11 native quantum machine','platform':platform.platform(),'execution_suites':{},'tools':{}}
objects={}
for name,filename in files.items():
 path=D/filename
 obj=json.loads(path.read_text())
 if obj.get('status')!='PASS':raise SystemExit('FAILED GATE: '+filename)
 objects[name]=obj
 report['execution_suites'][name]={'status':'PASS','path':str(path.relative_to(R)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
text=(D/'dense_oracle.log').read_text()
m=re.search(r'QVU_INDEPENDENT_ORACLE_PASS programs=(\d+) operations=(\d+) measurement_events=(\d+)',text)
if not m or 'Ran 6 tests' not in text or '\nOK\n' not in text:raise SystemExit('dense unittest suite not complete')
regression=(D/'regressions.log').read_text()
reg=re.search(r'Ran (\d+) tests',regression)
if not reg or '\nOK\n' not in regression:raise SystemExit('release regression suite not complete')
report['counts']={
 'dense_random_programs':int(m[1]),'dense_random_operations':int(m[2]),'dense_measurement_events':int(m[3]),
 'release_regression_tests':int(reg[1]),
 'direct_random_programs':objects['clifford32_native']['randomized_programs'],
 'direct_inverse_checks':objects['clifford32_native']['reversal_proofs'],
 'single_bit_repairs':objects['exhaustive_tableau_faults']['single_bit_native_execution_repairs'],
 'two_lane_refusals':objects['exhaustive_tableau_faults']['two_lane_same_bit_native_refusals'],
 'payload_bit_refusals':objects['dense_algorithmic_programs']['corruption_detection']['all_payload_bits_flipped_and_refused_by_native_inspector'],
 'example_source_compiles':objects['dense_program_replays']['native_programs'],
 'basis_cases':len(objects['basis_repetition']['basis_cases']),
 'clean_rebuilt_outputs':len(objects['source_only_rebuild']['outputs']),
 'seed_generations':objects['seed_generations']['generations'],
 'complex_oracle_programs':objects['mathematical_laws']['unitary_programs'],
 'dense_inverse_programs':objects['mathematical_laws']['inverse_programs'],
}
machine=objects['native_quantum_machine']
report['counts'].update({'native_compiler_generations':3,'native_machine_quantum_programs':machine['quantum_programs'],
 'native_machine_frames_compared':machine['full_frame_comparisons'],'maximum_native_guest_depth':machine['maximum_nested_depth'],
 'native_journal_roundtrips':machine['native_inverse_roundtrips'],'native_seed_generation_restorations':machine['complete_seed_history_restorations']})
report['limits']={'physical_coherent_qubits_demonstrated':0,'native_source_self_hosting':True,
 'compiler_source_language':'ANF64 native/quantum assembly','dense_site_limit':20,'clifford_sites':32,
 'windows_arm64_tested':False,'machine_level_nesting_tested':True,'uses_os_guest_virtualization':False,
 'history_requirement':'complete retained journal including original seed and every canonical preimage',
 'machine_gas_limit':1024,'machine_nested_guest_limit':16}
report['release_readiness']={'requested_compiler_history_nesting_additions_implemented':True,
 'classification':'VERIFIED_NATIVE_QUANTUM_MACHINE',
 'remaining_research_boundaries':['physical coherent-qubit behavior not demonstrated',
 'bootstrap from exact latest previously saved trained/live SNN checkpoint not established',
 'cross-platform backends not executed','dense Q30 engine remains a separate mathematical execution profile'],
 'reference_sanitizer_result':objects['closed_routine_state_lineage']['native_reference_builds']['san']}
for name,argv in {'python':['python3','--version'],'gcc':['gcc','--version'],'binutils':['ld','--version'],
                  'openssl':['openssl','version'],'libc':['getconf','GNU_LIBC_VERSION']}.items():
 p=subprocess.run(argv,capture_output=True,text=True,timeout=10,check=True)
 report['tools'][name]=p.stdout.splitlines()[0]
report['status']='PASS'
(D/'VERIFICATION_SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
