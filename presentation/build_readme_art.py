#!/usr/bin/env python3
"""Render self-contained README SVGs from the current verified engine report."""
from html import escape
import json
from pathlib import Path

R=Path(__file__).resolve().parents[1]
D=R/'presentation'
summary=json.loads((R/'application/evidence/VERIFICATION_SUMMARY.json').read_text())
if summary['status']!='PASS':raise SystemExit('execution evidence is not passing')
C=summary['counts']
version=(R/'VERSION').read_text().strip()
FG='#edf4fb';MUTED='#a0b1c8';LINE='#2c3e56';TEAL='#67e7cd';GOLD='#ffc478'

def text(x,y,value,size=18,color=FG,weight=400,mono=False,spacing=None):
    font='DejaVu Sans Mono,monospace' if mono else 'DejaVu Sans,Arial,sans-serif'
    extra=f' letter-spacing="{spacing}"' if spacing is not None else ''
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="{font}" font-size="{size}" font-weight="{weight}"{extra}>{escape(str(value))}</text>'
def rect(x,y,w,h,fill='#101d2d',stroke=LINE,r=16):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>'
def line(x1,y1,x2,y2,color=LINE):return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" fill="none"/>'
def arrow(path,color=TEAL):return f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" marker-end="url(#arrow)"/>'
def svg(height,title,description,parts):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="{height}" viewBox="0 0 1280 {height}" role="img" aria-labelledby="title desc"><title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc><defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#101d2c"/><stop offset="1" stop-color="#080f1b"/></linearGradient><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10" fill="{TEAL}"/></marker></defs>'+rect(1,1,1278,height-2,'url(#bg)',LINE,22)+''.join(parts)+'</svg>\n'
def save(name,value):(D/name).write_text(value)

hero=[]
hero+=[text(48,49,'ALEXANDRU MORARU / NATIVE COMPUTING RESEARCH',14,MUTED,mono=True),
       rect(962,25,268,34,'#152c31','#2d605a',17),text(982,48,'ENGINE G11 / '+version,14,TEAL,mono=True),
       text(46,165,'QUANTUM AXIOM',58,FG,700,spacing=2),text(52,207,'NATIVE FABRIC',26,TEAL,600,spacing=7),
       text(50,267,'A compiler that compiles itself.',29,FG,600),
       text(50,302,'Native quantum guests. Complete recorded histories.',20,MUTED),
       line(50,337,1230,337),text(50,378,'ANF64  /  x86-64  /  EXCLUSIVE STATE OWNERSHIP',15,TEAL,mono=True),
       text(50,406,'Digital stabilizer computation. Physical coherent qubits are not demonstrated.',16,MUTED)]
hero+=[rect(927,91,303,213,'#0c1624','#314660',16),text(950,119,'CANONICAL PAULI BANK',14,MUTED,mono=True)]
for row in range(8):
    for col in range(8):
        fill=TEAL if (row*5+col*3)%11==0 else '#3a5574' if (row+col)%3==0 else '#1c2e44'
        hero.append(rect(951+31*col,138+17*row,23,10,fill,fill,2))
hero.append(text(950,290,'64 rows / 32 virtual qubits',13,MUTED,mono=True))
save('hero.svg',svg(440,'Quantum AXIOM','Self-hosted native compilation, bounded quantum guests and reversible recorded history.',hero))

parts=[text(36,45,'EXECUTED LOCALLY · SOURCE-LINKED EVIDENCE',15,TEAL,600,mono=True)]
metrics=[(C['native_compiler_generations'],'NATIVE GENERATIONS','Compiler source compiled by itself'),
         (C['maximum_native_guest_depth'],'GUEST LEVELS','Exclusive bank and bounded frames'),
         (C['native_seed_generation_restorations'],'RESTORED GENERATIONS','Complete retained seed histories'),
         (C['clean_rebuilt_outputs'],'EXACT REBUILD OUTPUTS','Fresh extraction, byte-for-byte')]
for i,(value,label,detail) in enumerate(metrics):
    x=36+i*310
    if i:parts.append(line(x-18,71,x-18,205))
    parts+=[text(x,136,value,66,FG,700),text(x,170,label,14,TEAL,600,mono=True),text(x,199,detail,14,MUTED)]
parts.append(text(36,235,f"{C['native_machine_quantum_programs']} native machine programs · {C['native_machine_frames_compared']} full canonical-state comparisons · {C['native_journal_roundtrips']} journal round trips",13,MUTED))
save('verification.svg',svg(264,'Current verification results','Three native compiler generations, sixteen guest levels, twelve seed generations restored and sixty-one exact rebuilt outputs.',parts))

parts=[text(36,43,'ONE CONNECTED EXECUTION PATH',15,TEAL,600,mono=True),
       text(36,74,'Source → native compiler → machine → recorded state',27,FG,600)]
nodes=[(36,111,'01 / BOOTSTRAP INPUTS','ANF64 compiler source','Encoded seed + independent constructor'),
       (458,111,'02 / NATIVE COMPILER','Parses and emits fresh code','Three actual self-compilation generations'),
       (880,111,'03 / MACHINE KERNELS','Quantum VM + history ELFs','Freestanding native x86-64 executables'),
       (36,334,'04 / QUANTUM PROGRAM','Admitted typed seed','Initial bank + bounded instruction records'),
       (458,334,'05 / EXECUTION + JOURNAL','One owned quantum bank','Canonical control, entropy and state'),
       (880,334,'06 / INVERSE + NEXT SEED','Checks actual inverse gates','Restore history/seed; emit next seed')]
for x,y,title,a,b in nodes:
    parts+=[rect(x,y,364,143),text(x+20,y+31,title,13,TEAL,600,mono=True),
            text(x+20,y+70,a,20,FG,600),text(x+20,y+105,b,14,MUTED)]
parts+=[arrow('M400,182 L458,182'),arrow('M822,182 L880,182'),
        arrow('M520,254 L520,288 L218,288 L218,334'),
        arrow('M1062,254 L1062,303 L640,303 L640,334'),
        arrow('M400,405 L458,405'),arrow('M822,405 L880,405'),
        text(36,520,'16 guest levels  ·  1,024 fuel cap  ·  4,096-byte canonical states  ·  no KVM',16,TEAL,mono=True),
        text(36,552,'Complete reversal retains overwritten information; the physical host and entropy device are not reversed.',15,MUTED)]
save('architecture.svg',svg(582,'Native compiler and quantum machine architecture','Native source compiles to machine kernels and typed seeds. Machine execution creates canonical histories that native inverse and next-seed tools consume.',parts))

parts=[]
for x,label,title,desc,sub,color in [
    (28,'01 / RUN','THE APP','Executables · SDK · examples · operating guide','No repository artwork or CI files',TEAL),
    (654,'02 / REPRODUCE','THE COMPLETE ENGINE','Editable source · tests · raw journals · provenance','All required application files retained',GOLD)]:
    parts+=[rect(x,26,598,195,'#101e2f'),text(x+24,62,label,14,color,600,mono=True),
            text(x+24,110,title,28,FG,700),text(x+24,150,desc,16,MUTED),text(x+24,185,sub,14,color)]
save('downloads.svg',svg(248,'Application and complete downloads','Choose app executables and operating files, or the complete editable engine with tests and evidence. Both exclude repository presentation.',parts))
print('README SVGs generated from current G11 evidence: 4 panels')
