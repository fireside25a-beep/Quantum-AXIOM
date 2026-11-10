# Operating AXIOM

The Linux app download is a command-line application. It has no graphical Studio or background service. Extract the ZIP with executable permissions preserved. If an archive manager drops those permissions, run `chmod u+x bin/*` in the extracted app directory.

## Check the environment

```sh
bash VERIFY.sh
./bin/axiom doctor
./bin/axiom version
```

Native compiler, machine, history and seed-emitter binaries are freestanding Linux x86-64 ELFs. The dense compiler/executor/inspector use the system ELF loader and glibc; the shipped binaries require glibc 2.41 or newer. `qentropy` and legacy direct images need CPUID-reported RDSEED. There is no software entropy fallback. The complete package provides source rebuilding for compatible Linux systems with older glibc.

Verification needs coreutils (`sha256sum`, `sort`, `cut`, `cmp`, `mktemp`) and `find`. OpenSSL is needed only when a detached package signature is present. An unsigned inventory detects changed payloads but does not authenticate a publisher. A bundled public key likewise needs an independently trusted fingerprint to establish identity.

## Demonstrate the connected native path

```sh
./bin/axiom demo
./bin/axiom selfhost
```

`demo` compiles the nested example, executes actual quantum guest instructions, reverses the journal, checks a second reversal and compares the restored seed byte-for-byte. It uses actual hardware entropy. `selfhost` reconstructs the compiler from the encoded seed and compiles its own source three times, checking complete native images at each step. Temporary outputs are cleaned after the check.

## Compile and run your own quantum source

The source syntax is documented in `share/doc/axiom/ANF64.md` inside the app package.

```sh
./bin/axiom compile < share/axiom/examples/Machine/entropy_seed_loop.anf > experiment.seed
./bin/axiom run < experiment.seed > experiment.history
./bin/axiom history < experiment.history > experiment.reverse.history
./bin/axiom history seed < experiment.reverse.history > restored.seed
cmp experiment.seed restored.seed
./bin/axiom history next < experiment.history > next.seed
./bin/axiom run < next.seed > next.history
```

Source and machine output are binary streams where documented. Redirect compiler and machine stdout to files. A partial output from a failed command must be discarded; shell pipelines should enable `set -o pipefail` where supported.

## Dense profile

```sh
./bin/axiom dense-inspect share/axiom/compiled/grover_2.qvb
./bin/axiom dense-run share/axiom/compiled/grover_2.qvb
./bin/axiom dense-compile share/axiom/examples/Dense/t_interference.ql share/axiom/compiled/compiled.release_seed.qseed t_interference.qvb
```

Dense runtime results are fixed-point digital amplitudes. `--trace` and explicit replay draws are described in `share/doc/axiom/LANGUAGE.md`. The new machine's journal protocol does not apply to dense QVU1 execution.

## Refusals and recovery

The native machine/history tools return 74 for malformed admission, exhausted fuel, guest-bound violations and invalid history. Hardware entropy unavailability returns 66. Other tools have their own documented nonzero error codes. Preserve the input and stderr, inspect the applicable ABI and rerun only after resolving the cause. Missing hardware entropy is never silently replaced.

Keep journals when exact generation restoration matters. A final quantum bank alone cannot reconstruct discarded control or entropy information. Back up source and evidence before edits; rebuild and run the full suite from the complete download in a separate working directory.
