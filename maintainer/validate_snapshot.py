#!/usr/bin/env python3
"""Portable read-only hash validation; native and Ed25519 gates run in Linux CI."""
import hashlib
import json
from pathlib import Path
import re

R=Path(__file__).resolve().parents[1]
A=R/'application'
manifest=A/'security/MANIFEST_SHA256.txt'
excluded={'security/MANIFEST_SHA256.txt','security/release_manifest.ed25519.sig'}
expected={}
for line in manifest.read_text().splitlines():
    match=re.fullmatch(r'([0-9a-f]{64})  \./([^\r\n]+)',line)
    if not match:raise SystemExit('malformed application manifest')
    digest,name=match.groups()
    if Path(name).is_absolute() or '..' in Path(name).parts or name in expected:
        raise SystemExit('unsafe or duplicate application path')
    expected[name]=digest
actual={}
for p in A.rglob('*'):
    if p.is_symlink():raise SystemExit('application symlink: '+str(p))
    if p.is_file() and p.relative_to(A).as_posix() not in excluded:
        actual[p.relative_to(A).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
if actual!=expected:raise SystemExit('application hash inventory mismatch')
summary=json.loads((A/'evidence/VERIFICATION_SUMMARY.json').read_text())
if summary['status']!='PASS':raise SystemExit('recorded execution suite incomplete')
if not re.fullmatch(r'g[0-9]+(?:\.[0-9]+)*',(R/'VERSION').read_text().strip()):
    raise SystemExit('invalid distribution version')
print('PASS: portable application file/hash inventory ('+str(len(actual))+' payload files).')
print('Ed25519 verification and native execution remain mandatory Linux CI gates.')
