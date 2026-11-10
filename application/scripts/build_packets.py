#!/usr/bin/env python3
"""Rebuild all example packets through the native assembly compiler.

Each compile uses a fresh exclusive-create output. Verified success is then
installed in the build tree. The fixed seed is a nonsecret replay fixture.
"""
from pathlib import Path
import os
import subprocess
import tempfile

R = Path(__file__).resolve().parents[1]
D = R / 'native/dense'
for source in sorted((R / 'examples/Dense').rglob('*.ql')):
    target = (D / 'repetition_compiled' if source.parent.name == 'Repetition' else D) / (source.stem+'.qvb')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.packets-', dir=D) as temp:
        fresh = Path(temp) / 'program.qvb'
        result = subprocess.run([str(D/'bin/native_q_compile'), str(source),
                                 str(D/'compiled.release_seed.qseed'), str(fresh)],
                                capture_output=True, text=True, timeout=15)
        if result.returncode:
            raise SystemExit(f'{source.name}: {result.stderr}')
        os.replace(fresh, target)
print('NATIVE EXAMPLE PACKETS REBUILT')
