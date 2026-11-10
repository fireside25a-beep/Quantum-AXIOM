#!/usr/bin/env python3
"""Measured end-to-end CLI cost on this host; no quantum-speedup inference."""
import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time

R=Path(__file__).resolve().parents[1]
B=R/'native/dense/bin'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repetitions',type=int,default=5)
    a=parser.parse_args()
    if not 3<=a.repetitions<=100:raise SystemExit('repetitions must be 3..100')
    result={'status':'FAIL','platform':platform.platform(),'scope':'process creation, packet I/O, allocation, five native gates, final output, termination',
            'controls':'same executable, seed fixture and five-gate schedule; sites varied',
            'rss_method':'per-child wait4 resource usage, KiB on Linux; process high-water metric',
            'exclusions':['not an isolated kernel benchmark','CPU frequency/thermal state not controlled','no quantum-speedup comparison'],
            'cases':[]}
    with tempfile.TemporaryDirectory(prefix='axiom-benchmark-') as folder:
        p=Path(folder)
        for n in (4,8,12,16,20):
            source=p/f'{n}.ql';packet=p/f'{n}.qvb'
            source.write_text(f'qubits {n}\ncbits 1\nH 0\nCX 0 {n-1}\nT {n-1}\nCZ 0 {n-1}\nH 0\n')
            subprocess.run([str(B/'native_q_compile'),str(source),str(R/'native/dense/compiled.release_seed.qseed'),str(packet)],capture_output=True,check=True,timeout=10)
            samples=[];rss=[]
            for _ in range(a.repetitions):
                stdout=p/'stdout.txt';stderr=p/'stderr.txt'
                started=time.perf_counter_ns()
                actions=[(os.POSIX_SPAWN_OPEN,fd,str(path),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
                         for fd,path in ((1,stdout),(2,stderr))]
                pid=os.posix_spawn(str(B/'native_q_execute'),[str(B/'native_q_execute'),str(packet)],os.environ,file_actions=actions)
                _,status,usage=os.wait4(pid,0)
                elapsed=time.perf_counter_ns()-started
                code=os.waitstatus_to_exitcode(status)
                if code or 'QVU_FINAL' not in stdout.read_text():raise AssertionError((n,code,stderr.read_text()))
                samples.append(elapsed);rss.append(usage.ru_maxrss)
            result['cases'].append({'sites':n,'complex_state_slots':1<<n,'state_buffer_bytes':16*(1<<n),
                                    'operations':5,'repetitions':a.repetitions,'elapsed_ns':samples,
                                    'median_elapsed_ns':statistics.median(samples),'peak_rss_kib':rss,
                                    'maximum_peak_rss_kib':max(rss)})
    result['status']='PASS'
    (R/'evidence/native_benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
