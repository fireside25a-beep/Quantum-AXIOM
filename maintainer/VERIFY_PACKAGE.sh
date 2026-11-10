#!/bin/sh
set -eu
cd "$(dirname "$0")"
if find . -type l -print -quit | grep -q .; then echo 'Symlink in package' >&2; exit 5; fi
if [ -f MANIFEST.ed25519.sig ] || [ -f package_public_ed25519.pem ]; then
  test -s MANIFEST.ed25519.sig && test -s package_public_ed25519.pem
  openssl pkeyutl -verify -pubin -inkey package_public_ed25519.pem -sigfile MANIFEST.ed25519.sig -in MANIFEST_SHA256.txt -rawin >/dev/null
  echo 'Ed25519 package signature verified; independently pin the public key for publisher identity.'
else
  echo 'Unsigned package inventory; no publisher authentication is asserted.'
fi
sha256sum -c --status MANIFEST_SHA256.txt
actual=$(mktemp)
expected=$(mktemp)
cleanup() { rm -f "$actual" "$expected"; }
trap cleanup EXIT HUP INT TERM
find . -type f ! -path './MANIFEST_SHA256.txt' ! -path './MANIFEST.ed25519.sig' | LC_ALL=C sort > "$actual"
cut -c67- MANIFEST_SHA256.txt | LC_ALL=C sort > "$expected"
cmp "$actual" "$expected"
echo 'PASS: all package payload hashes and exact file inventory.'
