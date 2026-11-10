.intel_syntax noprefix
# Native QVU1 dense quantum state executor: fixed Q30 complex integer amplitudes.
# All quantum arithmetic in x86-64 machine instructions; libc is I/O only.
.section .rodata
rmode: .asciz "rb"
usage: .asciz "usage: qvue PROGRAM.qvb [REPLAY_ENTROPY.u32le] [--trace]"
str_trace: .asciz "--trace"
fmt_step: .asciz "QVU_STEP step=%u op=%u q0=%u q1=%u c0=%u hash=%016lx classical=%u\n"
fmt_fail: .asciz "QVU_REFUSED reason=%s\n"
invalid: .asciz "invalid packet, unsupported operation or state arithmetic"
failio: .asciz "file, memory or entropy acquisition failed"
fmt_ok: .asciz "QVU_FINAL qubits=%u cbits=%u operations=%u classical=%u norm=%lu seedtag=%016lx\n"
fmt_meas: .asciz "QVU_MEASURE step=%u qubit=%u cbit=%u draw=%u outcome=%u source=%s\n"
fmt_amp: .asciz "QVU_AMP index=%u re=%ld im=%ld\n"
source_live: .asciz "getrandom"
source_replay: .asciz "replay"

# Kernel-enforced syscall allowlist; after packet validation and state allocation.
# This BPF checks arch and excludes x32 syscall space before testing syscall IDs.
# Linux seccomp_data offsets: nr=0, arch=4.
.macro ALLOWED nr
 .short 0x15
 .byte 0,1
 .long \nr
 .short 0x06
 .byte 0,0
 .long 0x7fff0000
.endm
.balign 8
native_bpf:
 .short 0x20; .byte 0,0; .long 4
 .short 0x15; .byte 1,0; .long 0xc000003e
 .short 0x06; .byte 0,0; .long 0x80000000
 .short 0x20; .byte 0,0; .long 0
 .short 0x35; .byte 0,1; .long 0x40000000
 .short 0x06; .byte 0,0; .long 0x80000000
 ALLOWED 0
 ALLOWED 1
 ALLOWED 3
 ALLOWED 5
 ALLOWED 8
 ALLOWED 9
 ALLOWED 10
 ALLOWED 11
 ALLOWED 12
 ALLOWED 13
 ALLOWED 14
 ALLOWED 16
 ALLOWED 17
 ALLOWED 21
 ALLOWED 60
 ALLOWED 89
 ALLOWED 158
 ALLOWED 202
 ALLOWED 218
 ALLOWED 228
 ALLOWED 231
 ALLOWED 262
 ALLOWED 273
 ALLOWED 302
 ALLOWED 318
 ALLOWED 332
 ALLOWED 334
 .short 0x06; .byte 0,0; .long 0x00050001
native_bpf_end:
.balign 8
native_filter_program:
 .short (native_bpf_end-native_bpf)/8
 .zero 6
 .quad native_bpf
.section .bss
.align 16
header: .skip 48
packet: .skip 65536
state_ptr: .skip 8
input_file: .skip 8
replay_file: .skip 8
nqubits: .skip 4
nclass: .skip 4
count: .skip 4
dim: .skip 4
classical: .skip 4
step: .skip 4
op: .skip 4
q0: .skip 4
q1: .skip 4
c0: .skip 4
parm: .skip 4
mask0: .skip 8
mask1: .skip 8
i_idx: .skip 8
pa: .skip 8
pb: .skip 8
vra: .skip 8
via: .skip 8
vrb: .skip 8
vib: .skip 8
pzero: .skip 8
pone: .skip 8
ptotal: .skip 8
outcome: .skip 4
draw: .skip 4
reset_mode: .skip 4
source_kind: .skip 8
trace_enabled: .skip 4
src_op: .skip 4
argfile: .skip 8
main_stack: .skip 8
.section .text
.global main
.extern fopen
.extern fclose
.extern fgetc
.extern fread
.extern fseek
.extern ftell
.extern rewind
.extern malloc
.extern calloc
.extern free
.extern printf
.extern puts
.extern fprintf
.extern strcmp
.extern stderr
.extern ferror
.extern fflush
# mul_q30 input rax, output rax. Signed 128-bit intermediate.
mul_q30:
 mov ecx,759250125
 imul rcx
 shrd rax,rdx,30
 ret
