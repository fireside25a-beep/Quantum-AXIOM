#!/usr/bin/env python3
"""Regenerate source-data-derived architecture schematics as text-native SVG.
Numeric labels are parsed directly from the released ELF and verified ABI fact JSON.
"""
from pathlib import Path
import json,struct,html
HERE=Path(__file__).resolve().parent
F=json.loads((HERE/'SOURCE_EXTRACTED_MACHINE_FACTS.json').read_text())
ROOT=HERE.parent
seed=(ROOT/'native/seed/genesis.x86_64').read_bytes()
assert F['image_bytes']==len(seed)
# Validate semantic fields against physical ELF bytes before drawing.
assert struct.unpack_from('<Q',seed,24)[0]==0x401000
assert seed[0x2000:0x2008]==b'SEEDX86!'
assert struct.unpack_from('<Q',seed,0x2050)[0]==32
assert F['tableau_replicas']==3 and F['tableau_replica_bytes']==768
PALETTE={'bg':'#f8fafc','ink':'#162039','blue':'#dbeafe','teal':'#ccfbf1','amber':'#fef3c7','line':'#64748b','muted':'#475569','green':'#dcfce7'}
def rect(x,y,w,h,fill,radius=8):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{PALETTE["line"]}" stroke-width="1.5"/>'
def line(x1,y1,x2,y2):return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{PALETTE["line"]}" stroke-width="1.8" marker-end="url(#arrow)"/>'
def txt(x,y,s,size=15,weight='normal',anchor='start'):
 return f'<text x="{x}" y="{y}" font-family="DejaVu Sans,Arial,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{PALETTE["ink"]}">{html.escape(str(s))}</text>'
def svg(w,h,elements,title,path):
 head=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}"><title>{html.escape(title)}</title><defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{PALETTE["line"]}"/></marker></defs><rect width="100%" height="100%" fill="{PALETTE["bg"]}"/>'
 (HERE/path).write_text(head+''.join(elements)+'</svg>')
# ELF physical image
els=[txt(36,37,'Native ELF64 image — extracted offsets and kernel segment permissions',19,'bold')]
for y,fill,title,sub in [
(70,PALETTE['blue'],'0x0000–0x0FFF: ELF header / program headers','PT_LOAD header and metadata; RX mapping'),
(154,PALETTE['blue'],f'0x1000: native opcode region (entry 0x{F["ELF_entry"]:X})','Machine instruction stream, no bytecode VM'),
(238,PALETTE['teal'],'0x2000: resident logical header (128 bytes)','Epoch, ternary triplicate, tags, entropy, syndrome'),
(322,PALETTE['green'],'0x2080–0x237F: Pauli tableau replica A (768 bytes)','64 rows × 12 bytes: X, Z, phase'),
(406,PALETTE['green'],'0x2380–0x267F: Pauli tableau replica B (768 bytes)','Independent correction lane'),
(490,PALETTE['green'],'0x2680–0x297F: Pauli tableau replica C (768 bytes)','Independent correction lane'),
]:
 els.append(rect(36,y,790,70,fill));els.extend([txt(55,y+28,title,15,'bold'),txt(55,y+52,sub,13)])
els.append(txt(36,594,'Actual image 10,624 bytes • RX (flags 5) and RW (flags 6) PT_LOAD segments',13))
svg(862,620,els,'ELF64 actual native image map','NATIVE_ELF_MEMORY_MAP.svg')
# Live execution routes
els=[txt(32,35,'Two executed compilation/execution paths — distinct semantics',19,'bold')]
route=[('Clifford32 .qcl source',PALETTE['blue']),('Offline static lowering',PALETTE['amber']),('Native ELF64 direct gate code',PALETTE['teal']),('CPU 64-row Pauli conjugation',PALETTE['green']),('ECC, RDSEED, BPF seccomp, emit ELF',PALETTE['blue'])]
for j,(s,c) in enumerate(route):
 y=68+j*87;els.append(rect(35,y,380,60,c));els.append(txt(225,y+35,s,14,'bold','middle'))
 if j<4:els.append(line(225,y+60,225,y+86))
