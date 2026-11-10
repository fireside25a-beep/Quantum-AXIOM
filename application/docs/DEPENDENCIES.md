# Dependencies

| Dependency | Role | Required at runtime? |
|---|---|---|
| Linux x86-64 kernel with seccomp BPF | ELF loader, syscalls and confinement | Yes |
| CPU reporting RDSEED via CPUID | Native machine QENTROPY and direct nucleus/Clifford entropy input | Programs using hardware entropy; required for the full suite |
| Host glibc and ELF dynamic loader | Dense tool I/O, parsing and allocation | Dense tools only |
| GNU assembler, linker, ar, make and GCC driver | Assemble/link native source | Build only |
| Python 3.9+ standard library | Offline opcode lowering, bit-seed encoding, build driver and tests | Build/verify only |
| Graphviz dot | Source-derived software diagram | Documentation only |
| OpenSSL with Ed25519 support | Sign/verify the distribution inventory | Integrity verification only |

No third-party quantum simulator, ML framework, SDK runtime package, remote QPU service or source submodule is used by the production runtime. The compatibility suite compiles the included historical six-file C reference with its original license/notice. A C compiler with AddressSanitizer/UndefinedBehaviorSanitizer support is required for that additional test; its current LeakSanitizer host limitation is recorded separately. The compiler/runtime core is assembly; a C/C++ ABI header is supplied for consumers. GCC is used as an assembler/linker driver, not as a C-language bootstrap for the runtime. Current tool versions and linked binaries are recorded in `evidence/VERIFICATION_SUMMARY.json` and `evidence/security_platform_assurance.json`.

External dependencies are obtained from the user's system and retain their own licenses. They are not copied into this archive. The standalone seed/emitter/Clifford images do not link libc. Source rebuilding is the supported path when the shipped glibc-linked tools cannot load on another distribution.

The new self-hosted compiler and quantum machine are freestanding native executables. Their source-to-source-generation execution does not call libc, Python, a system assembler or an external VM. Python constructs the initial independent reference image during a source-only bootstrap and runs offline verification. Thereafter native compiler generations build both the compiler and quantum/history machine kernels. The guest machine uses no OS/hypervisor virtualization.