# load pair values at index i, j via global `pa` and `pb` pointers.
load_pair:
 mov rdx,[rip+state_ptr]
 mov rax,[rip+i_idx]
 shl rax,4
 lea rbx,[rdx+rax]
 mov [rip+pa],rbx
 mov r8,[rbx]
 mov r9,[rbx+8]
 mov rax,[rip+i_idx]
 or rax,[rip+mask0]
 shl rax,4
 lea rbx,[rdx+rax]
 mov [rip+pb],rbx
 mov r10,[rbx]
 mov r11,[rbx+8]
 ret
# apply_single uses `op` and q0; branch to executable machine instruction loops.
apply_single:
 mov ecx,[rip+q0]
 mov eax,1
 shl rax,cl
 mov [rip+mask0],rax
 mov qword ptr [rip+i_idx],0
.single_loop:
 mov rsi,[rip+i_idx]
 cmp esi,[rip+dim]
 jae .single_done
 mov eax,[rip+op]
 cmp eax,1
 je .h
 cmp eax,2
 je .x
 cmp eax,3
 je .y
 cmp eax,4
 je .z
 cmp eax,5
 je .s
 cmp eax,6
 je .sdg
 cmp eax,7
 je .t
 cmp eax,8
 je .tdg
 jmp refuse_invalid
.h:
 test rsi,[rip+mask0]
 jnz .single_next
 call load_pair
 mov rax,r8
 add rax,r10
 call mul_q30
 mov rbx,[rip+pa]
 mov [rbx],rax
 mov rax,r9
 add rax,r11
 call mul_q30
 mov [rbx+8],rax
 mov rax,r8
 sub rax,r10
 call mul_q30
 mov rbx,[rip+pb]
 mov [rbx],rax
 mov rax,r9
 sub rax,r11
 call mul_q30
 mov [rbx+8],rax
 jmp .single_next
.x:
 test rsi,[rip+mask0]
 jnz .single_next
 call load_pair
 mov rbx,[rip+pa]
 mov [rbx],r10
 mov [rbx+8],r11
 mov rbx,[rip+pb]
 mov [rbx],r8
 mov [rbx+8],r9
 jmp .single_next
.y:
 test rsi,[rip+mask0]
 jnz .single_next
 call load_pair
 mov rbx,[rip+pa]
 mov [rbx],r11
 mov rax,r10
 neg rax
 mov [rbx+8],rax
 mov rbx,[rip+pb]
 mov rax,r9
 neg rax
 mov [rbx],rax
 mov [rbx+8],r8
 jmp .single_next
.z:
 test rsi,[rip+mask0]
 jz .single_next
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 neg qword ptr [rbx]
 neg qword ptr [rbx+8]
 jmp .single_next
.s:
 test rsi,[rip+mask0]
 jz .single_next
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 mov rax,[rbx]
 mov rdx,[rbx+8]
 neg rdx
 mov [rbx],rdx
 mov [rbx+8],rax
 jmp .single_next
.sdg:
 test rsi,[rip+mask0]
 jz .single_next
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 mov rax,[rbx]
 mov rdx,[rbx+8]
 mov [rbx],rdx
 neg rax
 mov [rbx+8],rax
 jmp .single_next
.t:
 test rsi,[rip+mask0]
 jz .single_next
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 mov r8,[rbx]
 mov r9,[rbx+8]
 mov rax,r8
 sub rax,r9
 call mul_q30
 mov [rbx],rax
 mov rax,r8
 add rax,r9
 call mul_q30
 mov [rbx+8],rax
 jmp .single_next
.tdg:
 test rsi,[rip+mask0]
 jz .single_next
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 mov r8,[rbx]
 mov r9,[rbx+8]
 mov rax,r8
 add rax,r9
 call mul_q30
 mov [rbx],rax
 mov rax,r9
 sub rax,r8
 call mul_q30
 mov [rbx+8],rax
