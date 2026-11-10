#!/usr/bin/env python3
"""Build deterministic app-only and full-project ZIP assets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile

R=Path(__file__).resolve().parents[1]
A=R/'application'
STAMP=(2026,11,10,0,0,0)

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(*args,**kwargs):return subprocess.run(list(map(str,args)),check=True,capture_output=True,**kwargs)
def files(root):return sorted(p for p in root.rglob('*') if p.is_file())
def copy(src,dst):
    if src.is_symlink() or not src.is_file():raise ValueError('invalid source '+str(src))
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)

def inventory(root,key):
    copy(R/'maintainer/VERIFY_PACKAGE.sh',root/'VERIFY.sh')
    (root/'VERIFY.sh').chmod(0o755)
    if key:
        command('openssl','pkey','-in',key,'-pubout','-out',root/'package_public_ed25519.pem')
    lines=[]
    for p in files(root):
        rel=p.relative_to(root).as_posix()
        if rel in ('MANIFEST_SHA256.txt','MANIFEST.ed25519.sig'):continue
        if '\n' in rel or '\\' in rel:raise ValueError('unsafe package path')
        lines.append(digest(p)+'  ./'+rel+'\n')
    (root/'MANIFEST_SHA256.txt').write_text(''.join(lines))
    if key:command('openssl','pkeyutl','-sign','-inkey',key,'-in',root/'MANIFEST_SHA256.txt','-rawin','-out',root/'MANIFEST.ed25519.sig')
    command('bash',root/'VERIFY.sh')

def zip_tree(root,out):
    items=files(root)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for p in items:
            if p.is_symlink():raise ValueError('package symlink')
            info=zipfile.ZipInfo(root.name+'/'+p.relative_to(root).as_posix(),STAMP)
            info.create_system=3
            info.external_attr=(stat.S_IFREG|(0o755 if os.access(p,os.X_OK) else 0o644))<<16
            archive.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    return {'file':out.name,'sha256':digest(out),'zip_bytes':out.stat().st_size,
            'files':len(items),'uncompressed_bytes':sum(p.stat().st_size for p in items)}

def metadata(version,kind,key):
    p=subprocess.run(['git','rev-parse','HEAD'],cwd=R,capture_output=True,text=True)
    github_sha=os.environ.get('GITHUB_SHA','')
    if github_sha and not re.fullmatch(r'[0-9a-f]{40}',github_sha):
        raise ValueError('invalid GITHUB_SHA')
    return {'version':version,'engine':'G11','kind':kind,'platform':'Linux x86-64',
            'minimum_glibc_for_shipped_dense_tools':'2.41',
            'requires_rdseed':'qentropy and legacy direct images only',
            'source_commit':github_sha or (p.stdout.strip() if p.returncode==0 else 'uncommitted-local-preparation'),
            'engine_source_inventory_sha256':digest(A/'ai/SOURCE_MAP.json'),
            'engine_verification_summary_sha256':digest(A/'evidence/VERIFICATION_SUMMARY.json'),
            'outer_package_signed':bool(key),'publisher_identity_authenticated':False,
            'physical_coherent_qubits_demonstrated':False,
            'presentation_included':kind=='complete'}

def tracked_project_files():
    """Use the checked-in release inventory even if CI's Git metadata is absent."""
    names=(R/'maintainer/RELEASE_FILES.txt').read_text().splitlines()
    if not names or names!=sorted(set(names)) or 'application/security/VERIFY_RELEASE.sh' not in names:
        raise ValueError('invalid release file inventory')
    paths=[]
    for name in names:
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts or '\\' in name or not name:
            raise ValueError('unsafe release file path')
        path=R/rel
        if not path.is_file() or path.is_symlink():raise ValueError('missing release file '+name)
        paths.append(path)
    return paths

