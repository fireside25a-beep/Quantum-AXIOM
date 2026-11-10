#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
unset PYTHONOPTIMIZE
for tool in python3 gcc as ld ar make readelf objdump dot openssl timeout; do
  command -v "$tool" >/dev/null || { echo "Missing build/test dependency: $tool" >&2; exit 2; }
done
mkdir -p evidence
run_suite() {
  local name=$1
  shift
  echo "AXIOM: $name"
  "$@" 2>&1 | tee "evidence/$name.log"
}
run_suite build make -B all
run_suite dense_oracle python3 -B -W error tests/native_dense_regression.py -v
run_suite release_programs python3 -B -W error tests/verify_release_programs.py
run_suite clifford_oracle timeout 240s python3 -B -W error tests/native_clifford_independent.py
run_suite exhaustive_memory timeout 180s python3 -B -W error tests/full_memory_fault_matrix.py
run_suite fault_campaign python3 -B -W error tests/fault_campaign.py
run_suite algorithms python3 -B -W error tests/quantum_algorithms_acceptance.py
run_suite basis_repetition python3 -B -W error tests/basis_repetition.py
run_suite security_platform python3 -B -W error tests/security_platform_assurance.py
run_suite native_machine python3 -B -W error tests/native_machine_acceptance.py
run_suite regressions python3 -B -W error tests/release_regressions.py
run_suite closed_routine_lineage python3 -B -W error tests/closed_routine_lineage.py
run_suite mathematical_laws python3 -B -W error tests/mathematical_laws.py
run_suite native_benchmark python3 -B -W error tests/benchmark_native.py --repetitions 5
run_suite abi_documents python3 -B -W error docs/derive_abi_docs.py
run_suite diagrams python3 -B -W error docs/generate_source_diagrams.py
run_suite machine_documents python3 -B -W error docs/derive_machine_docs.py
run_suite aggregate python3 -B -W error tests/summarize_evidence.py
run_suite release_records python3 -B -W error scripts/refresh_release_records.py
echo 'AXIOM: NATIVE COMPILER, MACHINE, REVERSAL AND LEGACY REGRESSIONS COMPLETE; see exact scientific scope in VERIFICATION_SUMMARY.json'
