# Working on AXIOM

Read the root LICENSE and LICENSING.md for the Apache-2.0 grant covering first-party contents. Preserve the reference source's own license and notice.

Preserve the signed application snapshot. Work in a separate copy, make a focused change, and run the connected verification suite. Native/oracle disagreement, changed compiler generations, invalid guest ownership or a broken inverse check are failures. Retain negative evidence and actual hardware-entropy observations; do not substitute oracle results for executable output.

Application sources, ABI documents and scientific limits belong under `application/`. README artwork belongs under `presentation/`. Packaging and publishing tools belong under `maintainer/`. Keep those responsibilities separate so presentation changes never become runtime dependencies.
