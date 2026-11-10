# Active compatibility reference

This directory contains six unchanged source/header files selected from the preserved closed-routine dependency snapshot, plus its existing license and notice. `PROVENANCE.json` records exact original paths, hashes and the verified source-volume identity. No parent project build is needed.

`tests/closed_routine_probe.c` is separate test instrumentation. It calls these actual neuron, world and tableau functions to exercise 195 fault/readout combinations, neural feedback and transactional refusals. `tests/closed_routine_lineage.py` recompiles the reference, compares the exported state with the fixture, executes admitted native images, and checks inverses and malformed-state refusal. These sources are not a second production engine and are not linked into the production compiler/runtime.
