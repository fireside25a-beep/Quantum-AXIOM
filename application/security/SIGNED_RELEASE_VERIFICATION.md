# Signed standalone release verification

From the extracted archive's root:

```sh
bash security/VERIFY_RELEASE.sh
```

The verifier checks an Ed25519 detached signature over the exact `security/MANIFEST_SHA256.txt` bytes, compares all SHA-256 file hashes, rejects unsigned additional files, and checks that the manifest and signature themselves are the only excluded regular files. Public verification key: `security/release_public_ed25519.pem`; signature: `security/release_manifest.ed25519.sig`. Private signing material is never packaged. No publisher identity is established without a separately trusted copy/fingerprint of the public key.

The adversarial test perturbs disposable copies and verifies rejection of changed content, a changed manifest, unsigned files and symlinks, including with Python optimization enabled. See `evidence/signature_tamper.json`. The signed artifact is immutable: perform rebuilds in a disposable extraction. The verifier prints the current DER public-key SHA-256 fingerprint; it is not a third-party identity certificate.

Git administrative metadata under `.git/` is excluded from the distribution inventory so the same content can be checked in a repository checkout. Tracked project payload, including `.github/`, remains covered.
