# Native-state ABI (source- and executable-derived)

## ELF64 image

The image is an ET_EXEC, x86-64 Linux ELF, with two PT_LOAD segments. The initial entry address is `0x401000` and the native instruction region begins at file offset `0x1000`. The code and file header occupy the first loadable RX segment (`flags=5`). The data is at file offset `0x2000`, mapped to `0x402000` as RW (`flags=6`). The image length is 10,624 bytes; see `SOURCE_EXTRACTED_MACHINE_FACTS.json` for the exact segment lengths read directly from the ELF.

The resident state header begins at file offset `0x2000` (all offsets below relative to this position):

| Offset | Width | Actual field |
|---|---:|---|
| `0x00` | 8 | magic `SEEDX86!` |
| `0x08` | 8 | generation epoch, LE u64 |
| `0x10`, `0x18`, `0x20` | 8 each | three redundant 64-bit ternary state words |
| `0x28`, `0x30` | 8 each | epoch/state XOR-and-multiply integrity tag and bitwise complement |
| `0x38` | 8 | last native RDSEED word |
| `0x40` | 8 | state transition XOR syndrome |
| `0x48` | 8 | lineage evolution word |
| `0x50` | 8 | logical site count (`32`) |
| `0x58` | 8 | machine-state format identifier (`1`) |
| `0x60`, `0x68` | 4 each | FNV1a32 tableau checksum, complement |
| `0x80` | 2304 | three independent tableau replicas, 768 bytes each |

Each tableau has **64 rows of 12 bytes**, each row stored as little-endian `X mask u32`, `Z mask u32`, `phase u32`. The algebra uses the ordered Pauli convention `i^phase X^x Z^z`. The first 32 basis images are X generators and the last 32 are Z generators. Each native H, S and CX gate conjugates all 64 rows. The whole tableau is checked/corrected by independent 3-way majority, then validated by a digest and its inverse.

The ternary logical sites are represented as two disjoint 32-bit positive and negative planes within a 64-bit word. A site cannot be simultaneously positive and negative. A new RDSEED word and native rotate/XOR interactions determine the next state. The complete self-image is emitted using Linux `write(1, image, length)` after kernel BPF-seccomp initialization, then `_exit`. Exit 66 = RDSEED unavailable, exit 74 = corrupt or sandbox failure. This is not a QPU instruction set.

## Build-independent ABI tests

`docs/closed_seed_disassembly.txt`, `docs/SOURCE_EXTRACTED_MACHINE_FACTS.json` and `evidence/*.lowering.json` are derived from actual instructions and ELF fields. The native triple-lane emitter reconstructs fixed-format executable bytes. It does not implement arbitrary-language self-hosting.