.single_next:
 inc qword ptr [rip+i_idx]
 jmp .single_loop
.single_done:
 ret
# two-qubit operations. CX swaps amplitudes; CZ changes sign on both 1.
apply_double:
 mov ecx,[rip+q0]
 mov eax,1
 shl rax,cl
 mov [rip+mask1],rax
 mov ecx,[rip+q1]
 mov eax,1
 shl rax,cl
 mov [rip+mask0],rax
 mov qword ptr [rip+i_idx],0
.double_loop:
 mov rsi,[rip+i_idx]
 cmp esi,[rip+dim]
 jae .double_done
 test rsi,[rip+mask1]
 jz .double_next
 mov eax,[rip+op]
 cmp eax,10
 je .cz
 test rsi,[rip+mask0]
 jnz .double_next
 call load_pair
 mov rbx,[rip+pa]
 mov [rbx],r10
 mov [rbx+8],r11
 mov rbx,[rip+pb]
 mov [rbx],r8
 mov [rbx+8],r9
 jmp .double_next
.cz:
 test rsi,[rip+mask0]
 jz .double_next
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 neg qword ptr [rbx]
 neg qword ptr [rbx+8]
.double_next:
 inc qword ptr [rip+i_idx]
 jmp .double_loop
.double_done:
 ret
# Renormalize the retained Born branch after projective measurement.
# Fixed-point integer only: selected norm uses Q60; integer sqrt is computed
# with bounded downward Newton iterations; gain=floor(2^60/isqrt(norm)).
# Does not perform any system calls or allocate dynamic memory.
renormalize_after_measure:
 mov r8,[rip+pzero]
 cmp dword ptr [rip+outcome],0
 je .select_norm
 mov r8,[rip+pone]
.select_norm:
 test r8,r8
 jz refuse_invalid
 bsr rcx,r8
 shr ecx,1
 inc ecx
 mov r9,1
 shl r9,cl
.isqrt_loop:
 mov rax,r8
 xor edx,edx
 div r9
 add rax,r9
 jc refuse_invalid
 shr rax,1
 cmp rax,r9
 jae .root_found
 mov r9,rax
 jmp .isqrt_loop
.root_found:
 # R10 = floor(2^60 / isqrt(retained squared amplitude norm)).
 movabs rax,0x1000000000000000
 xor edx,edx
 div r9
 mov r10,rax
 xor r11d,r11d
.renorm_loop:
 cmp r11d,[rip+dim]
 jae .renorm_done
 mov rax,r11
 shl rax,4
 mov rdx,[rip+state_ptr]
 lea r8,[rdx+rax]
 mov rax,[r8]
 imul r10
 shrd rax,rdx,30
 mov [r8],rax
 mov rax,[r8+8]
 imul r10
 shrd rax,rdx,30
 mov [r8+8],rax
 inc r11d
 jmp .renorm_loop
.renorm_done:
 ret
# measure q0 with getrandom(4) or explicit replay file (no weak fallback).
# returns outcome in global; on reset_mode does NOT write classical bit.
measure:
 push rbp
 mov rbp,rsp
 push rbx
 sub rsp,8
 mov qword ptr [rip+pzero],0
 mov qword ptr [rip+pone],0
 mov ecx,[rip+q0]
 mov eax,1
 shl rax,cl
 mov [rip+mask0],rax
 mov qword ptr [rip+i_idx],0
.measure_norm:
 mov rsi,[rip+i_idx]
 cmp esi,[rip+dim]
 jae .norm_done
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 mov rax,[rbx]
 imul rax
 mov r8,rax
 mov rax,[rbx+8]
 imul rax
 add rax,r8
 jc refuse_invalid
 test rsi,[rip+mask0]
 jnz .norm_one
 add [rip+pzero],rax
 jc refuse_invalid
 jmp .norm_next
.norm_one:
 add [rip+pone],rax
 jc refuse_invalid
