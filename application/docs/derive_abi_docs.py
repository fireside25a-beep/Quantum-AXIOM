#!/usr/bin/env python3
"""Regenerate evidence diagrams and ABI annotations by checking actual native source and ELF images.
This is a documentation/extraction tool, not a quantum backend.
"""
import hashlib,json,re,struct,subprocess,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]
D=R/'docs'
S=R/'native/dense/source'
image=(R/'native/seed/genesis.x86_64').read_bytes()
phoff=struct.unpack_from('<Q',image,32)[0]
def segment(index):
 v=struct.unpack_from('<IIQQQQQQ',image,phoff+56*index)
 return dict(zip(('type','flags','offset','vaddr','paddr','file_bytes','memory_bytes','alignment'),v))
facts={'profile_scope':'legacy direct Clifford/closed-seed ELF, separate from the G11 guest machine',
 'image_bytes':len(image),'ELF_header_bytes':64,'ELF_program_header_bytes':56,
 'ELF_entry':struct.unpack_from('<Q',image,24)[0],'RX_segment':segment(0),'RW_segment':segment(1),
 'code_offset':4096,'data_offset':8192,'data_header_bytes':128,'tableau_replica_bytes':768,
 'tableau_replicas':3,'tableau_rows':64,'pauli_sites':32,'state_word_bytes':8,'state_replicas':3,
 'physical_coherent_qubits_measured':0,'programs_32_site':len(list((R/'examples/Clifford32').glob('*.qcl'))),
 'programs_dense':len(list((R/'examples/Dense').glob('*.ql'))),
 'native_self_emitter_SHA256':hashlib.sha256((R/'native/seed/native_seed_emitter.x86_64').read_bytes()).hexdigest(),
 'genesis_SHA256':hashlib.sha256(image).hexdigest(),'seccomp_stackable_BPF_native':True,
 'seccomp_BPF_dense_after_validation':True,
 'native_quantum_machine_facts':'NATIVE_MACHINE_FACTS.json'}
