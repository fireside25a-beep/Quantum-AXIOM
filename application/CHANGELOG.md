# Changes

## G11 — native compiler, quantum machine and complete history

- Implemented a two-pass self-hosted x86-64/quantum compiler in its own ANF64 source language; three native generations match byte for byte.
- Added an independent native quantum machine with checked 32-qubit Pauli state, exclusive ownership transfer, code-view attenuation, global fuel and sixteen guest levels.
- Implemented native history reversal with actual inverse quantum kernels, source-PC/opcode binding, full preimages and exact seed restoration.
- Added native next-seed generation carrying computed quantum state and actual retained hardware entropy; twelve complete generation histories are executed and restored.
- Added hardware-entropy-conditioned phases, source-linked state admission, negative/semantic-corruption cases, public ABI and runnable examples.
- Replaced OS-namespace nesting as the relevant model with the user-requested native machine guest architecture. No hypervisor or HX89 code is used.

## G10 research candidate — 2026-11-10

- Corrected the release-readiness claim: a self-contained build does not prove completion of the original scope. Added an explicit completeness audit.
- Verified the preserved BF13 archive CRC and all 193 extracted checkpoint-manifest entries. Selected only six unchanged source/header files and their license/notice for test-only use.
- Executed the actual closed SNN/quantum loop over 195 Pauli-fault/readout cases, including real neural feedback and transactional double-fault refusal, under O0/O2.
- Added bounded, typed tableau-state admission with duplicate-key, integer-range, Hermiticity and all-pair symplectic checks. The exported state now seeds a standalone native image.
- Added 16 native imported-state and 16 native inverse sequences, 14 malformed-state refusals and a measured 4..20-site native CLI benchmark.
- Preserved the sanitizer failure: LeakSanitizer cannot finish in the traced host environment. Sanitizers remain enabled; this gate is explicitly incomplete.
- Genuine compiler self-hosting, physical coherence, complete history inversion and nested hardware guest validation remain undelivered requirements.

## G9 — 2026-11-10

- Recovered the nucleus source schedule and reproduced the entire original G8 nucleus byte for byte before applying fixes. Included the exact recovery receipt.
- Added readable freestanding emitter assembly and linker source; fixed its single-read pipe failure and the mismatch between advertised 16 KiB capacity and its old input-buffer size. Added full-lane correction, malformed-stream and forbidden-syscall checks.
- Replaced strict seccomp in the direct images with a restrictive stackable BPF filter. The original images refused execution under an existing host filter; the replacement retains kernel enforcement and passes a hostile syscall test.
- Fixed missing IF0/IF1 operands that reached strcmp with a null pointer. Reject embedded NUL/non-ASCII source and overlong lines before parsing.
- Enforced the same seed flags and signed RZ8 range across compiler, executor and SDK. Corrected default classical-bit handling when cbits is omitted.
- Preserved all 12 CPUID vendor bytes in new seeds; added maximum-leaf checks before RDSEED capability queries.
- Restored the main stack on runtime errors reached inside gate/measurement helpers. Replay exhaustion now returns a controlled refusal. Output flush errors refuse success.
- Kept Clifford operand validation active under Python optimization; validate the resident ABI header and reject epoch wraparound.
- Made every built native executable/library and example packet reproducible from source. Deterministic object names remove random linker filename metadata. Create missing build directories automatically.
- Added the SDK header, independent complex-number gate checks, 48 dense inverse programs, Born-threshold boundaries, 24 checked seed generations, and a source-only byte-exact rebuild gate.
- Recompile all 13 dense example sources and all 16 repetition fixtures during the connected build. Refresh ABI facts, source anchors, logs, acceptance counts and diagrams from current files.
- Consolidated the standalone module tree; removed duplicate documents, stale binaries/logs, historical acceptance claims and Python caches from the new snapshot. The uploaded original remains unchanged.
