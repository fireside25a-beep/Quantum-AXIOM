#!/usr/bin/env python3
"""Adversarial input, bootstrap, rebuild and cross-interface regressions.

Tests execute actual compiled targets; no program output is substituted.
"""
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import threading
import time
import unittest

R = Path(__file__).resolve().parents[1]
B = R / 'native/dense/bin'
E = R / 'native/seed/native_seed_emitter.x86_64'
SEED = R / 'native/dense/compiled.release_seed.qseed'
spec = importlib.util.spec_from_file_location('bitseed', R / 'native/seed/encode_bitseed.py')
encoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(encoder)
from native_dense_regression import fnv64, decode, oracle, parse_output
from native_clifford_independent import state, apply, parse_file, CANONICAL

def run(*args, data=None):
    return subprocess.run(list(map(str, args)), input=data, capture_output=True, timeout=30)

class ReleaseRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='axiom-regression-')
        self.p = Path(self.tmp.name)
        self.index = 0

    def tearDown(self):
        self.tmp.cleanup()

    def compile(self, source, seed=SEED):
        self.index += 1
        src = self.p / f'{self.index}.ql'
        out = self.p / f'{self.index}.qvb'
        src.write_bytes(source.encode() if isinstance(source, str) else source)
        return run(B / 'native_q_compile', src, seed, out), out

    def test_parser_missing_if_operands_refused_without_crash(self):
        for kind in ('IF1', 'IF0'):
            for args in ('', ' 0', ' 0 X', ' 0 UNKNOWN 1', ' 0 #', ' -1 X 0'):
                result, out = self.compile('qubits 2\ncbits 1\n' + kind + args + '\n')
                self.assertGreater(result.returncode, 0, (kind, args, result))
                self.assertFalse(out.exists())

    def test_nul_non_ascii_and_long_lines_refused(self):
        for suffix in (b'H 0\0 H 1\n', b'#comment\0H 0\n', b'H 0\xff\n',
                       b'H 0' + b' ' * 1020 + b'\n'):
            result, out = self.compile(b'qubits 2\n' + suffix)
            self.assertGreater(result.returncode, 0)
            self.assertFalse(out.exists())
        good, _ = self.compile('qubits 2\nH 0')
        self.assertEqual(good.returncode, 0)

    def test_seed_flags_consistent_with_sdk(self):
        sdk = ctypes.CDLL(str(R / 'native/dense/sdk/libnative_quantum_abi.so'))
        sdk.qvu_abi_seed_validate.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        sdk.qvu_abi_seed_validate.restype = ctypes.c_int
        for flags in (0, 1, 2, 3, 4, 5, 6, 7, 8, 0xffffffff):
            blob = bytearray(SEED.read_bytes())
            struct.pack_into('<I', blob, 12, flags)
            seed = self.p / f'flags{flags}.seed'
            seed.write_bytes(blob)
            expected = sdk.qvu_abi_seed_validate(ctypes.create_string_buffer(bytes(blob)), 64)
            result, _ = self.compile('qubits 2\nH 0\n', seed)
            self.assertEqual(result.returncode == 0, expected == 0, flags)

    def test_rz_parameter_consistency_across_three_native_interfaces(self):
        result, pkt = self.compile('qubits 2\nRZ8 0 0\n')
        self.assertEqual(result.returncode, 0)
        raw = pkt.read_bytes()
        sdk = ctypes.CDLL(str(R / 'native/dense/sdk/libnative_quantum_abi.so'))
        sdk.qvu_abi_packet_validate.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        sdk.qvu_abi_packet_validate.restype = ctypes.c_int
        for value in (-2147483648, -65536, -65535, -1, 0, 65535, 65536, 2147483647):
            blob = bytearray(raw)
            struct.pack_into('<i', blob, 52, value)
            struct.pack_into('<Q', blob, 32, fnv64(blob[48:]))
            pkt.write_bytes(blob)
            expected = -65535 <= value <= 65535
            self.assertEqual(sdk.qvu_abi_packet_validate(ctypes.create_string_buffer(bytes(blob)), len(blob)) == 0, expected)
            for tool in ('native_q_inspect', 'native_q_execute'):
                self.assertEqual(run(B / tool, pkt).returncode == 0, expected, (tool, value))

    def test_native_emitter_full_capacity_and_streamed_pipe(self):
        rng = random.Random(0xA810)
        for size in (1, 4432, 10624, 16384):
            raw = rng.randbytes(size)
            encoded = encoder.encode(raw)
            # communicate uses a pipe; the historical one-read decoder fails
            # whenever a pipe read returns less than the complete input.
            result = run(E, data=encoded)
            self.assertEqual(result.returncode, 0, size)
            self.assertEqual(result.stdout, raw)
        encoded = encoder.encode(b'fragmented native input' * 17)
        proc = subprocess.Popen([str(E)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        failures = []
        def writer():
            try:
                for pos in range(0, len(encoded), 31):
                    proc.stdin.write(encoded[pos:pos+31])
                    proc.stdin.flush()
                    time.sleep(0.0002)
            except Exception as exc:
                failures.append(repr(exc))
            finally:
                proc.stdin.close()
        thread = threading.Thread(target=writer)
        thread.start()
        out = proc.stdout.read()
        error = proc.stderr.read()
        proc.stdout.close()
        proc.stderr.close()
        self.assertEqual(proc.wait(timeout=10), 0, error)
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        self.assertFalse(failures)
        self.assertEqual(out, b'fragmented native input' * 17)

    def test_native_emitter_repairs_and_refuses_invalid_input(self):
        raw = E.read_bytes()
        base = encoder.encode(raw)
        for lane in range(3):
            damaged = bytearray(base)
            for i in range(len(raw)):
                damaged[16 + lane * len(raw) + i] ^= 0xff
            result = run(E, data=damaged)
            self.assertEqual((result.returncode, result.stdout), (0, raw))
        for damaged in (base[:-1], base + b'x', b'X' + base[1:], b'x' * 49169):
            result = run(E, data=damaged)
            self.assertGreater(result.returncode, 0)
            self.assertFalse(result.stdout)
        damaged = bytearray(base)
        damaged[16] ^= 1
        damaged[16 + len(raw)] ^= 1
        result = run(E, data=damaged)
        self.assertGreater(result.returncode, 0)
        self.assertFalse(result.stdout)
        probe = R / 'security/native_emitter_probe.x86_64'
        result = run(probe, data=base)
        self.assertIn(result.returncode, (-9, -31))
        self.assertFalse(result.stdout)

    def test_seed_generations_independent_full_state(self):
        image = (R / 'native/seed/genesis.x86_64').read_bytes()
        ops = parse_file(R / 'native/seed/nucleus.qcl')
        rows = CANONICAL
        hashes = []
        for generation in range(1, 25):
            path = self.p / 'seed.x86_64'
            path.write_bytes(image)
            path.chmod(0o700)
            result = run(path)
            self.assertEqual(result.returncode, 0)
            epoch, actual = state(result.stdout)
            rows = apply(rows, ops)
            self.assertEqual((epoch, actual), (generation, rows))
            # Test native ternary transition against independent integer math,
            # using the actually observed hardware draw, never a guessed draw.
            d = 8192
            previous = struct.unpack_from('<Q', image, d + 16)[0]
            draw = struct.unpack_from('<Q', result.stdout, d + 56)[0]
            mask = (1 << 64) - 1
            rot = lambda x, n: ((x << n) | (x >> (64-n))) & mask
            mixed = previous ^ rot(previous, 1) ^ rot(draw, 47) ^ draw
            mixed ^= rot(mixed, 23)
            lo = mixed & 0xffffffff
            ror11 = ((lo >> 11) | (lo << 21)) & 0xffffffff
            rol7 = ((lo << 7) | (lo >> 25)) & 0xffffffff
            predicted = (lo & ~ror11) | ((rol7 & ~lo) << 32)
            actual_logical = struct.unpack_from('<Q', result.stdout, d+16)[0]
            self.assertEqual(actual_logical, predicted)
            self.assertEqual(struct.unpack_from('<Q', result.stdout, d+64)[0], previous ^ predicted)
            hashes.append(hashlib.sha256(result.stdout).hexdigest())
            image = result.stdout
        self.assertEqual(len(set(hashes)), 24)
        (R / 'evidence/native_seed_generations.json').write_text(json.dumps({'status': 'PASS', 'generations': 24, 'full_tableau_oracle': True, 'ternary_transition_oracle': True, 'image_sha256_chain': hashes}, indent=2)+'\n')

    def test_resident_header_corruption_refused(self):
        base = (R / 'native/seed/genesis.x86_64').read_bytes()
        path = self.p / 'invalid.x86_64'
        for offset in (0, 80, 88):
            damaged = bytearray(base)
            damaged[8192+offset] ^= 1
            path.write_bytes(damaged)
            path.chmod(0o700)
            result = run(path)
            self.assertEqual((result.returncode, result.stdout), (74, b''))

    def test_runtime_failure_unwinds_nested_frame(self):
        good, packet = self.compile('qubits 1\nH 0\nMEASURE 0 0\n')
        self.assertEqual(good.returncode, 0)
        replay = self.p / 'empty.draws'
        replay.write_bytes(b'')
        result = run(B / 'native_q_execute', packet, replay)
        self.assertEqual(result.returncode, 3, result.stderr)
        # A write error after successful arithmetic must also refuse success.
        with open('/dev/full', 'wb') as sink:
            result = subprocess.run([str(B / 'native_q_execute'), str(packet)], stdout=sink, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 3, result.stderr)

    def test_optimized_clifford_compiler_rejects_invalid_sites(self):
        compiler = R / 'native/clifford/native_clifford_compiler.py'
        for source in ('sites 32\nH -1\n', 'sites 32\nH 32\n', 'sites 32\nCX 0 0\n'):
            path = self.p / 'bad.qcl'
            path.write_text(source)
            result = run('python3', '-O', compiler, path, self.p / 'bad.native')
            self.assertGreater(result.returncode, 0)

    def test_large_input_reads_are_bounded(self):
        compiler=R/'native/clifford/native_clifford_compiler.py'
        large=self.p/'large.input'
        with large.open('wb') as file:
            file.seek(512*1024*1024)
            file.write(b'X')
        result=run('python3',compiler,large,self.p/'refused.x86_64')
        self.assertGreater(result.returncode,0)
        self.assertIn(b'oversized program',result.stderr)
        self.assertFalse((self.p/'refused.x86_64').exists())
        source=self.p/'small.qcl';source.write_text('sites 32\nH 0\n')
        result=run('python3',compiler,source,self.p/'refused.x86_64',self.p/'audit.json',large)
        self.assertGreater(result.returncode,0)
        self.assertIn(b'tableau snapshot exceeds',result.stderr)
        self.assertFalse((self.p/'refused.x86_64').exists())

    def test_rebuild_all_from_sources_only_byte_exact(self):
        clean = self.p / 'clean'
        def ignore(folder, names):
            return [name for name in names if name in ('.git', '__pycache__') or name.endswith(('.x86_64', '.pyc', '.o', '.so', '.a', '.bits', '.qvb', '.seed')) or (Path(folder).name == 'bin')]
        shutil.copytree(R, clean, ignore=ignore)
        result = run('make', '-C', clean, 'all')
        self.assertEqual(result.returncode, 0, result.stderr[-3000:])
        outputs = sorted(p for p in R.rglob('*') if p.is_file() and
                         (p.suffix in ('.x86_64', '.a', '.so', '.bits', '.qvb', '.seed') or p.parent == B))
        # Only actively built targets, never historical trace descendants.
        outputs = [p for p in outputs if str(p.relative_to(R)).startswith(('native/', 'security/', 'examples/'))]
        outputs = [p for p in outputs if 'probe' not in p.name or p.name in
                   ('native_emitter_probe.x86_64', 'native_q_execute_bpf_probe.x86_64', 'native_q_compile_bpf_probe.x86_64')]
        for original in outputs:
            rebuilt = clean / original.relative_to(R)
            self.assertTrue(rebuilt.is_file(), original)
            self.assertEqual(original.read_bytes(), rebuilt.read_bytes(), original)
        self.assertGreaterEqual(len(outputs), 18)
        (R / 'evidence/source_only_rebuild.json').write_text(json.dumps({'status': 'PASS', 'outputs': [str(p.relative_to(R)) for p in outputs], 'byte_identical': True}, indent=2)+'\n')

    def test_sdk_header_compiles_and_links_native_library(self):
        packet=(R/'native/dense/grover_2.qvb').read_bytes()
        source=self.p/'consumer.c'
        array=lambda data: ','.join(str(x) for x in data)
        source.write_text('#include "axiom_qvu.h"\n'
            +'static uint8_t packet[]={'+array(packet)+'};\n'
            +'static const uint8_t seed[]={'+array(SEED.read_bytes())+'};\n'
            +'int main(void) {\n'
            +'if(qvu_abi_seed_validate(seed,sizeof seed)!=0) return 1;\n'
            +'if(qvu_abi_packet_validate(packet,sizeof packet)!=0) return 2;\n'
            +'packet[0]^=1; return qvu_abi_packet_validate(packet,sizeof packet)==-1 ? 0 : 3;\n}\n')
        executable=self.p/'consumer'
        result=run('gcc','-std=c11','-Wall','-Wextra','-Werror','-I',R/'native/dense/sdk',source,R/'native/dense/sdk/libnative_quantum_abi.a','-o',executable)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(run(executable).returncode,0)

if __name__ == '__main__':
    unittest.main(verbosity=2)
