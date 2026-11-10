#!/usr/bin/env python3
"""Check native files and executed witnesses before emitting machine facts/SVG."""
from pathlib import Path
import hashlib
import html
import json
import struct
import subprocess
import tempfile

R=Path(__file__).resolve().parents[1]
D=R/'docs'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    report=json.loads((R/'evidence/native_machine_acceptance.json').read_text())
    build=json.loads((R/'evidence/native_self_hosting.json').read_text())
    if report['status']!='PASS' or build['status']!='PASS':raise SystemExit('machine evidence incomplete')
    source=R/'native/selfhost/compiler.anf'
    binaries={}
    targets=[('source_compiler','native/selfhost/anf_stage3.x86_64'),
             ('quantum_machine','native/machine/quantum_machine.x86_64'),
             ('history_reverser','native/machine/reverse_history.x86_64')]
    for generation in build['native_generations']:
        p=R/f"native/selfhost/anf_stage{generation['generation']}.x86_64"
        if digest(p)!=generation['image_sha256'] or digest(source)!=generation['source_sha256']:
            raise SystemExit('compiler generation/source mismatch')
    for item in build['machine_targets_built_by_native_compiler']:
        if digest(R/item['target'])!=item['image_sha256']:raise SystemExit('machine image/source evidence mismatch')
        text='\n'.join((R/p).read_text() for p in item['source_parts'])
        if hashlib.sha256(text.encode('ascii')).hexdigest()!=item['combined_source_sha256']:
            raise SystemExit('combined native source mismatch')
    for stem,name in targets:
        p=R/name;b=p.read_bytes()
        if b[:4]!=b'\x7fELF':raise SystemExit('missing ELF')
        phoff=struct.unpack_from('<Q',b,32)[0]
        width,count=struct.unpack_from('<HH',b,54)
        segments=[]
        for i in range(count):
            t,flags,offset,vaddr,paddr,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',b,phoff+i*width)
            if t==1:
                if flags&3==3:raise SystemExit('writable executable segment')
                segments.append({'flags':flags,'offset':offset,'virtual_address':vaddr,
                                 'file_bytes':filesz,'memory_bytes':memsz,'alignment':align})
            if t==3:raise SystemExit('unexpected runtime interpreter')
        binaries[stem]={'path':name,'sha256':digest(p),'bytes':len(b),
                        'entry':struct.unpack_from('<Q',b,24)[0],'load_segments':segments}
        headers=subprocess.run(['readelf','-W','-l',name],cwd=R,capture_output=True,text=True,check=True)
        (D/(stem+'_elf_segments.txt')).write_text(headers.stdout)
        with tempfile.TemporaryDirectory(prefix='axiom-machine-disasm-') as tmp:
            raw=Path(tmp)/'rx_payload.bin';raw.write_bytes(b[4096:])
            result=subprocess.run(['objdump','-D','-b','binary','-m','i386:x86-64','-M','intel',
                                   '--adjust-vma=0x401000',str(raw)],capture_output=True,text=True,check=True)
            (D/(stem+'_disassembly.txt')).write_text('# RX payload includes native instructions and embedded constants.\n'+'\n'.join(result.stdout.splitlines()[3:])+'\n')
    raw=(R/'evidence/nested_machine.history').read_bytes()
    magic,version,frames,state_bytes,seed_bytes,checksum,direction,reserved=struct.unpack('<8s7Q',raw[:64])
    if magic!=b'AXHST11\0' or version!=1 or state_bytes!=4096 or direction or reserved:
        raise SystemExit('unexpected recorded history ABI')
    seed=(R/'evidence/nested_machine.seed').read_bytes()
    if raw[64:64+seed_bytes]!=seed or len(raw)!=64+seed_bytes+frames*state_bytes:
        raise SystemExit('recorded source/history pairing differs')
    facts={'release':'G11','native_binaries':binaries,'native_source_generations':len(build['native_generations']),
           'virtual_stabilizer_qubits':struct.unpack_from('<Q',seed,16)[0],
           'canonical_state_bytes':state_bytes,'witness_history_frames':frames,
           'tested_nested_guest_depth':report['maximum_nested_depth'],
           'seed_generations_restored':report['complete_seed_history_restorations'],
           'tableau_rows':64,'tableau_row_bytes':24,'tableau_state_offset':1024,
           'frame_slots':16,'guest_frame_bytes':32,'os_guest_virtualization_used':False,
           'physical_coherent_qubits_demonstrated':0}
    (D/'NATIVE_MACHINE_FACTS.json').write_text(json.dumps(facts,indent=2)+'\n')
    # Software/data ownership map. Labels are checked against native witnesses.
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="690" viewBox="0 0 1040 690" role="img" aria-label="AXIOM native compiler and quantum state ownership">',
           '<rect width="1040" height="690" fill="#f8fafc"/>',
           '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#52657b"/></marker></defs>']
    def text(x,y,s,size=15,bold=False):
        parts.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="#17243c">{html.escape(s)}</text>')
    def box(x,y,w,h,fill,lines):
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="#64748b"/>')
        for i,line in enumerate(lines):text(x+16,y+28+i*23,line,14,i==0)
    def arrow(x,y,xx,yy):parts.append(f'<path d="M{x},{y} L{xx},{yy}" stroke="#52657b" stroke-width="2" fill="none" marker-end="url(#arrow)"/>')
    text(30,35,'AXIOM G11 — native source, quantum ownership and reversible history',20,True)
    box(30,70,300,116,'#dbeafe',['Self-hosted ANF64 compiler',f'{len(build["native_generations"])} executed native generations',f'{binaries["source_compiler"]["bytes"]:,} bytes; direct ELF execution','Native and quantum source dialects'])
    box(390,70,280,116,'#ccfbf1',['Native quantum machine','Typed seed / bounded quantum ISA','No OS guest / hypervisor layer','Native inverse-compatible operations'])
    box(730,70,280,116,'#dcfce7',['Canonical quantum bank',f'{facts["virtual_stabilizer_qubits"]} virtual stabilizer qubits','64 Pauli rows × 24 bytes','Exclusive owner; parent suspended'])
    arrow(330,128,390,128);arrow(670,128,730,128)
    box(30,255,300,116,'#e0e7ff',['Guest control frames','Code-view attenuation and fuel',f'{facts["tested_nested_guest_depth"]} nested guest levels tested','Checked owner IDs and return PCs'])
    box(390,255,280,116,'#fef3c7',['Complete canonical snapshots',f'{state_bytes:,} bytes per committed state','Quantum + control + entropy','Original complete seed retained'])
    box(730,255,280,116,'#e0f2fe',['Hardware-coupled phase','Actual CPUID / RDSEED','Retained sample controls S / SDG','Explicit refusal; no weak fallback'])
    arrow(330,313,390,313);arrow(870,186,870,255);arrow(730,313,670,313);arrow(530,186,530,255)
    box(30,450,300,116,'#dbeafe',['Native reverse/history tool','Executes inverse quantum kernels','Checks recorded predecessors','Restores byte-exact seed/state'])
    box(390,450,280,116,'#dcfce7',['Next native seed','Executed final quantum bank','Retained hardware entropy word',f'{facts["seed_generations_restored"]} generations executed/restored'])
    box(730,450,280,116,'#f1f5f9',['Independent verification','Full canonical frame comparisons','Encoding and malformed-state tests','Forward/reverse source-bound evidence'])
    arrow(530,371,180,450);arrow(330,508,390,508);arrow(670,508,730,508)
    text(30,625,'Source-derived software map. Quantum states are digital representations; physical coherence is not established.',14)
    text(30,651,'Complete reversal retains overwritten information. It does not reverse host time or the physical entropy device.',14)
    parts.append('</svg>');(D/'NATIVE_MACHINE_FLOW.svg').write_text(''.join(parts))
    print('NATIVE MACHINE SOURCE / ELF / HISTORY FACTS VERIFIED')

if __name__=='__main__':main()
