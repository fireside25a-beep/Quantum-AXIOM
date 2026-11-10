# Maintainer release procedure

The existing remote is `fireside25a-beep/Quantum-AXIOM` over HTTPS. The
repository owner and maintainer is Alexandru Moraru. Work in a separate local
`Quantum-AXIOM/` Git checkout restored from the delivered G11 bundle; the
outer handoff archive and private Mac staging instructions are not committed.

The `maintainer/publish.sh --check` helper is a read-only preflight for the
existing remote. It verifies the local staging tree, GitHub identity and
remote state; it does not create a repository, push or tag. If the remote has
an independently initialized history, stop and reconcile it deliberately.
Never force-push. Use `gh auth setup-git` to configure Git HTTPS credentials
on the Mac after checking the active `gh` login.

Commit and review local changes, run the portable application inventory check,
then push `main`. Wait for the Linux `Verify application and downloads` job to
pass. Create/push the `g11.1` tag at that exact commit; the tag triggers a
second verify job followed by asset publication. Inspect the actual Release
and its two named ZIPs and checksum files.

`make art` regenerates the SVGs. On Linux x86-64, `make check` packages and
tests both extracted downloads. macOS can package, but native Linux execution
and inner Ed25519 verification must run in Linux CI. Do not claim they ran on
the Mac.

The signed `application/` snapshot should not be edited or rebuilt in place
for a distribution-only change. Its prior license notice remains intact as
historical signed data; the new root LICENSE and LICENSING.md grant rights to
its first-party contents. Runtime source changes require separate evidence,
rebuild and a fresh signature with an external key. No private key belongs in
this repository.