route=[('Dense .ql source',PALETTE['blue']),('x86 assembler-native compiler',PALETTE['amber']),('48+16N-byte QVU1 canonical packet',PALETTE['teal']),('x86 assembler-native Q30 executor',PALETTE['green']),('BPF seccomp, trace/replay, getrandom',PALETTE['blue'])]
for j,(s,c) in enumerate(route):
 y=68+j*87;els.append(rect(465,y,380,60,c));els.append(txt(655,y+35,s,14,'bold','middle'))
 if j<4:els.append(line(655,y+60,655,y+86))
els.append(txt(35,537,'Both paths execute on x86 CPU. No physical coherent qubit substrate is demonstrated.',13))
svg(880,560,els,'Executed native quantum software paths','COMPILER_RUNTIME_DATAFLOW.svg')
# Packet memory layout
els=[txt(36,38,'Dense program ABI — exact little-endian packet layout',19,'bold')]
fields=[('0–3','magic QVU1'),('4–7','version u32 = 1'),('8–11','qubits u32'),('12–15','classical bits u32'),('16–19','record count u32'),('20–23','flags u32 = 1'),('24–31','seed tag u64'),('32–39','FNV64 records checksum'),('40–47','reserved u64 = 0')]
for i,(off,name) in enumerate(fields):
 y=62+i*52;els.append(rect(45,y,790,44,PALETTE['teal'] if i%2==0 else PALETTE['blue']));els.append(txt(65,y+27,off,13,'bold'));els.append(txt(235,y+27,name,14))
y=62+len(fields)*52+14
els.append(rect(45,y,790,90,PALETTE['amber']));els.append(txt(65,y+31,'48 + 16×i',14,'bold'));els.append(txt(235,y+26,'Record: op:u8, q0:u8, q1:u8, c0:u8, param:i32',12));els.append(txt(235,y+48,'flags:u32=0, reserved:u32=0; exactly N records',12));els.append(txt(235,y+70,'Invalid length, checksum or operands cause refusal',12))
svg(875,680,els,'Actual native dense packet ABI','DENSE_PACKET_LAYOUT.svg')
# Fault correction / security
els=[txt(36,40,'Native memory repair — physical three-lane replication in RW state',18,'bold')]
for j,name in enumerate(('Replica A — 768 bytes','Replica B — 768 bytes','Replica C — 768 bytes')):
 x=40+j*300;els.append(rect(x,100,260,80,PALETTE['blue']));els.append(txt(x+130,130,name,14,'bold','middle'));els.append(txt(x+130,156,'64 rows × (X,Z,phase)',12,anchor='middle'));els.append(line(x+130,180,490,251))
els.append(rect(310,254,360,75,PALETTE['teal']));els.append(txt(490,286,'Bitwise majority, repair all replicas',14,'bold','middle'));els.append(txt(490,310,'192 × u32 per replica',12,anchor='middle'));els.append(line(490,329,490,385))
els.append(rect(310,387,360,72,PALETTE['green']));els.append(txt(490,415,'Verify FNV32 + complement',14,'bold','middle'));els.append(txt(490,440,'reject uncorrectable state',12,anchor='middle'));els.append(line(490,459,490,504))
els.append(rect(310,506,360,72,PALETTE['amber']));els.append(txt(490,538,'Native H / S / CX update',14,'bold','middle'));els.append(txt(490,561,'reduplicate and commit',12,anchor='middle'))
els.append(txt(42,624,'Boundary: accidental one-lane fault model, not malicious or physical quantum error correction.',13))
svg(960,655,els,'Three-lane native error correction','THREE_LANE_ECC_FLOW.svg')
print('SVG generated from facts and ELF; four diagrams')
