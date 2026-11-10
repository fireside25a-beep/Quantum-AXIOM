PYTHON ?= python3
CC ?= gcc
.PHONY: all seed clifford dense probes packets selfhost test docs verify
all: seed clifford dense probes packets selfhost
seed:
	as --fatal-warnings -o native/seed/native_seed_emitter.o native/seed/native_seed_emitter.S
	ld --build-id=none -T native/seed/emitter.ld -o native/seed/native_seed_emitter.x86_64 native/seed/native_seed_emitter.o
	$(PYTHON) native/seed/encode_bitseed.py native/seed/native_seed_emitter.x86_64 native/seed/compiler_self_seed.bits
	$(PYTHON) native/clifford/native_clifford_compiler.py native/seed/nucleus.qcl native/seed/genesis.x86_64 evidence/nucleus.lowering.json
	$(PYTHON) native/clifford/native_clifford_compiler.py native/seed/nucleus.qcl native/seed/closed_routine_seed.x86_64 evidence/closed_routine.lowering.json examples/States/closed_routine.qstate.json
clifford:
	@for src in examples/Clifford32/*.qcl; do name=$$(basename "$$src" .qcl); $(PYTHON) native/clifford/native_clifford_compiler.py "$$src" "native/clifford/$$name.x86_64" "evidence/$$name.lowering.json" || exit $$?; done
dense:
	$(MAKE) -C native/dense all
selfhost: seed
	$(PYTHON) native/selfhost/build_selfhost.py
packets: dense
	$(PYTHON) scripts/build_packets.py
probes: dense
	as --fatal-warnings --defsym SECURITY_PROBE=1 -o native/seed/native_emitter_probe.o native/seed/native_seed_emitter.S
	ld --build-id=none -T native/seed/emitter.ld -o security/native_emitter_probe.x86_64 native/seed/native_emitter_probe.o
	$(CC) -c -Wall -Wextra -Werror -Wa,--fatal-warnings,--defsym,SECURITY_PROBE=1 -o security/native_q_execute_bpf_probe.o native/dense/source/native_q_execute.S
	$(CC) -no-pie -Wl,-z,noexecstack -o security/native_q_execute_bpf_probe.x86_64 security/native_q_execute_bpf_probe.o
	$(CC) -c -Wall -Wextra -Werror -Wa,--fatal-warnings,--defsym,SECURITY_PROBE=1 -o security/native_q_compile_bpf_probe.o native/dense/source/native_q_compile.S
	$(CC) -no-pie -Wl,-z,noexecstack -o security/native_q_compile_bpf_probe.x86_64 security/native_q_compile_bpf_probe.o native/dense/sdk/libnative_quantum_abi.a
test:
	bash scripts/RUN_VERIFICATION.sh
docs:
	$(PYTHON) docs/derive_abi_docs.py
	$(PYTHON) docs/generate_source_diagrams.py
	$(PYTHON) docs/derive_machine_docs.py
verify:
	bash security/VERIFY_RELEASE.sh
