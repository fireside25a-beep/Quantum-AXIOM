#!/usr/bin/env python3
"""Test a signed snapshot using disposable copies; never mutate the input.

Run after signing. JSON is written to stdout so it can be stored outside the
signed tree. A publisher may include the report and then re-sign the snapshot.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

R=Path(__file__).resolve().parents[1]

def main():
    report={'status':'FAIL','cases':{}}
    cases=('pristine','changed_payload','changed_manifest','unsigned_extra',
           'symlink','optimized_unsigned_extra','git_metadata')
    with tempfile.TemporaryDirectory(prefix='axiom-distribution-') as d:
        for name in cases:
            target=Path(d)/name
            shutil.copytree(R,target,ignore=shutil.ignore_patterns('.git','__pycache__','*.o'))
            if name=='changed_payload':
                with (target/'README.md').open('a') as file:
                    file.write('\nUNTRUSTED MODIFICATION\n')
            elif name=='changed_manifest':
                path=target/'security/MANIFEST_SHA256.txt'
                b=bytearray(path.read_bytes())
                b[0]^=1
                path.write_bytes(b)
            elif name in ('unsigned_extra','optimized_unsigned_extra'):
                (target/'UNSIGNED.txt').write_text('unsigned payload\n')
            elif name=='symlink':
                (target/'UNSIGNED_LINK').symlink_to('README.md')
            elif name=='git_metadata':
                (target/'.git').mkdir()
                (target/'.git/HEAD').write_text('ref: refs/heads/main\n')
            env=dict(os.environ)
            if name=='optimized_unsigned_extra':env['PYTHONOPTIMIZE']='1'
            p=subprocess.run(['bash',str(target/'security/VERIFY_RELEASE.sh')],
                             capture_output=True,text=True,timeout=20,env=env)
            expected_accept=name in ('pristine','git_metadata')
            if (p.returncode==0)!=expected_accept:
                raise AssertionError((name,p.returncode,p.stdout,p.stderr))
            report['cases'][name]={'exit_code':p.returncode,'expected_accept':expected_accept,
                                   'observed_accept':p.returncode==0,'passed':True}
    report['status']='PASS'
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
