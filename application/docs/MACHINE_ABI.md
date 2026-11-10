# AXIOM native quantum-machine ABI v1

All serialized scalars are little-endian u64. No host struct padding is used. `native/machine/axiom_machine.h` defines constants for consumers. The guest ISA is machine-defined; the OS supplies only executable loading and input/output services.

## Seed packet

| Offset | Field |
|---:|---|
| 0 | 8-byte magic `AXQVM11` followed by NUL |
| 8 | Version = 1 |
| 16 | Stabilizer-qubit width = 32 |
| 24 | Record count, 1..1024 |
| 32 | Execution fuel, 1..1024 |
| 40 | FNV1a64 of the complete payload after byte 64 |
| 48, 56 | Reserved = 0 |

The payload is one 4,096-byte initial state followed by exactly N 32-byte records. Initial control/stack/reserved bytes must be zero; the prior entropy word at state offset 32 may be retained. The Pauli bank must have bounded masks/phases, Hermitian generators, and all 2,016 canonical symplectic pair relations. Admission validates every instruction before execution.

## Canonical state

| Offset | Field |
|---:|---|
| 0 | Epoch / committed transition count |
| 8 | Current guest program counter, in record indices |
| 16 | Quantum-bank owner ID, root = 0 |
| 24 | Guest depth, 0..16 |
| 32 | Last successful RDSEED word / retained seed entropy |
| 40, 48, 56 | Last opcode and operands A/B |
| 64, 72 | Current guest code-view start and exclusive end |
| 80 | Remaining global fuel |
| 88 | Halt flag |
| 96..127 | Reserved |
| 128..639 | Sixteen frames of four u64 values: parent owner, return PC, parent start, parent end |
| 640..1023 | Reserved |
| 1024..2559 | 64 Pauli rows, 24 bytes each: X mask, Z mask, phase |
| 2560..4095 | Reserved |

Masks use their low 32 bits. Phases are 0..3 in the ordered convention `i^phase X^x Z^z`. The first 32 rows are destabilizers and the last 32 are stabilizers. Machine transition ownership is exclusive. A call transfers the single quantum bank; the parent is suspended. Frame records are cleared on return.

## Guest instructions

Each record is `(opcode, A, B, C)` as four u64 words. Unused fields must be zero.

| Opcode | Instruction | Operands |
|---:|---|---|
| 0 | QHALT | None; root only, with balanced guest stack |
| 1,2,3 | H, S, SDG | A = qubit 0..31 |
| 4 | CX | A/B = distinct control/target qubits |
| 5,6,7 | X, Y, Z | A = qubit |
| 8 | QENTROPY | None; feature-checked bounded RDSEED sampling |
| 9 | QEPHASE | A = qubit; S if retained entropy bit A is 1, otherwise SDG |
| 16 | VMCALL | A = child ID 1..255; B = code start; C = code length |
| 17 | VMRETURN | None; active child only |

Child views must be contained within the current view and total program. Active owner IDs cannot be reused. Root/guest PC and fuel are checked on every step. Guests have no raw memory, syscall, file, native pointer or executable-permission instruction. These restrictions implement machine-level admission and isolation. They are not a claim that arbitrary native ANF64 programs are sandboxed.

The CPU entropy word is classical control input to a quantum phase operation, not a claim of physical quantum measurement. CPUID and RDSEED execute real CPU instructions. Missing features or exhausted bounded retries return 66; other refusals return 74. No failure is converted to fabricated random data.

## Complete history

History magic is `AXHST11` + NUL. Its 64-byte header contains: version at 8, frame count at 16, state width 4096 at 24, original seed byte length at 32, FNV1a64 payload checksum at 40, direction flag 0/1 at 48, reserved zero at 56. The payload is the original complete seed followed by every canonical state, including admitted state zero and the halted final state. Maximum native journal size is 4,235,392 bytes.

`reverse_history` checks sizes, both checksums, epochs, source-PC/opcode bindings, and native inverse quantum operations for each predecessor. It then reverses the full state sequence. S/SDG are exchanged; H/CX/Paulis are self-inverse; entropy-conditioned phases use the retained actual entropy word. Irreversible control/entropy preimages are restored from the complete recorded state. Two native reversals reproduce the original journal byte for byte.

`reverse_history seed` restores the original seed. `state` emits the admitted initial canonical state. `next` emits a new seed carrying the final quantum bank and retained entropy word, with refreshed checksum and reset control state. Repeating execution and next-seed emission forms a native closed chain; retaining its journals permits byte-exact restoration through every recorded generation.

FNV is an accidental-corruption check, not a cryptographic MAC. Semantic inverse checks detect tested recomputed-checksum inconsistencies. SHA-256 and Ed25519 protect the distributed evidence snapshot. Physical host time and the entropy device itself are not reversed; discarded information is explicitly retained in the journal.
