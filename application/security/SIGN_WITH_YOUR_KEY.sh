#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo 'usage: bash security/SIGN_WITH_YOUR_KEY.sh /absolute/outside/path/ed25519_private_key.pem' >&2;exit 2;fi
cd "$(dirname "$0")/.."
private=$(realpath "$1")
root=$(pwd -P)
if [[ "$private" == "$root"/* ]]; then echo 'REFUSED: private key must be OUTSIDE release root' >&2;exit 3;fi
umask 077
openssl pkey -in "$private" -pubout -out security/release_public_ed25519.pem
export LC_ALL=C
find . -path './.git' -prune -o -type f ! -path './security/MANIFEST_SHA256.txt' ! -path './security/release_manifest.ed25519.sig' -print0 | sort -z | xargs -0 sha256sum > security/MANIFEST_SHA256.txt
openssl pkeyutl -sign -inkey "$private" -in security/MANIFEST_SHA256.txt -rawin -out security/release_manifest.ed25519.sig
bash security/VERIFY_RELEASE.sh
