# Security scope

The restricted quantum guest ISA has checked code views, ownership, stack depth and fuel. Arbitrary native ANF64 programs are unrestricted Linux machine code. Read `application/security/SECURITY_MODEL.md` before treating either as a security boundary.

SHA-256 inventories detect changed payloads. The complete application's Ed25519 signature establishes snapshot consistency with its supplied key; trusted publisher identity requires an independently authenticated fingerprint. The tag workflow uses read permissions for validation and grants release write permission only to the publishing job.

Avoid including private source inputs, credentials or secret-bearing journals in public reports. No private signing key belongs in a commit, release asset or GitHub issue.
