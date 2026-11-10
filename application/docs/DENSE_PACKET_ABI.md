# Dense quantum packet ABI v1

The `.ql` parser and `.qvb` executor are native x86-64 assembly. The packet header (`QVU1`) is **48 bytes**, with exact little-endian fields: `magic[4]`, `version:u32`, `qubits:u32`, `cbits:u32`, `records:u32`, `flags:u32`, `seedtag:u64`, `records_fnv1a64:u64`, `reserved:u64`. Version=1, flags=1 and reserved=0.

Each instruction record is exactly 16 bytes: `opcode:u8`, `qubit0:u8`, `qubit1:u8`, `classical0:u8`, `parameter:i32`, `flags:u32`, `reserved:u32`. All non-applicable operands, flags, and reserved words must be zero. Packet length must be exactly `48+16*records`. Bad magic, unsupported opcodes, malformed arity, invalid indices, nonzero reserved fields, and checksum corruption are refused before execution.

| Opcode | Operator | Semantics |
|---:|---|---|
| 1–8 | `H X Y Z S SDG T TDG` | One-site fixed-point complex amplitude updates |
| 9–10 | `CX CZ` | Two-site controlled unitary gates |
| 11 | `MEASURE q c` | Projective measurement and bit assignment; entropy or explicit replay |
| 12 | `RESET q` | Measure then conditional X to return measured site to zero |
| 13–14 | `IF1 c op q`, `IF0 c op q` | Classical one-site feedforward (opcodes 1–8) |
| 15 | `RZ8 q k` | Phase rotation in signed integer multiples of π/4 |
| 16 | `BARRIER` | No-op synchronization boundary |

The compiler supports 1..256 qubit indices, up to 4096 operation records, 1..32 classical bits; the available x86 native dense executor refuses >20 qubits (bounded dense state allocation). A 20-qubit statevector has `2^20` complex amplitudes, each with two signed Q30 components stored as int64. All arithmetic is integer/fixed-point and may accumulate rounding error; *not exact arbitrary quantum arithmetic*. The runtime uses `getrandom` for measurements and validates the exact number of draws in replay mode. After a projective measurement it renormalizes the selected branch with an integer square-root based Q30 gain; see the actual `renormalize_after_measure` instruction implementation and independent oracle.

Compiler and executor install a Linux seccomp BPF allowlist after the relevant inputs/outputs are open and validated, before native processing/output. No pathname-based filesystem confinement or kernel compromise protection is implied. The `SECURITY_PROBE` build deliberately issues forbidden syscall 39 (`getpid`) and verifies `EPERM`.

`COMPTIME REQUIRE_QUBITS`, `COMPTIME REQUIRE_CBITS`, and `COMPTIME REPEAT N gate` execute during compilation (not at runtime). The packet is an input format consumed by an assembly-native digital engine, not executable machine code. This is intentionally distinct from the direct Clifford32 instruction compilation.
