#!/bin/sh
set -eu
bindir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$bindir/.." && pwd)
command=${1:-help}
if [ "$#" -gt 0 ]; then shift; fi
case "$command" in
  compile) exec "$bindir/axiom-compile" "$@" ;;
  run) exec "$bindir/axiom-machine" "$@" ;;
  history) exec "$bindir/axiom-history" "$@" ;;
  seed) exec "$bindir/axiom-seed" "$@" ;;
  dense-compile|dense-run|dense-inspect|dense-seed) exec "$bindir/axiom-$command" "$@" ;;
  version) printf 'AXIOM Native Fabric '; cat "$root/share/axiom/VERSION" ;;
  doctor)
    printf 'Platform: %s / %s\n' "$(uname -s)" "$(uname -m)"
    [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || { echo 'Linux x86-64 is required' >&2; exit 65; }
    printf 'Dense tools require glibc >= 2.41; detected: '
    getconf GNU_LIBC_VERSION 2>/dev/null || true
    if grep -qw rdseed /proc/cpuinfo 2>/dev/null; then
      echo 'RDSEED advertised; each entropy instruction still checks actual availability.'
    else
      echo 'RDSEED is not advertised: entropy-dependent programs will refuse execution.'
    fi
    ;;
  demo|selfhost)
    work=$(mktemp -d "${TMPDIR:-/tmp}/axiom-check.XXXXXXXX")
    cleanup() { rm -f "$work/compiler" "$work/next" "$work/program.seed" "$work/program.history" "$work/reverse.history" "$work/again.history" "$work/restored.seed"; rmdir "$work"; }
    trap cleanup EXIT HUP INT TERM
    if [ "$command" = selfhost ]; then
      "$bindir/axiom-seed" < "$root/share/axiom/bootstrap/compiler_seed.bits" > "$work/compiler"
      chmod 700 "$work/compiler"
      cmp "$work/compiler" "$bindir/axiom-compile"
      for generation in 1 2 3; do
        "$work/compiler" < "$root/share/axiom/bootstrap/compiler.anf" > "$work/next"
        cmp "$work/compiler" "$work/next"
        mv "$work/next" "$work/compiler"
        chmod 700 "$work/compiler"
      done
      echo 'PASS: encoded seed reconstruction and three native source self-compilations.'
    else
      "$bindir/axiom-compile" < "$root/share/axiom/examples/Machine/nested_quantum.anf" > "$work/program.seed"
      "$bindir/axiom-machine" < "$work/program.seed" > "$work/program.history"
      "$bindir/axiom-history" < "$work/program.history" > "$work/reverse.history"
      "$bindir/axiom-history" < "$work/reverse.history" > "$work/again.history"
      cmp "$work/program.history" "$work/again.history"
      "$bindir/axiom-history" seed < "$work/reverse.history" > "$work/restored.seed"
      cmp "$work/program.seed" "$work/restored.seed"
      echo 'PASS: native nested guests, two history reversals and byte-exact seed restoration.'
    fi
    ;;
  help|--help|-h)
    echo 'AXIOM Native Fabric'
    echo 'usage: axiom {compile|run|history [seed|state|next]|seed}'
    echo '       axiom {dense-compile|dense-run|dense-inspect|dense-seed} [arguments]'
    echo '       axiom {doctor|demo|selfhost|version}'
    echo 'Native compile/run/history use stdin and stdout; redirect binary outputs.'
    ;;
  *) echo "Unknown command: $command" >&2; exit 64 ;;
esac