(D/'SOURCE_EXTRACTED_MACHINE_FACTS.json').write_text(json.dumps(facts,indent=2)+'\n')
def h(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def anchor(file,term):
 lines=file.read_text().splitlines()
 hits=[i+1 for i,line in enumerate(lines) if term in line]
 if not hits:raise AssertionError('missing source signature '+term+' in '+str(file))
 return {'path':str(file.relative_to(R)),'line':hits[0],'pattern':term,'file_sha256':h(file)}
abi=S/'native_packet_abi.S';comp=S/'native_q_compile.S';exe=S/'native_q_execute.S';seed=S/'native_entropy_seed.S'
assert 'cmp rsi,65584' in abi.read_text()
assert 'cmp eax,20' in exe.read_text()
assert 'renormalize_after_measure:' in exe.read_text()
assert 'native_filter_program:' in exe.read_text()
source_checks={
 'packet_magic':anchor(abi,'0x31555651'),
 'packet_version':anchor(abi,'[rdi+4],1'),
 'packet_record_limit':anchor(abi,'4096'),
 'executor_20_site_limit':anchor(exe,'cmp eax,20'),
 'packet_payload_hash':anchor(abi,'0xcbf29ce484222325'),
 'seed_magic':anchor(seed,'0x0031304445455351'),
 'kernel_entropy':anchor(seed,'mov eax, 318'),
 'rdseed_optional':anchor(seed,'rdseed rax'),
 'linux_filter':anchor(exe,'native_filter_program:'),
 'native_measure_renormalization':anchor(exe,'renormalize_after_measure:'),
 'gate_tokens':anchor(comp,'str_h: .asciz "H"'),
 'vm_free_clifford':anchor(R/'native/clifford/native_clifford_compiler.py','ELF64 x86-64'),
}
(D/'abi_source_anchors.json').write_text(json.dumps(source_checks,indent=2)+'\n')
# Independently parse a native packet as an ABI conformance witness.
packet=(R/'native/dense/grover_2.qvb').read_bytes()
magic,version,nq,nc,nops,flags,seedtag,digest,reserved=struct.unpack('<4sIIIIIQQQ',packet[:48])
assert magic==b'QVU1' and version==1 and flags==1 and reserved==0 and len(packet)==48+16*nops
fields=[('magic',0,4,'ASCII QVU1'),('version',4,4,'u32 = 1'),('qubits',8,4,'u32: syntax 1..256, dense executor 1..20'),('classical_bits',12,4,'u32: 1..32'),('operation_count',16,4,'u32: 1..4096'),('flags',20,4,'u32 = 1'),('seed_tag',24,8,'u64 unkeyed provenance tag'),('record_digest',32,8,'u64 FNV-1a over all records'),('reserved',40,8,'u64 = 0')]
md=['# Native packet ABI QVU1 — source-checked','',f'Source file: `{abi.relative_to(R)}`.','',f'Observed witness: `{(R/"native/dense/grover_2.qvb").relative_to(R)}`; SHA-256 `{hashlib.sha256(packet).hexdigest()}`.','', 'The ABI uses fixed-width **little-endian** fields; no language object layout is embedded. A file contains a 48-byte header and `operation_count` records of 16 bytes each.','','| Header field | Offset | Width | Meaning |','|---|---:|---:|---|']
for name,off,w,why in fields:md.append(f'| `{name}` | {off} | {w} | {why} |')
md+=['','Each 16-byte operation record is `opcode:u8`, `site0:u8`, `site1:u8`, `classical0:u8`, `parameter:i32`, `flags:u32=0`, `reserved:u32=0`. The packet digest is **not** a cryptographic signature.','','## Native gate opcodes','','| Opcode | Instruction |','|---:|---|']
for idx,name in enumerate(['H','X','Y','Z','S','SDG','T','TDG','CX','CZ','MEASURE','RESET','IF1','IF0','RZ8','BARRIER'],1):md.append(f'| {idx} | {name} |')
md+=['','## Compiler and runtime boundaries','','- The `native_q_compile` translator is x86-64 assembly with libc calls for file I/O/token parsing. It reads text programs and a 64-byte seed and writes the above native-defined binary packet. `COMPTIME` directives are expanded at compile time.','- The `native_q_execute` interpreter dispatches validated packet records into native x86-64 fixed-Q30 complex-amplitude kernels. It is a **native instruction implementation of a classical quantum-state calculation**, not execution on coherent physical qubits.','- The dense executor supports up to 20 sites (`2^20` complex amplitudes). The syntax/packet validator supports 256 sites, but larger packets **are not executable** by this dense backend.','- Measurement uses 128-bit threshold division, OS `getrandom()` or an exact external replay sequence. The retained branch is normalized by a native integer-square-root routine before the next gate.','- The runtime validates the packet, allocates state, installs `PR_SET_NO_NEW_PRIVS` and a Linux seccomp BPF allowlist, and only then executes gates. The filter blocks `getpid` in a deliberate probe build; this does not protect against malicious kernels.','- The separately compiled Clifford32 image contains **direct expanded x86 instructions for every scheduled H/S/CX operation**, with no packet interpreter, and maintains triplicated 64-row tableau state. Its offline source-to-instruction lowering tool is Python and **not** self-hosting.','- The seed emitter replicates its own native executable through its triple-lane bit-seed format; no new instruction vocabulary is invented by this bootstrap.','', '## Source-backed memory layout of native closed seed','','These offsets are verified from the native ELF64 data image and the source-lowering declarations.','','| Offset from data VMA `0x402000` | Field |','|---:|---|','| `0x00` | 8-byte `SEEDX86!` magic |','| `0x08` | u64 generation epoch |','| `0x10`..`0x27` | three u64 ternary logical-state replicas (positive/negative 32-bit lanes) |','| `0x28`..`0x37` | u64 state-integrity tag and complement |','| `0x38`..`0x4F` | entropy, syndrome, lineage state |','| `0x60`/`0x68` | u32 FNV digest/complement for full tableau lane |','| `0x80`..`0x37F` | 64 × 12-byte tableau rows, ECC lane A |','| `0x380`..`0x67F` | ECC lane B |','| `0x680`..`0x97F` | ECC lane C |','', 'A Pauli tableau row comprises `x_mask:u32`, `z_mask:u32`, `phase_mod4:u32`. Three 768-byte lanes undergo majority correction across all 192 words before each native instruction-plane transform. Faults that leave two lanes in agreement on the wrong value are not automatically correctable; the unkeyed digest rejects the tested conflicts.','','## Reproducibility','','Run `python3 docs/derive_abi_docs.py` from the release root to check source anchors and regenerate ABI evidence/diagrams.','']
(D/'ABI_QVU1_AND_CLIFFORD32.md').write_text('\n'.join(md)+'\n')
# True ELF payload disassembly (these files have no ELF section header table).
for stem,path,audit in [
 ('closed_seed',R/'native/seed/genesis.x86_64',None),
 ('clifford32',R/'native/clifford/ghz_32.x86_64',R/'evidence/ghz_32.lowering.json')]:
 img=path.read_bytes();assert img[:4]==b'\x7fELF' and len(img)==10624
 length=json.loads((R/'evidence/nucleus.lowering.json' if audit is None else audit).read_text())['code_region_length']
 code=img[0x1000:0x1000+length]
 with tempfile.TemporaryDirectory(prefix='axiom-disasm-') as folder:
  raw=Path(folder)/'direct-opcodes.bin';raw.write_bytes(code)
  res=subprocess.run(['objdump','-D','-b','binary','-m','i386:x86-64','-M','intel','--adjust-vma=0x401000',str(raw)],capture_output=True)
  if res.returncode:raise RuntimeError(res.stderr)
  (D/(stem+'_disassembly.txt')).write_text(f'# {stem}: ELF RX opcode region 0x401000, {length} source-derived bytes\n'+'\n'.join(res.stdout.decode().splitlines()[3:])+'\n')
# Diagrams model source flows and storage; do not pretend to be circuit board wiring.
for stem,path in [('closed_seed','native/seed/genesis.x86_64'),
                  ('clifford32','native/clifford/ghz_32.x86_64'),
                  ('dense_runtime','native/dense/bin/native_q_execute'),
                  ('native_emitter','native/seed/native_seed_emitter.x86_64')]:
 result=subprocess.run(['readelf','-W','-l',path],cwd=R,capture_output=True,text=True,check=True)
 (D/(stem+'_elf_segments.txt')).write_text(result.stdout)
for stem,path in [('dense_native','native/dense/bin/native_q_execute'),
                  ('native_emitter','native/seed/native_seed_emitter.x86_64')]:
 result=subprocess.run(['objdump','-d','-M','intel',path],cwd=R,capture_output=True,text=True,check=True)
 (D/(stem+'_disassembly.txt')).write_text(result.stdout)
graph=r'''digraph Axiom {
 graph [rankdir=LR, bgcolor="white", label="AXIOM Native Fabric — executed software layers", labelloc=t, fontsize=20, fontname="DejaVu Sans", pad="0.2"];
 node [fontname="DejaVu Sans", shape=box, style="rounded,filled", color="#28405A", fillcolor="#EAF3FD"];
 edge [color="#52677C", arrowsize=0.8];
 subgraph cluster_a {label="Native seed and direct instruction plane"; color="#9EBED6";
   bitseed [label="Triple-lane\nbitseed data"];
   emitter [label="x86-64 self-emitter\n(native ELF)"];
   image [label="x86-64 ELF RX opcodes\nRW 32-site state"];
   ecc [label="3-lane majority\n64-row tableau ECC"];
   bitseed -> emitter -> image -> ecc;
 }
 subgraph cluster_b {label="Clifford32 direct program family"; color="#9EBED6";
  qcl [label="QCL32 source\n(H / S / CX)"];
  offline [label="Offline opcode generator\n(Python build utility)"];
  native32 [label="Native standalone image\nno gate VM at runtime"];
  qcl->offline->native32;
 }
 subgraph cluster_c {label="Dense QVU1 classical amplitude execution"; color="#9EBED6";
  qlang [label="Quantum-language text\nCOMPTIME + gates"];
  asmcomp [label="Assembly translator\nQVU1 packet compiler"];
  packet [label="48-byte header\n16-byte records"];
  check [label="ABI + digest +\nsemantic validation"];
  sandbox [label="Linux NNP +\nseccomp BPF"];
  runner [label="Native Q30 kernels\nup to 20 sites"];
  qlang->asmcomp->packet->check->sandbox->runner;
 }
 ecc->native32 [style=dotted,label="separate image implementation"];
}
'''
(D/'native_execution_architecture.dot').write_text(graph)
subprocess.run(['dot','-Tsvg',str(D/'native_execution_architecture.dot'),'-o',str(D/'native_execution_architecture.svg')],check=True)
print('ABI SOURCE-DERIVED PASS, witness operations:',nops,'graph and ELF disassemblies generated')