.norm_next:
 inc qword ptr [rip+i_idx]
 jmp .measure_norm
.norm_done:
 mov r15,[rip+pzero]
 add r15,[rip+pone]
 jc refuse_invalid
 test r15,r15
 jz refuse_invalid
 mov [rip+ptotal],r15
 mov rax,[rip+replay_file]
 test rax,rax
 jz .live
 lea rdi,[rip+draw]
 mov esi,1
 mov edx,4
 mov rcx,rax
 call fread@PLT
 cmp eax,4
 jne refuse_io
 lea rax,[rip+source_replay]
 mov [rip+source_kind],rax
 jmp .have_draw
.live:
 mov eax,318
 lea rdi,[rip+draw]
 mov esi,4
 xor edx,edx
 syscall
 cmp eax,4
 jne refuse_io
 lea rax,[rip+source_live]
 mov [rip+source_kind],rax
.have_draw:
 # threshold = floor((P1 << 32)/(P0+P1)); 128-bit dividend.
 mov rax,[rip+pone]
 mov rdx,rax
 shr rdx,32
 shl rax,32
 div r15
 mov edx,[rip+draw]
 mov dword ptr [rip+outcome],0
 cmp rdx,rax
 jae .collapse
 mov dword ptr [rip+outcome],1
.collapse:
 mov qword ptr [rip+i_idx],0
.collapse_loop:
 mov rsi,[rip+i_idx]
 cmp esi,[rip+dim]
 jae .collapse_done
 mov rax,rsi
 and rax,[rip+mask0]
 setnz al
 movzx eax,al
 cmp eax,[rip+outcome]
 je .collapse_next
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 mov qword ptr [rbx],0
 mov qword ptr [rbx+8],0
.collapse_next:
 inc qword ptr [rip+i_idx]
 jmp .collapse_loop
.collapse_done:
 call renormalize_after_measure
 # preserve original cbit value when RESET is an internal measurement.
 cmp dword ptr [rip+reset_mode],0
 jne .log_measure
 mov ecx,[rip+c0]
 mov eax,1
 shl eax,cl
 not eax
 and [rip+classical],eax
 cmp dword ptr [rip+outcome],0
 je .log_measure
 not eax
 or [rip+classical],eax
.log_measure:
 lea rdi,[rip+fmt_meas]
 mov esi,[rip+step]
 mov edx,[rip+q0]
 mov ecx,[rip+c0]
 mov r8d,[rip+draw]
 mov r9d,[rip+outcome]
 sub rsp,16
 mov rax,[rip+source_kind]
 mov [rsp],rax
 xor eax,eax
 call printf@PLT
 add rsp,16
 add rsp,8
 pop rbx
 pop rbp
 ret
main:
 push rbp
 mov rbp,rsp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 mov [rip+main_stack],rsp
 cmp edi,2
 je .args_ok
 cmp edi,3
 je .three_args
 cmp edi,4
 je .four_args
 jmp bad_args
.three_args:
 mov r14,rsi
 mov rdi,[r14+16]
 lea rsi,[rip+str_trace]
 call strcmp@PLT
 test eax,eax
 jne .three_replay
 mov dword ptr [rip+trace_enabled],1
 mov rsi,r14
 jmp .args_ok
.three_replay:
 mov rsi,r14
 mov rax,[rsi+16]
 mov [rip+argfile],rax
 jmp .args_ok
.four_args:
 mov r14,rsi
 mov rdi,[r14+24]
 lea rsi,[rip+str_trace]
 call strcmp@PLT
 test eax,eax
 jne bad_args
 mov dword ptr [rip+trace_enabled],1
 mov rsi,r14
 mov rax,[rsi+16]
 mov [rip+argfile],rax
