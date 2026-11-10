#!/usr/bin/env python3
"""Integration checks for extracted downloads, native demos and Git exports."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from package_release import tracked_project_files

R=Path(__file__).resolve().parents[1]

def run(*args,cwd=None,data=None,accept=0):
    p=subprocess.run(list(map(str,args)),cwd=cwd,input=data,capture_output=True,timeout=120,
                     env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    if p.returncode!=accept:raise AssertionError((args,p.returncode,p.stderr[-2000:]))
    return p.stdout

def extract(path,dest):
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise AssertionError('bad archive CRC')
        names=z.namelist()
        if len(names)!=len(set(names)):raise AssertionError('duplicate archive path')
        roots={Path(n).parts[0] for n in names}
        if len(roots)!=1:raise AssertionError('archive root')
        for info in z.infolist():
            p=Path(info.filename)
            if p.is_absolute() or '..' in p.parts or stat.S_ISLNK(info.external_attr>>16):raise AssertionError('unsafe archive entry')
            z.extract(info,dest)
            if not info.is_dir():(dest/info.filename).chmod((info.external_attr>>16)&0o777)
    return dest/next(iter(roots)),names

def svg_checks():
    result=[]
    for p in sorted((R/'presentation').glob('*.svg')):
        root=ET.fromstring(p.read_bytes())
        if not root.tag.endswith('svg') or not root.attrib.get('viewBox'):raise AssertionError('invalid SVG')
        for node in root.iter():
            if node.tag.split('}')[-1] in ('script','foreignObject','animate','set'):raise AssertionError('active SVG')
            for key,value in node.attrib.items():
                if key.lower().startswith('on') or ('href' in key and not value.startswith('#')):raise AssertionError('external/active SVG')
        result.append(p.name)
    if len(result)!=4:raise AssertionError('missing README panels')
    return result

def archive_check(tmp):
    # Use a disposable Git repository if this is an extracted handoff without .git.
    repo=R
    if not (repo/'.git').is_dir():
        repo=tmp/'git-export-source'
        shutil.copytree(R,repo,ignore=shutil.ignore_patterns('.git','dist','build','__pycache__'))
        run('git','init','-q','-b','main',cwd=repo)
        run('git','add','.',cwd=repo)
        run('git','-c','user.name=AXIOM Release Preparation','-c','user.email=release-preparation@localhost','commit','-qm','Prepare standalone distribution',cwd=repo)
    else:
        run('git','diff','--exit-code',cwd=repo)
        run('git','diff','--cached','--exit-code',cwd=repo)
    raw=run('git','archive','--format=zip','HEAD',cwd=repo)
    archive=tmp/'source-export.zip';archive.write_bytes(raw)
    with zipfile.ZipFile(archive) as z:
        expected={p.relative_to(R).as_posix() for p in tracked_project_files()}
        actual={name for name in z.namelist() if not name.endswith('/')}
        if actual!=expected:raise AssertionError(('source export incomplete',expected-actual,actual-expected))
        for name in expected:
            if z.read(name)!=(R/name).read_bytes():raise AssertionError(('Git source bytes changed',name))
    return len(expected)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist',type=Path,default=R/'dist')
    parser.add_argument('--verified-application',type=Path)
    args=parser.parse_args()
    report=json.loads((args.dist/'RELEASE_CONTENTS.json').read_text())
    run('sha256sum','-c','SHA256SUMS',cwd=args.dist)
    checks={'status':'FAIL','assets':[],'readme_svg_panels':svg_checks()}
    with tempfile.TemporaryDirectory(prefix='axiom-delivery-check-') as d:
        tmp=Path(d)
        for asset in report['assets']:
            path=args.dist/asset['file']
            if hashlib.sha256(path.read_bytes()).hexdigest()!=asset['sha256']:raise AssertionError('asset digest')
            root,names=extract(path,tmp/asset['kind'])
            run('bash',root/'VERIFY.sh')
            if asset['kind']=='linux-x86_64':
                for name in names:
                    parts=Path(name).parts[1:]
                    if 'presentation' in parts or '.github' in parts or 'maintainer' in parts:
                        raise AssertionError('repository tooling in app release')
            if asset['kind']=='complete':
                tracked={p.relative_to(R).as_posix() for p in tracked_project_files()}
                actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
                added={'RELEASE.json','VERIFY.sh','MANIFEST_SHA256.txt'}
                if actual!=tracked|added:raise AssertionError(('complete project omission',tracked-actual,actual-tracked-added))
                for name in tracked:
                    if (root/name).read_bytes()!=(R/name).read_bytes():raise AssertionError(('complete source changed',name))
                run('bash',root/'application/security/VERIFY_RELEASE.sh')
                checks['complete_project_files_byte_verified']=len(tracked)
                checks['complete_application_files_byte_verified']=len([p for p in tracked if p.startswith('application/')])
            else:
                launcher=root/'bin/axiom'
                run(launcher,'doctor');run(launcher,'demo');run(launcher,'selfhost')
                compile_exe=root/'bin/axiom-compile'
                packet=run(compile_exe,data=(root/'share/axiom/examples/Machine/entropy_seed_loop.anf').read_bytes())
                journal=run(root/'bin/axiom-machine',data=packet)
                next_seed=run(root/'bin/axiom-history','next',data=journal)
                run(root/'bin/axiom-machine',data=next_seed)
                run(launcher,'dense-inspect',root/'share/axiom/compiled/grover_2.qvb')
                run(launcher,'dense-run',root/'share/axiom/compiled/grover_2.qvb')
                run(launcher,'dense-compile',root/'share/axiom/examples/Dense/t_interference.ql',root/'share/axiom/compiled/compiled.release_seed.qseed',tmp/'new.qvb')
                run(launcher,'dense-run',tmp/'new.qvb')
                checks['relocatable_native_demo']='PASS'
                checks['native_seed_to_three_source_compilations']='PASS'
                checks['executed_next_seed']='PASS'
                checks['dense_compile_inspect_execute']='PASS'
            (root/'UNSIGNED_EXTRA').write_text('tamper\n')
            p=subprocess.run(['bash',str(root/'VERIFY.sh')],capture_output=True)
            if not p.returncode:raise AssertionError('unsigned extra accepted')
            (root/'UNSIGNED_EXTRA').unlink()
            with (root/'README.md').open('a') as f:f.write('\nmodified\n')
            p=subprocess.run(['bash',str(root/'VERIFY.sh')],capture_output=True)
            if not p.returncode:raise AssertionError('changed payload accepted')
            checks['assets'].append({'file':asset['file'],'extraction_verified':True,
                                     'presentation_included':asset['kind']=='complete',
                                     'tampering_refused':True})
        checks['git_export_project_files']=archive_check(tmp)
    if args.verified_application:
        outputs=json.loads((R/'application/evidence/source_only_rebuild.json').read_text())['outputs']
        for rel in outputs:
            if (R/'application'/rel).read_bytes()!=(args.verified_application/rel).read_bytes():raise AssertionError(('sealed output differs from verified rebuild',rel))
        checks['verified_rebuild_outputs_compared']=len(outputs)
    checks['status']='PASS'
    check_path=args.dist/'DELIVERY_CHECK.json'
    check_path.write_text(json.dumps(checks,indent=2)+'\n')
    checked=[args.dist/item['file'] for item in report['assets']]+[args.dist/'RELEASE_CONTENTS.json',check_path]
    (args.dist/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in checked))
    print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
