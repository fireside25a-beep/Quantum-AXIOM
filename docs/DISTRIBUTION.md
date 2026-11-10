# Download and source policy

`g11.1` distributes the signed G11 engine, with repository presentation,
maintainer tools and automated verification. The engine source and binary bytes
remain unchanged.

| Delivery | Contents | Presentation and maintainer tools |
|---|---|---|
| `axiom-g11.1-linux-x86_64.zip` | Runnable Linux x86-64 executables, SDK, examples, compiler seed/source, operating guide, license and checksum inventory | Excluded |
| `axiom-g11.1-complete.zip` | Entire tracked repository tree, including the sealed application, reference notices, tests, raw evidence, README, docs and workflow source; plus package verification files | Included |
| GitHub Code → Download ZIP / source archive | Entire reviewed Git tree at the chosen ref | Included |
| Git clone | Entire reviewed Git tree and Git history | Included |

The complete ZIP is a single `axiom-g11.1-complete/` directory. `application/`
is the signed engine inside it. `maintainer/` contains first-party packaging
and verification tools. `presentation/` contains static self-contained SVGs
rendered by GitHub's README; GitHub Pages is not required. The source archive
retains the full tracked tree because `.gitattributes` has no export exclusions.
The Linux app ZIP is purposefully smaller and does not need the repository
presentation or its packaging scripts to run.

Both named assets carry per-file SHA-256 inventories and reject added or
modified content. The complete package also checks the inner signed
application snapshot. The package builder selects tracked files, excludes Git
history and ignored outputs, preserves executable modes, and writes fixed ZIP
metadata. Release metadata records the actual commit, so a new commit changes
the asset hashes even when the signed engine bytes stay unchanged.

The Linux CI job verifies the signed application, runs the native suite in a
disposable copy, checks exact rebuilt outputs, validates SVGs, and tests
extracted app and complete ZIPs. Tag publishing runs only after that job passes.
An actual successful GitHub Actions run must be observed before claiming a
remote release is verified.

Apache-2.0 rights for first-party contents are stated in the root LICENSE and
LICENSING.md. The signed application's older license text remains as historical
snapshot data. The reference source retains its own license and notice.