.args_ok:
 mov r12,[rsi+8]
 mov rdi,r12
 lea rsi,[rip+rmode]
 call fopen@PLT
 test rax,rax
 jz refuse_io
 mov [rip+input_file],rax
 # Get exact length and require bounded payload.
 mov rdi,rax
 xor esi,esi
 mov edx,2
 call fseek@PLT
 test eax,eax
 jne refuse_io
 mov rdi,[rip+input_file]
 call ftell@PLT
 cmp rax,64
 jl refuse_invalid
 cmp rax,65584
 jg refuse_invalid
 mov r13,rax
 mov rdi,[rip+input_file]
 call rewind@PLT
 lea rdi,[rip+header]
 mov esi,1
 mov edx,48
 mov rcx,[rip+input_file]
 call fread@PLT
 cmp rax,48
 jne refuse_io
 cmp dword ptr [rip+header],0x31555651
 jne refuse_invalid
 cmp dword ptr [rip+header+4],1
 jne refuse_invalid
 cmp dword ptr [rip+header+20],1
 jne refuse_invalid
 cmp qword ptr [rip+header+40],0
 jne refuse_invalid
 mov eax,[rip+header+8]
 cmp eax,1
 jl refuse_invalid
 cmp eax,20
 jg refuse_invalid
 mov [rip+nqubits],eax
 mov ecx,eax
 mov eax,1
 shl eax,cl
 mov [rip+dim],eax
 mov eax,[rip+header+12]
 cmp eax,1
 jl refuse_invalid
 cmp eax,32
 jg refuse_invalid
 mov [rip+nclass],eax
 mov eax,[rip+header+16]
 cmp eax,1
 jl refuse_invalid
 cmp eax,4096
 jg refuse_invalid
 mov [rip+count],eax
 mov edx,eax
 shl rdx,4
 add rdx,48
 cmp rdx,r13
 jne refuse_invalid
 lea rdi,[rip+packet]
 mov esi,16
 mov edx,[rip+count]
 mov rcx,[rip+input_file]
 call fread@PLT
 cmp eax,[rip+count]
 jne refuse_io
 mov rdi,[rip+input_file]
 call fclose@PLT
 movabs rax,0xcbf29ce484222325
 lea rsi,[rip+packet]
 mov ecx,[rip+count]
 shl ecx,4
.hash:
 movzx rdx,byte ptr [rsi]
 xor rax,rdx
 movabs r10,0x100000001b3
 imul rax,r10
 inc rsi
 dec ecx
 jne .hash
 cmp rax,[rip+header+32]
 jne refuse_invalid
 # validation pass before allocating state or consuming entropy
 xor r14d,r14d
.validate:
 cmp r14d,[rip+count]
 jae .validation_done
 lea rbx,[rip+packet]
 mov eax,r14d
 shl eax,4
 add rbx,rax
 cmp dword ptr [rbx+8],0
 jne refuse_invalid
 cmp dword ptr [rbx+12],0
 jne refuse_invalid
 movzx eax,byte ptr [rbx]
 cmp eax,1
 jl refuse_invalid
 cmp eax,16
 jg refuse_invalid
 movzx r10d,byte ptr [rbx+1]
 movzx r11d,byte ptr [rbx+2]
 movzx r12d,byte ptr [rbx+3]
 mov r13d,[rbx+4]
 cmp eax,16
 je .v_barrier
 cmp r10d,[rip+nqubits]
 jae refuse_invalid
 cmp eax,13
 je .v_if
 cmp eax,14
 je .v_if
 cmp eax,9
 je .v_pair
 cmp eax,10
 je .v_pair
 cmp eax,11
 je .v_measure
 cmp r11d,0
 jne refuse_invalid
 cmp r12d,0
 jne refuse_invalid
 cmp eax,15
 je .v_rz
 cmp r13d,0
 jne refuse_invalid
 jmp .v_next
.v_rz:
 cmp r13d,65535
 jg refuse_invalid
 cmp r13d,-65535
 jl refuse_invalid
 jmp .v_next
.v_barrier:
 test r10d,r10d
 jne refuse_invalid
 test r11d,r11d
 jne refuse_invalid
 test r12d,r12d
 jne refuse_invalid
 test r13d,r13d
 jne refuse_invalid
 jmp .v_next
.v_if:
 cmp r11d,0
 jne refuse_invalid
 cmp r12d,[rip+nclass]
 jae refuse_invalid
 cmp r13d,1
 jl refuse_invalid
 cmp r13d,8
 jg refuse_invalid
 jmp .v_next
