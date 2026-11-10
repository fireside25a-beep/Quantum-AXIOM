#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
key=security/release_public_ed25519.pem
manifest=security/MANIFEST_SHA256.txt
sig=security/release_manifest.ed25519.sig
test -s "$key" && test -s "$manifest" && test -s "$sig" || { echo 'MISSING RELEASE SIGNATURE MATERIAL' >&2; exit 2; }
openssl pkeyutl -verify -pubin -inkey "$key" -sigfile "$sig" -in "$manifest" -rawin > /dev/null || { echo 'ED25519 SIGNATURE INVALID' >&2; exit 3; }
if find . -path './.git' -prune -o -type l -print -quit | grep -q .; then echo 'UNSIGNED SYMLINK IN DISTRIBUTION' >&2; exit 5; fi
sha256sum -c --status "$manifest" || { echo 'SHA256 MANIFEST CONTENT MISMATCH' >&2; exit 4; }
# No unsigned payloads are allowed inside the release root. The signature and manifest
# are the only deliberately excluded files. A malicious key replacement still requires
# independent fingerprint pinning: this checker is not certificate-based identity.
python3 - <<'PY'
from pathlib import Path
root=Path('.')
manifest=Path('security/MANIFEST_SHA256.txt').read_text().splitlines()
names=set()
for line in manifest:
 if len(line)<=67 or line[64:66]!='  ':raise SystemExit('MALFORMED MANIFEST LINE')
 name=line[66:].removeprefix('./')
 if name in names or Path(name).is_absolute() or '..' in Path(name).parts:raise SystemExit('UNSAFE OR DUPLICATE MANIFEST PATH')
 names.add(name)
ignore={'security/MANIFEST_SHA256.txt','security/release_manifest.ed25519.sig'}
files={x.as_posix() for x in root.rglob('*') if x.is_file() and '.git' not in x.parts}
if files-names!=ignore:raise SystemExit('UNSIGNED EXTRA FILES: '+str(sorted(files-names-ignore)))
if names-files:raise SystemExit('MANIFEST REFERENCED MISSING FILES: '+str(sorted(names-files)))
print('RELEASE CONTENT INVENTORY PASS files=',len(names))
PY
fingerprint=$(openssl pkey -pubin -in "$key" -outform DER | sha256sum | awk '{print $1}')
printf 'ED25519 signature verified, SHA256 inventory verified. Public-key DER fingerprint: %s\n' "$fingerprint"
