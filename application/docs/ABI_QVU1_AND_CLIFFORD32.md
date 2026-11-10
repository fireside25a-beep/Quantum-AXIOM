# Native packet ABI QVU1 — source-checked

Source file: `native/dense/source/native_packet_abi.S`.

Observed witness: `native/dense/grover_2.qvb`; SHA-256 `2f0015cb9ff8849c562e3c3fa29dfdd7dcb6e8266b8698792f18e4d36081d357`.

The ABI uses fixed-width **little-endian** fields; no language object layout is embedded. A file contains a 48-byte header and `operation_count` records of 16 bytes each.

| Header field | Offset | Width | Meaning |
|---|---:|---:|---|
| `magic` | 0 | 4 | ASCII QVU1 |
| `version` | 4 | 4 | u32 = 1 |
| `qubits` | 8 | 4 | u32: syntax 1..256, dense executor 1..20 |
| `classical_bits` | 12 | 4 | u32: 1..32 |
| `operation_count` | 16 | 4 | u32: 1..4096 |
| `flags` | 20 | 4 | u32 = 1 |
| `seed_tag` | 24 | 8 | u64 unkeyed provenance tag |
| `record_digest` | 32 | 8 | u64 FNV-1a over all records |
| `reserved` | 40 | 8 | u64 = 0 |

Each 16-byte operation record is `opcode:u8`, `site0:u8`, `site1:u8`, `classical0:u8`, `parameter:i32`, `flags:u32=0`, `reserved:u32=0`. The packet digest is **not** a cryptographic signature.

## Native gate opcodes

| Opcode | Instruction |
|---:|---|
| 1 | H |
| 2 | X |
| 3 | Y |
| 4 | Z |
| 5 | S |
| 6 | SDG |
| 7 | T |
| 8 | TDG |
| 9 | CX |
| 10 | CZ |
| 11 | MEASURE |
| 12 | RESET |
| 13 | IF1 |
| 14 | IF0 |
| 15 | RZ8 |
| 16 | BARRIER |

## Compiler and runtime boundaries

- The `native_q_compile` translator is x86-64 assembly with libc calls for file I/O/token parsing. It reads text programs and a 64-byte seed and writes the above native-defined binary packet. `COMPTIME` directives are expanded at compile time.
- The `native_q_execute` interpreter dispatches validated packet records into native x86-64 fixed-Q30 complex-amplitude kernels. It is a **native instruction implementation of a classical quantum-state calculation**, not execution on coherent physical qubits.
- The dense executor supports up to 20 sites (`2^20` complex amplitudes). The syntax/packet validator supports 256 sites, but larger packets **are not executable** by this dense backend.
- Measurement uses 128-bit threshold division, OS `getrandom()` or an exact external replay sequence. The retained branch is normalized by a native integer-square-root routine before the next gate.
- The runtime validates the packet, allocates state, installs `PR_SET_NO_NEW_PRIVS` and a Linux seccomp BPF allowlist, and only then executes gates. The filter blocks `getpid` in a deliberate probe build; this does not protect against malicious kernels.
- The separately compiled Clifford32 image contains **direct expanded x86 instructions for every scheduled H/S/CX operation**, with no packet interpreter, and maintains triplicated 64-row tableau state. Its offline source-to-instruction lowering tool is Python and **not** self-hosting.
- The seed emitter replicates its own native executable through its triple-lane bit-seed format; no new instruction vocabulary is invented by this bootstrap.

## Source-backed memory layout of native closed seed

These offsets are verified from the native ELF64 data image and the source-lowering declarations.

| Offset from data VMA `0x402000` | Field |
|---:|---|
| `0x00` | 8-byte `SEEDX86!` magic |
| `0x08` | u64 generation epoch |
| `0x10`..`0x27` | three u64 ternary logical-state replicas (positive/negative 32-bit lanes) |
| `0x28`..`0x37` | u64 state-integrity tag and complement |
| `0x38`..`0x4F` | entropy, syndrome, lineage state |
| `0x60`/`0x68` | u32 FNV digest/complement for full tableau lane |
| `0x80`..`0x37F` | 64 × 12-byte tableau rows, ECC lane A |
| `0x380`..`0x67F` | ECC lane B |
| `0x680`..`0x97F` | ECC lane C |

A Pauli tableau row comprises `x_mask:u32`, `z_mask:u32`, `phase_mod4:u32`. Three 768-byte lanes undergo majority correction across all 192 words before each native instruction-plane transform. Faults that leave two lanes in agreement on the wrong value are not automatically correctable; the unkeyed digest rejects the tested conflicts.

## Reproducibility

Run `python3 docs/derive_abi_docs.py` from the release root to check source anchors and regenerate ABI evidence/diagrams.