.v_pair:
 cmp r11d,[rip+nqubits]
 jae refuse_invalid
 cmp r11d,r10d
 je refuse_invalid
 test r12d,r12d
 jne refuse_invalid
 test r13d,r13d
 jne refuse_invalid
 jmp .v_next
.v_measure:
 test r11d,r11d
 jne refuse_invalid
 cmp r12d,[rip+nclass]
 jae refuse_invalid
 test r13d,r13d
 jne refuse_invalid
.v_next:
 inc r14d
 jmp .validate
.validation_done:
 # optional exact replay source; read 4 bytes per measurement from file.
 mov rdi,[rip+argfile]
 test rdi,rdi
 jz .no_replay
 lea rsi,[rip+rmode]
 call fopen@PLT
 test rax,rax
 jz refuse_io
 mov [rip+replay_file],rax
.no_replay:
 mov edi,[rip+dim]
 mov esi,16
 call calloc@PLT
 test rax,rax
 jz refuse_io
 mov [rip+state_ptr],rax
 mov qword ptr [rax],1073741824
 mov dword ptr [rip+step],0
 # Install no-new-privileges and hardware-enforced seccomp BPF before the first gate.
 mov eax,157
 mov edi,38
 mov esi,1
 xor edx,edx
 xor r10d,r10d
 xor r8d,r8d
 syscall
 test eax,eax
 jne refuse_io
 mov eax,317
 mov edi,1
 xor esi,esi
 lea rdx,[rip+native_filter_program]
 syscall
 test eax,eax
 jne refuse_io
 .ifdef SECURITY_PROBE
 # Deliberately forbidden real syscall, exercised in the negative test build.
 mov eax,39
 syscall
 cmp rax,-1
 jne refuse_invalid
 mov dword ptr [rip+step],0
 .endif
.execute:
 mov eax,[rip+step]
 cmp eax,[rip+count]
 jae .finish
 lea rbx,[rip+packet]
 shl eax,4
 add rbx,rax
 movzx eax,byte ptr [rbx]
 mov [rip+op],eax
 mov [rip+src_op],eax
 movzx eax,byte ptr [rbx+1]
 mov [rip+q0],eax
 movzx eax,byte ptr [rbx+2]
 mov [rip+q1],eax
 movzx eax,byte ptr [rbx+3]
 mov [rip+c0],eax
 mov eax,[rbx+4]
 mov [rip+parm],eax
 mov eax,[rip+op]
 cmp eax,8
 jbe .exec_single
 cmp eax,10
 jbe .exec_double
 cmp eax,11
 je .exec_measure
 cmp eax,12
 je .exec_reset
 cmp eax,13
 je .exec_if1
 cmp eax,14
 je .exec_if0
 cmp eax,15
 je .exec_rz8
 jmp .next
.exec_single:
 call apply_single
 jmp .next
.exec_double:
 call apply_double
 jmp .next
.exec_measure:
 mov dword ptr [rip+reset_mode],0
 call measure
 jmp .next
.exec_reset:
 mov dword ptr [rip+reset_mode],1
 call measure
 cmp dword ptr [rip+outcome],0
 je .next
 mov dword ptr [rip+op],2
 call apply_single
 jmp .next
.exec_if1:
 mov ecx,[rip+c0]
 mov eax,[rip+classical]
 shr eax,cl
 test eax,1
 jz .next
 mov eax,[rip+parm]
 mov [rip+op],eax
 call apply_single
 jmp .next
.exec_if0:
 mov ecx,[rip+c0]
 mov eax,[rip+classical]
 shr eax,cl
 test eax,1
 jnz .next
 mov eax,[rip+parm]
 mov [rip+op],eax
 call apply_single
 jmp .next
.exec_rz8:
 mov eax,[rip+parm]
 and eax,7
 mov r14d,eax
.rz_loop:
 test r14d,r14d
 jz .next
 mov dword ptr [rip+op],7
 call apply_single
 dec r14d
 jmp .rz_loop
