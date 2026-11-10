# Program languages

## Dense QVU1 source

ASCII, one statement per line. A `#` token starts a comment after the required operands. Blank lines and comment lines are allowed. NUL bytes, non-ASCII bytes, clipped/overlong lines, unknown instructions, missing operands, extra operands, duplicate headers and range violations are refused.

Begin with `qubits N` (1..256). Optional `cbits C` (1..32, default 1) precedes instructions. The dense executor supports N <= 20; the compiler/packet SDK can represent larger targets without claiming they execute on this backend. There are at most 4,096 expanded records. Site and classical-bit indices start at zero.

| Instruction | Operands | Meaning |
|---|---|---|
| H, X, Y, Z, S, SDG, T, TDG | `site` | Single-site gate |
| CX, CZ | `control target` | Distinct sites |
| MEASURE | `site cbit` | Born sample, collapse, integer renormalization, overwrite cbit |
| RESET | `site` | Measure then X if needed; preserve classical register |
| IF1, IF0 | `cbit gate site` | Apply single-site gate if bit equals 1 or 0; gate mnemonic H..TDG or opcode 1..8 |
| RZ8 | `site integer` | Apply T^(integer mod 8); integer range -65,535..65,535 |
| BARRIER | none | Retained no-op record |
| COMPTIME REQUIRE_QUBITS | `minimum` | Refuse if the declared target is smaller |
| COMPTIME REQUIRE_CBITS | `minimum` | Refuse if the declared classical register is smaller |
| COMPTIME REPEAT | `count instruction operands` | Expand 2..64 copies of one instruction during compilation |

RZ8 names the implemented T-power phase convention `diag(1, exp(i*pi*k/4))`; it differs from a conventional symmetric Rz by a global phase. Numeric fields accept signed decimal integers in the documented bounds. This is a bounded circuit language, not a general-purpose language with arbitrary loops or recursion.

The compiler consumes a validated 64-byte QSEED01 seed and writes a canonical QVU1 packet to a newly created output. The seed supplies a reproducible provenance tag; it does not supply runtime measurement draws. Measurement uses Linux getrandom, or an explicit file containing exactly one little-endian u32 per MEASURE/RESET. Missing or extra draws refuse replay. `--trace` prints per-operation state hashes; final nonzero amplitudes are signed Q30 integers.

## Direct Clifford32 source

Begin with exactly `sites 32`. H, S, SDG, X, Y and Z take one site (0..31). CX takes distinct control and target indices. BARRIER is ignored. The lowerer expands the source into H/S/CX machine instructions, bounded by 70 elementary gates and the single RX code page's available instruction space. Oversized code is refused. This source-to-opcode tool runs offline in Python; generated images execute without Python or a packet interpreter.

## Seed formats

QSEED01 is 64 bytes: magic[8], version:u32=1, flags:u32 (bit 0 mandatory OS entropy, bit 1 optional RDSEED, bit 2 CPUID metadata), 32 random bytes, 12 CPU-vendor bytes, and a 4-byte auxiliary machine tag. A seed is a nonsecret replay/provenance fixture, not a private key or attestation of entropy quality.

BSTBIT01 begins with magic[8], decoded_length:u32 and FNV1a32:u32. Three encoded lanes follow. Each byte is `bitreverse(decoded XOR 0xa5)`. The native emitter majority-corrects lanes, decodes, validates length/checksum, installs its write/exit BPF filter, and emits at most 16,384 decoded bytes. Input ends at EOF; truncated/extra input is refused. This byte reconstruction is narrower than general source-level self-compilation.

## Initial tableau admission

The direct compiler accepts an optional fourth positional argument after the audit path:

```sh
python3 native/clifford/native_clifford_compiler.py native/seed/nucleus.qcl /tmp/imported.x86_64 /tmp/imported.audit.json examples/States/closed_routine.qstate.json
```

The state snapshot is at most 16,384 bytes and has exactly three keys: `format` = `AXIOM_TABLEAU_STATE_1`, integer `sites` (1..32), and `rows` (2*sites triples of integer X mask, Z mask and phase 0..3). Destabilizers precede stabilizers. Masks must fit the source width. Duplicate keys, booleans/floats, invalid dimensions, non-Hermitian generators or a noncanonical symplectic basis are refused before output creation. Unused sites extend with independent canonical X/Z generators. The input hash and admitted width are recorded in the lowering audit.

`closed_routine.qstate.json` is regenerated during tests by executing the included historical reference. No historical neural framework is loaded by the emitted native image.

This fixture is the corrected encoded state of a controlled reference test. It is not represented as the exact latest trained/live SNN checkpoint or as an SNN-invented compiler.
