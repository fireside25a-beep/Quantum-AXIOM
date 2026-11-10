#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ ${1:-} == --check ]] || { echo 'usage: bash maintainer/publish.sh --check' >&2; exit 64; }
expected='https://github.com/fireside25a-beep/Quantum-AXIOM.git'
[[ $(git rev-parse --show-toplevel) == "$PWD" ]]
[[ $(git branch --show-current) == main ]]
[[ -z $(git status --porcelain) ]]
[[ $(git remote get-url origin) == "$expected" ]]
[[ $(gh api user --jq .login) == fireside25a-beep ]]
python3 -B maintainer/validate_snapshot.py
if [[ -n $(git ls-remote origin) ]]; then
  echo 'STOP: remote contains history; reconcile explicitly, no push performed.' >&2
  exit 1
fi
printf 'PASS: clean local main, verified owner and empty existing HTTPS remote. No push performed.\n'