.next:
 cmp dword ptr [rip+trace_enabled],0
 je .skip_trace
 # FNV64 over the executed native Q30 state bytes.
 movabs rax,0xcbf29ce484222325
 mov rsi,[rip+state_ptr]
 mov ecx,[rip+dim]
 shl ecx,4
.hash_step:
 movzx rdx,byte ptr [rsi]
 xor rax,rdx
 movabs r10,0x100000001b3
 imul rax,r10
 inc rsi
 dec ecx
 jnz .hash_step
 lea rdi,[rip+fmt_step]
 mov esi,[rip+step]
 mov edx,[rip+src_op]
 mov ecx,[rip+q0]
 mov r8d,[rip+q1]
 mov r9d,[rip+c0]
 sub rsp,16
 mov [rsp],rax
 mov eax,[rip+classical]
 mov [rsp+8],rax
 xor eax,eax
 call printf@PLT
 add rsp,16
.skip_trace:
 inc dword ptr [rip+step]
 jmp .execute
.finish:
 # verify finite nonzero norm and output final state in integer coordinates.
 mov qword ptr [rip+ptotal],0
 mov qword ptr [rip+i_idx],0
.final_norm:
 mov rsi,[rip+i_idx]
 cmp esi,[rip+dim]
 jae .norm_end
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 mov rax,[rbx]
 imul rax
 mov r8,rax
 mov rax,[rbx+8]
 imul rax
 add rax,r8
 jc refuse_invalid
 add [rip+ptotal],rax
 jc refuse_invalid
 inc qword ptr [rip+i_idx]
 jmp .final_norm
.norm_end:
 cmp qword ptr [rip+ptotal],0
 je refuse_invalid
 lea rdi,[rip+fmt_ok]
 mov esi,[rip+nqubits]
 mov edx,[rip+nclass]
 mov ecx,[rip+count]
 mov r8d,[rip+classical]
 mov r9,[rip+ptotal]
 sub rsp,16
 mov rax,[rip+header+24]
 mov [rsp],rax
 xor eax,eax
 call printf@PLT
 add rsp,16
 # emit only nonzero amplitudes; allows native-independent numerical oracle comparisons.
 mov qword ptr [rip+i_idx],0
.output_amplitudes:
 mov rsi,[rip+i_idx]
 cmp esi,[rip+dim]
 jae .done
 mov rbx,[rip+state_ptr]
 lea rbx,[rbx+rsi*8]
 lea rbx,[rbx+rsi*8]
 mov rdx,[rbx]
 mov rcx,[rbx+8]
 mov rax,rdx
 or rax,rcx
 jz .next_amp
 lea rdi,[rip+fmt_amp]
 xor eax,eax
 call printf@PLT
.next_amp:
 inc qword ptr [rip+i_idx]
 jmp .output_amplitudes
.done:
 mov rdi,[rip+replay_file]
 test rdi,rdi
 jz .success
 # replay must not have extra draws (no hidden entropy consumption mismatch).
 mov rbx,rdi
 call fgetc@PLT
 cmp eax,-1
 jne refuse_invalid
 mov rdi,rbx
 call ferror@PLT
 test eax,eax
 jnz refuse_io
 mov rdi,rbx
 call fclose@PLT
.success:
 xor edi,edi
 call fflush@PLT
 test eax,eax
 jnz refuse_io
 xor eax,eax
 jmp quit
bad_args:
 lea rdi,[rip+usage]
 call puts@PLT
 mov eax,2
 jmp quit
refuse_invalid:
 lea rcx,[rip+invalid]
 jmp refuse
refuse_io:
 lea rcx,[rip+failio]
refuse:
 mov rdi,[rip+stderr]
 lea rsi,[rip+fmt_fail]
 mov rdx,rcx
 xor eax,eax
 call fprintf@PLT
 mov eax,3
quit:
 # Failure labels can be reached inside measure/apply/renormalize helpers.
 # Restore the main frame before unwinding, even on nested failure paths.
 mov rsp,[rip+main_stack]
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
