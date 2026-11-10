# AXIOM G11 engineering handoff

Start with the root README and `docs/RELEASE_COMPLETENESS_AUDIT.md`. The native compiler source is `native/selfhost/compiler.anf`. Quantum/control/history sources are under `native/machine/`. Their executables are produced by the native self-hosted compiler; the independent initial constructor is retained explicitly.

`evidence/native_self_hosting.json` binds native generations and source identities. `evidence/native_machine_acceptance.json` records changed-source compilation, independent encodings, full canonical machine comparisons, nested guests, native inverse checks and complete generation restoration. Raw seed/history artifacts are included.

The machine's ISA/state/ownership is authoritative. No OS guest or hypervisor is part of the design. No HX89 source is reused. Distinguish exact virtual stabilizer algebra from physical coherent qubits; distinguish complete retained history reversal from recovering discarded information without a journal. The separate dense Q30 profile keeps its documented numerical limits.

Run signature verification on a pristine extraction and rebuild/test on a separate working copy. Preserve original snapshots and failures. The legacy reference LeakSanitizer host failure remains explicitly incomplete. Never substitute test-oracle output for native execution.
