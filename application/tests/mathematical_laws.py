#!/usr/bin/env python3
"""Independent complex-number gate definitions, separate from the Q30 oracle.

Floating point is used only here for a numerical cross-check of the native
integer implementation. No third-party quantum/simulator package is used.
"""
import cmath
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile
from native_dense_regression import parse_output, Q30

R = Path(__file__).resolve().parents[1]
B = R / 'native/dense/bin'

def run(*args):
    p = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=15)
    if p.returncode:
        raise AssertionError((args, p.returncode, p.stderr))
    return p.stdout

def apply(state, gate):
    """Apply independent 2x2 matrix definitions to a complex vector."""
    name, q, *more = gate
    out = list(state)
    if name in ('CX', 'CZ'):
        t = more[0]
        for i in range(len(state)):
            if i & (1 << q):
                if name == 'CX':
                    out[i ^ (1 << t)] = state[i]
                elif i & (1 << t):
                    out[i] = -state[i]
        return out
    s = math.sqrt(0.5)
    z = cmath.exp(1j * math.pi / 4)
    matrix = {'H': ((s, s), (s, -s)), 'X': ((0, 1), (1, 0)),
              'Y': ((0, -1j), (1j, 0)), 'Z': ((1, 0), (0, -1)),
              'S': ((1, 0), (0, 1j)), 'SDG': ((1, 0), (0, -1j)),
              'T': ((1, 0), (0, z)), 'TDG': ((1, 0), (0, z.conjugate()))}[name]
    for i in range(len(state)):
        if i & (1 << q):
            continue
        j = i | (1 << q)
        out[i] = matrix[0][0] * state[i] + matrix[0][1] * state[j]
        out[j] = matrix[1][0] * state[i] + matrix[1][1] * state[j]
    return out

def main():
    rng = random.Random(0xA810A)
    report = {'status': 'FAIL', 'unitary_programs': 0, 'inverse_programs': 0,
              'born_boundary_cases': 0, 'max_complex_amplitude_error': 0.0,
              'max_absolute_probability_norm_error': 0.0,
              'measurement_reversible_claim': False, 'physical_quantum_claim': False}
    with tempfile.TemporaryDirectory(prefix='axiom-laws-') as d:
        p = Path(d)
        def execute(nq, gates, name):
            source = p / (name+'.ql')
            packet = p / (name+'.qvb')
            source.write_text(f'qubits {nq}\ncbits 1\n' +
                              '\n'.join(' '.join(map(str, g)) for g in gates)+'\n')
            run(B/'native_q_compile', source, R/'native/dense/compiled.release_seed.qseed', packet)
            text = run(B/'native_q_execute', packet)
            _, _, _, final, amp = parse_output(text)
            return packet, final, amp
        for case in range(48):
            nq = rng.randint(2, 5)
            gates = []
            for _ in range(rng.randint(8, 48)):
                kind = rng.choice(('H', 'X', 'Y', 'Z', 'S', 'SDG', 'T', 'TDG', 'CX', 'CZ'))
                q = rng.randrange(nq)
                gates.append((kind, q, (q+rng.randrange(1,nq)) % nq) if kind in ('CX','CZ') else (kind,q))
            reference = [0j] * (1 << nq)
            reference[0] = 1
            for gate in gates:
                reference = apply(reference, gate)
            _, final, amp = execute(nq, gates, f'unitary{case}')
            error = max(abs(complex(*amp.get(i,(0,0))) / Q30 - value)
                        for i, value in enumerate(reference))
            norm_error = abs(final['norm'] / Q30**2 - 1)
            if error > 2e-7 or norm_error > 2e-7:
                raise AssertionError((case, error, norm_error))
            report['max_complex_amplitude_error'] = max(error, report['max_complex_amplitude_error'])
            report['max_absolute_probability_norm_error'] = max(norm_error, report['max_absolute_probability_norm_error'])
            report['unitary_programs'] += 1
            inverse_names = {'S':'SDG','SDG':'S','T':'TDG','TDG':'T'}
            inverse = [(inverse_names.get(g[0],g[0]),*g[1:]) for g in reversed(gates)]
            _, _, amp = execute(nq, gates+inverse, f'inverse{case}')
            error = max(abs(complex(*amp.get(i,(0,0))) / Q30 - int(i==0)) for i in range(1<<nq))
            if error > 4e-7:
                raise AssertionError(('inverse', case, error))
            report['inverse_programs'] += 1
        packet, _, _ = execute(1, [('H',0),('MEASURE',0,0)], 'born')
        replay = p/'draw.bin'
        for draw, outcome in ((0,1),(2**31-1,1),(2**31,0),(2**32-1,0)):
            replay.write_bytes(struct.pack('<I',draw))
            _, _, measured, final, amp = parse_output(run(B/'native_q_execute',packet,replay))
            if measured != [outcome] or final['classical'] != outcome or set(amp) != {outcome}:
                raise AssertionError((draw,measured,amp))
            report['born_boundary_cases'] += 1
    report['status'] = 'PASS'
    (R/'evidence/mathematical_laws.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