def runtime(root,version):
    targets={
      'bin/axiom':'@maintainer/axiom.sh',
      'bin/axiom-compile':'native/selfhost/anf_stage3.x86_64',
      'bin/axiom-machine':'native/machine/quantum_machine.x86_64',
      'bin/axiom-history':'native/machine/reverse_history.x86_64',
      'bin/axiom-seed':'native/seed/native_seed_emitter.x86_64',
      'bin/axiom-dense-compile':'native/dense/bin/native_q_compile',
      'bin/axiom-dense-run':'native/dense/bin/native_q_execute',
      'bin/axiom-dense-inspect':'native/dense/bin/native_q_inspect',
      'bin/axiom-dense-seed':'native/dense/bin/native_q_seed',
      'lib/libnative_quantum_abi.a':'native/dense/sdk/libnative_quantum_abi.a',
      'lib/libnative_quantum_abi.so':'native/dense/sdk/libnative_quantum_abi.so',
      'include/axiom_machine.h':'native/machine/axiom_machine.h',
      'include/axiom_qvu.h':'native/dense/sdk/axiom_qvu.h',
      'share/axiom/bootstrap/compiler.anf':'native/selfhost/compiler.anf',
      'share/axiom/bootstrap/compiler_seed.bits':'native/selfhost/compiler_seed.bits',
      'LICENSE':'@LICENSE','NOTICE':'@NOTICE',
      'LICENSING.md':'@LICENSING.md'}
    for dst,src in targets.items():copy(R/src[1:] if src.startswith('@') else A/src,root/dst)
    for p in (root/'bin').iterdir():p.chmod(0o755)
    (root/'share/axiom/VERSION').write_text(version+'\n')
    for p in files(A/'examples'):copy(p,root/'share/axiom/examples'/p.relative_to(A/'examples'))
    for p in files(A/'native/dense'):
        if p.suffix in ('.qvb','.qseed'):copy(p,root/'share/axiom/compiled'/p.relative_to(A/'native/dense'))
    for p in (A/'native/clifford').glob('*.x86_64'):copy(p,root/'share/axiom/clifford'/p.name)
    for name in ('genesis.x86_64','closed_routine_seed.x86_64'):copy(A/'native/seed'/name,root/'share/axiom/clifford'/name)
    for name in ('ANF64.md','MACHINE_ABI.md','LANGUAGE.md','DENSE_PACKET_ABI.md','DEPENDENCIES.md'):
        copy(A/'docs'/name,root/'share/doc/axiom'/name)
    copy(R/'docs/GETTING_STARTED.md',root/'share/doc/axiom/GETTING_STARTED.md')
    (root/'README.md').write_text('# Quantum AXIOM '+version+'\n\nLinux x86-64 command-line application.\n\n```sh\nbash VERIFY.sh\n./bin/axiom doctor\n./bin/axiom demo\n./bin/axiom selfhost\n```\n\nOperating guide: `share/doc/axiom/GETTING_STARTED.md`. Native operations need no Python or system assembler. Shipped dense tools require glibc >= 2.41. Entropy-dependent examples require actual RDSEED. These are digital stabilizer/amplitude representations; physical coherent qubits are not demonstrated. Complete reversal requires the retained journal. See LICENSE for the existing rights policy.\n')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=R/'dist')
    parser.add_argument('--signing-key',type=Path)
    args=parser.parse_args()
    version=(R/'VERSION').read_text().strip()
    if not re.fullmatch(r'g[0-9]+(?:\.[0-9]+)*',version):raise SystemExit('invalid version')
    key=args.signing_key.resolve() if args.signing_key else None
    if key and (key==R or R in key.parents):raise SystemExit('private key must be outside repository')
    command('bash',A/'security/VERIFY_RELEASE.sh')
    for p in A.rglob('*'):
        if p.is_symlink() or p.name=='__pycache__' or p.suffix in ('.o','.pyc'):
            raise SystemExit('unsealed application leftover: '+str(p))
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    results=[]
    with tempfile.TemporaryDirectory(prefix='axiom-package-') as tmp:
        for kind in ('linux-x86_64','complete'):
            root=Path(tmp)/('axiom-'+version+'-'+kind);root.mkdir()
            if kind=='linux-x86_64':runtime(root,version)
            else:
                for source in tracked_project_files():
                    copy(source,root/source.relative_to(R))
            (root/'RELEASE.json').write_text(json.dumps(metadata(version,kind,key),indent=2)+'\n')
            inventory(root,key)
            result=zip_tree(root,out/(root.name+'.zip'));result['kind']=kind
            results.append(result)
    report={'version':version,'engine':'G11','assets':results,
            'presentation_in_app_asset':False,'presentation_in_complete_asset':True}
    report_path=out/'RELEASE_CONTENTS.json';report_path.write_text(json.dumps(report,indent=2)+'\n')
    checked=[out/item['file'] for item in results]+[report_path]
    (out/'SHA256SUMS').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in checked))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
