# ANF64 native/quantum source language

The self-hosted compiler reads ASCII source from stdin and emits either an x86-64 ELF or a quantum-machine seed to stdout. It creates no output files itself. Input is bounded to 262,144 bytes; tokens to 63 bytes; labels to 4,096; native output to 1 MiB; BSS to 8 MiB. Symbols retain full names, not only hashes. Comments begin with `#`.

## Native dialect

Register operands are decimal native encoding IDs: RAX=0, RCX=1, RDX=2, RBX=3, RSP=4, RBP=5, RSI=6, RDI=7, R8..R15=8..15. Integers are unsigned decimal up to 2^64-1 or negative signed decimal down to -2^63, with overflow refusal.

| Syntax | Behavior |
|---|---|
| `code`, `bss` | Select emitted native code/constants or zero-initialized memory |
| `label name`, `space bytes` | Define a symbol; reserve bounded BSS |
| `db value`, `dq value` | Emit one byte / one little-endian u64 constant |
| `imm dst value`, `addr dst label` | Load immediate or resolved symbol address |
| `mov/add/sub/xor/and/or/cmp/test dst src` | Native two-register operation |
| `load/load8 dst base` | Read u64 / zero-extended byte at a register address |
| `store/store8 base src` | Write u64 / low byte |
| `shl/shr/sar reg count`, `mul dst src` | Native shift / low 64-bit multiplication |
| `div/not/neg/inc/dec/push/pop reg` | Native unary operation; DIV uses RDX:RAX |
| `jmp/call/jz/jnz/jb/jae/jbe/ja/jl/jge/jle/jg label` | Resolved native control flow |
| `ret`, `syscall`, `cpuid`, `rdseed reg` | Explicit native instruction |

The compiler performs two source passes, generates registers/ModRM/SIB/immediates/relative branches, constructs ELF headers and separates RX code from RW BSS. The native dialect is a low-level compiler language; arbitrary native programs are not the restricted quantum-guest ISA.

## Quantum dialect

Begin with `qubits32`. Optional `qgas N` sets 1..1024 fuel. `qrow index x z phase` provides an initial Pauli row (index 0..63, masks <=2^32-1, phase 0..3); the machine validates the complete basis. Default rows are canonical |0> stabilizer generators.

Instructions are `qh/qs/qsdg/qx/qy/qz qubit`, `qcx control target`, `qentropy`, `qephase qubit`, `vmcall child_id start length`, `vmreturn`, and `qhalt`. Code indices count 32-byte records. The compiler emits a canonical seed, never an OS guest image. Native ANF instructions are refused inside the quantum dialect. See `MACHINE_ABI.md` for execution, nesting, ownership and history semantics.

## Bootstrap and evidence

`bootstrap_anf.py` is the independent initial constructor. Its output is encoded as `compiler_seed.bits`. The freestanding native seed emitter reconstructs the initial native compiler. That compiler then compiles `compiler.anf` through three successive native generations. Their complete images match the independent initial construction byte for byte.

Acceptance also changes compiler source to alter its actual exit behavior, checks the resulting executable against the independent constructor, executes unseen native programs, and compares 100 generated register encodings. Thus self-hosting is tested at source-compilation level rather than inferred from image copying.

Once the initial seed/compiler is available, native source self-compilation, quantum program compilation, machine execution, next-seed generation and history reversal need no Python or system assembler. The Python constructor and test oracles remain included for transparent bootstrap provenance and independent checking.
