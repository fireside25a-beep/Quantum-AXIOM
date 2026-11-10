.intel_syntax noprefix
# Native native quantum QVU1 packet compiler, x86-64 SysV; calls libc only for I/O and tokenization.
.section .rodata
rmode: .asciz "rb"
wmode: .asciz "wbx"
delim: .asciz " \t\r\n"
fmt_ok: .asciz "QVU_COMPILED qubits=%u cbits=%u ops=%u seedtag=%016lx\n"
fmt_err: .asciz "QVU_COMPILE_REFUSED line=%u reason=%s\n"
err_args: .asciz "usage: qvuc SOURCE.ql SEED.bin OUTPUT.qvb"
err_parse: .asciz "invalid syntax, operand or range"
err_io: .asciz "input/seed/output failure"
str_q: .asciz "qubits"
str_c: .asciz "cbits"
str_h: .asciz "H"
str_x: .asciz "X"
str_y: .asciz "Y"
str_z: .asciz "Z"
str_s: .asciz "S"
str_sdg: .asciz "SDG"
str_t: .asciz "T"
str_tdg: .asciz "TDG"
str_cx: .asciz "CX"
str_cz: .asciz "CZ"
str_meas: .asciz "MEASURE"
str_reset: .asciz "RESET"
str_if1: .asciz "IF1"
str_if0: .asciz "IF0"
str_rz: .asciz "RZ8"
str_bar: .asciz "BARRIER"
str_comptime: .asciz "COMPTIME"
str_repeat: .asciz "REPEAT"
str_require_qubits: .asciz "REQUIRE_QUBITS"
str_require_cbits: .asciz "REQUIRE_CBITS"
# opcode indexed by table order
opcodes: .byte 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16
.align 8
names: .quad str_h,str_x,str_y,str_z,str_s,str_sdg,str_t,str_tdg,str_cx,str_cz,str_meas,str_reset,str_if1,str_if0,str_rz,str_bar
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
linebuf: .skip 1024
records: .skip 65536
header: .skip 48
seed: .skip 64
saveptr: .skip 8
infile: .skip 8
seedfile: .skip 8
outfile: .skip 8
word0: .skip 8
line_num: .skip 4
nq: .skip 4
nc: .skip 4
nc_declared: .skip 4
nops: .skip 4
started: .skip 4
repeat_extra: .skip 4
opcode: .skip 4
operands: .skip 12
.section .text
.global main
.extern fopen
.extern fclose
.extern fgetc
.extern fgets
.extern fread
.extern fwrite
.extern strtok_r
.extern strcmp
.extern strtol
.extern printf
.extern puts
.extern fprintf
.extern stderr
.extern ferror
.extern qvu_abi_seed_validate
# get_token() -> rax
get_token:
 push rbp
 mov rbp, rsp
 xor edi, edi
 lea rsi, [rip+delim]
 lea rdx, [rip+saveptr]
 call strtok_r@PLT
 pop rbp
 ret
# parse_i(token pointer rdi) -> rax; CF=1 on error; bounded signed [-65535,65535]
parse_i:
 push rbp
 mov rbp, rsp
 sub rsp, 16
 test rdi,rdi
 jz .ip_bad
 mov [rbp-16], rdi
 lea rsi,[rbp-8]
 mov edx,10
 call strtol@PLT
 mov rcx,[rbp-8]
 cmp rcx,[rbp-16]
 je .ip_bad
 cmp byte ptr [rcx],0
 jne .ip_bad
 cmp rax,65535
 jg .ip_bad
 cmp rax,-65535
 jl .ip_bad
 clc
 leave
 ret
.ip_bad:
 stc
 leave
 ret
# main: strict one-line op parser; rejects malformed/extra tokens.
main:
 push rbp
 mov rbp,rsp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,40
 cmp edi,4
 jne bad_args
 mov r12,[rsi+8]
 mov r13,[rsi+16]
 mov r14,[rsi+24]
 # seed exact 64 bytes
 mov rdi,r13
 lea rsi,[rip+rmode]
 call fopen@PLT
 test rax,rax
 jz bad_io
 mov [rip+seedfile],rax
 lea rdi,[rip+seed]
 mov esi,1
 mov edx,64
 mov rcx,rax
 call fread@PLT
 cmp rax,64
 jne bad_io
 mov rdi,[rip+seedfile]
 call fgetc@PLT
 cmp eax,-1
 jne bad_io
 mov rdi,[rip+seedfile]
 call ferror@PLT
 test eax,eax
 jnz bad_io
 lea rdi,[rip+seed]
 mov esi,64
 call qvu_abi_seed_validate
 test eax,eax
 jne bad_io
 mov rdi,[rip+seedfile]
 call fclose@PLT
 # input
 mov rdi,r12
 lea rsi,[rip+rmode]
 call fopen@PLT
 test rax,rax
 jz bad_io
 mov [rip+infile],rax
.read_line:
 # Read bytes explicitly: fgets/strlen silently truncated embedded NUL bytes.
 # Bound each physical line and reject non-ASCII input before tokenization.
 xor r15d,r15d
.read_byte:
 mov rdi,[rip+infile]
 call fgetc@PLT
 cmp eax,-1
 je .line_eof
 test eax,eax
 jz bad_parse
 cmp eax,127
 ja bad_parse
 cmp r15d,1022
 jae bad_parse
 lea rdx,[rip+linebuf]
 mov [rdx+r15],al
 inc r15d
 cmp al,10
 jne .read_byte
 jmp .line_ready
.line_eof:
 mov rdi,[rip+infile]
 call ferror@PLT
 test eax,eax
 jnz bad_io
 test r15d,r15d
 jz .done_parse
.line_ready:
 lea rax,[rip+linebuf]
 mov byte ptr [rax+r15],0
 add dword ptr [rip+line_num],1
 # ensure no line longer than 1023 chars: fgets may clip, reject at 1023
 lea rdi,[rip+linebuf]
 xor ecx,ecx
 .len_loop:
 cmp byte ptr [rdi+rcx],0
 je .len_done
 inc ecx
 cmp ecx,1023
 jae bad_parse
 jmp .len_loop
 .len_done:
 mov rdi,rax
 lea rsi,[rip+delim]
 lea rdx,[rip+saveptr]
 call strtok_r@PLT
 test rax,rax
 jz .read_line
 cmp byte ptr [rax],'#'
 je .read_line
 mov [rip+word0],rax
 mov rdi,rax
 lea rsi,[rip+str_q]
 call strcmp@PLT
 test eax,eax
 jne .not_q
 cmp dword ptr [rip+nq],0
 jne bad_parse
 cmp dword ptr [rip+started],0
 jne bad_parse
 call get_token
 mov rdi,rax
 call parse_i
 jc bad_parse
 cmp rax,1
 jl bad_parse
 cmp rax,256
 jg bad_parse
 mov [rip+nq],eax
 mov dword ptr [rip+nc],1  # documented default when cbits is omitted
 call get_token
 test rax,rax
 jnz .check_comment_q
 jmp .read_line
.check_comment_q:
 cmp byte ptr [rax],'#'
 jne bad_parse
 jmp .read_line
.not_q:
 mov rdi,[rip+word0]
 lea rsi,[rip+str_c]
 call strcmp@PLT
 test eax,eax
 jne .not_c
 cmp dword ptr [rip+nq],0
 je bad_parse
 cmp dword ptr [rip+started],0
 jne bad_parse
 cmp dword ptr [rip+nc_declared],0
 jne bad_parse
 call get_token
 mov rdi,rax
 call parse_i
 jc bad_parse
 cmp eax,1
 jl bad_parse
 cmp eax,32
 jg bad_parse
 mov [rip+nc],eax
 mov dword ptr [rip+nc_declared],1
 call get_token
 test rax,rax
 jnz .check_comment_c
 jmp .read_line
.check_comment_c:
 cmp byte ptr [rax],'#'
 jne bad_parse
 jmp .read_line
.not_c:
 cmp dword ptr [rip+nq],0
 je bad_parse
 # Compile-time stage: explicit bounds check or bounded instruction expansion.
 # These are executed by this native compiler and are NOT QVU runtime ops.
 mov dword ptr [rip+repeat_extra],0
 mov rdi,[rip+word0]
 lea rsi,[rip+str_comptime]
 call strcmp@PLT
 test eax,eax
 jne .not_comptime
 call get_token
 test rax,rax
 jz bad_parse
 mov [rip+word0],rax
 mov rdi,rax
 lea rsi,[rip+str_require_qubits]
 call strcmp@PLT
 test eax,eax
 je .require_qubits
 mov rdi,[rip+word0]
 lea rsi,[rip+str_require_cbits]
 call strcmp@PLT
 test eax,eax
 je .require_cbits
 mov rdi,[rip+word0]
 lea rsi,[rip+str_repeat]
 call strcmp@PLT
 test eax,eax
 jne bad_parse
 call get_token
 mov rdi,rax
 call parse_i
 jc bad_parse
 cmp eax,2
 jl bad_parse
 cmp eax,64
 jg bad_parse
 dec eax
 mov [rip+repeat_extra],eax
 call get_token
 test rax,rax
 jz bad_parse
 mov [rip+word0],rax
 jmp .ready_operation
.require_qubits:
 call get_token
 mov rdi,rax
 call parse_i
 jc bad_parse
 cmp eax,1
 jl bad_parse
 cmp eax,[rip+nq]
 jg bad_parse
 call get_token
 test rax,rax
 jnz bad_parse
 jmp .read_line
.require_cbits:
 call get_token
 mov rdi,rax
 call parse_i
 jc bad_parse
 cmp eax,1
 jl bad_parse
 cmp eax,[rip+nc]
 jg bad_parse
 call get_token
 test rax,rax
 jnz bad_parse
 jmp .read_line
.not_comptime:
 # A bare REPEAT is deliberately not accepted; comptime must be explicit.
.ready_operation:
 mov dword ptr [rip+started],1
 mov r15d,0
.find_op:
 cmp r15d,16
 jae bad_parse
 lea rdx,[rip+names]
 mov rdi,[rip+word0]
 mov rsi,[rdx+r15*8]
 call strcmp@PLT
 test eax,eax
 je .found_op
 inc r15d
 jmp .find_op
.found_op:
 lea rdx,[rip+opcodes]
 movzx eax,byte ptr [rdx+r15]
 mov [rip+opcode],eax
 mov dword ptr [rip+operands],0
 mov dword ptr [rip+operands+4],0
 mov dword ptr [rip+operands+8],0
 # op 1..8 or 12 : 1 operand
 mov ecx,1
 cmp r15d,8
 jl .args_count_done
 cmp r15d,11
 jle .two_if_needed
 cmp r15d,12
 je .two_if_needed
 cmp r15d,13
 je .two_if_needed
 cmp r15d,14
 je .two_if_needed
 cmp r15d,15
 je .zero_args
 jmp bad_parse
.two_if_needed:
 cmp r15d,11
 je .args_count_done
 cmp r15d,8
 jl .args_count_done
 mov ecx,2
 cmp r15d,12
 jl .args_count_done
 cmp r15d,14
 jl .three_args
 jmp .args_count_done
.three_args:
 mov ecx,3
 jmp .args_count_done
.zero_args:
 xor ecx,ecx
.args_count_done:
 mov r15d,ecx
 xor r13d,r13d
.read_arg:
 cmp r13d,r15d
 jge .args_done
 call get_token
 mov rdi,rax
 cmp dword ptr [rip+opcode],13
 je .try_if_mnemonic
 cmp dword ptr [rip+opcode],14
 jne .parse_numeric
.try_if_mnemonic:
 cmp r13d,1
 jne .parse_numeric
 test rax,rax
 jz bad_parse
 mov [rip+word0],rax
 xor r12d,r12d
.mnemonic_loop:
 cmp r12d,8
 jae .parse_numeric_from_saved
 lea rdx,[rip+names]
 mov rdi,[rip+word0]
 mov rsi,[rdx+r12*8]
 call strcmp@PLT
 test eax,eax
 je .mnemonic_found
 inc r12d
 jmp .mnemonic_loop
.mnemonic_found:
 lea eax,[r12+1]
 jmp .parsed_numeric
.parse_numeric_from_saved:
 mov rax,[rip+word0]
.parse_numeric:
 mov rdi,rax
 call parse_i
 jc bad_parse
.parsed_numeric:
 lea rdx,[rip+operands]
 mov [rdx+r13*4],eax
 inc r13d
 jmp .read_arg
.args_done:
 call get_token
 test rax,rax
 jz .validate_args
 cmp byte ptr [rax],'#'
 jne bad_parse
.validate_args:
 mov r11d,[rip+opcode]
 # arg0 is always qubit except IF op where arg0 is cbit; barrier no args
 cmp r11d,16
 je .store
 cmp r11d,13
 je .ifargs
 cmp r11d,14
 je .ifargs
 mov eax,[rip+operands]
 cmp eax,0
 jl bad_parse
 cmp eax,[rip+nq]
 jae bad_parse
 jmp .other_args
.ifargs:
 mov eax,[rip+operands]
 cmp eax,0
 jl bad_parse
 cmp eax,[rip+nc]
 jae bad_parse
 mov eax,[rip+operands+4]
 cmp eax,1
 jl bad_parse
 cmp eax,8
 jg bad_parse
 mov eax,[rip+operands+8]
 cmp eax,0
 jl bad_parse
 cmp eax,[rip+nq]
 jae bad_parse
 jmp .store
.other_args:
 cmp r11d,9
 je .twoqubit
 cmp r11d,10
 je .twoqubit
 cmp r11d,11
 je .measure
 cmp r11d,15
 je .store
 jmp .store
.twoqubit:
 mov eax,[rip+operands+4]
 cmp eax,0
 jl bad_parse
 cmp eax,[rip+nq]
 jae bad_parse
 cmp eax,[rip+operands]
 je bad_parse
 jmp .store
.measure:
 mov eax,[rip+operands+4]
 cmp eax,0
 jl bad_parse
 cmp eax,[rip+nc]
 jae bad_parse
.store:
 mov eax,[rip+nops]
 cmp eax,4096
 jae bad_parse
 shl eax,4
 lea rbx,[rip+records]
 add rbx,rax
 mov eax,[rip+opcode]
 mov [rbx],al
 mov eax,[rip+operands]
 mov [rbx+1],al
 mov r11d,[rip+opcode]
 cmp r11d,13
 je .ifstore
 cmp r11d,14
 je .ifstore
 cmp r11d,9
 je .set_second
 cmp r11d,10
 je .set_second
 cmp r11d,11
 je .set_c
 cmp r11d,15
 je .set_param
 jmp .stored
.ifstore:
 mov eax,[rip+operands+8]
 mov [rbx+1],al
 mov eax,[rip+operands]
 mov [rbx+3],al
 mov eax,[rip+operands+4]
 mov [rbx+4],eax
 jmp .stored
.set_second:
 mov eax,[rip+operands+4]
 mov [rbx+2],al
 jmp .stored
.set_c:
 mov eax,[rip+operands+4]
 mov [rbx+3],al
 jmp .stored
.set_param:
 mov eax,[rip+operands+4]
 mov [rbx+4],eax
.stored:
 inc dword ptr [rip+nops]
 # Repeat expands into real canonical QVU records at compilation time.
 # Copy the verified canonical record bytes; never execute a runtime loop.
.repeat_more:
 cmp dword ptr [rip+repeat_extra],0
 je .read_line
 cmp dword ptr [rip+nops],4096
 jae bad_parse
 lea rdi,[rbx+16]
 mov rsi,rbx
 mov ecx,16
 rep movsb
 add rbx,16
 inc dword ptr [rip+nops]
 dec dword ptr [rip+repeat_extra]
 jmp .repeat_more
.done_parse:
 cmp dword ptr [rip+nops],0
 je bad_parse
 cmp dword ptr [rip+nc],0
 jne .nc_ok
 mov dword ptr [rip+nc],1
.nc_ok:
 mov rdi,[rip+infile]
 call fclose@PLT
 # compute seedtag FNV64
 movabs rax,0xcbf29ce484222325
 lea rsi,[rip+seed]
 mov ecx,64
 .hash_seed:
 movzx rdx,byte ptr [rsi]
 xor rax,rdx
 movabs r10,0x100000001b3
 imul rax,r10
 inc rsi
 dec ecx
 jne .hash_seed
 mov r12,rax
 # compute record hash FNV64
 movabs rax,0xcbf29ce484222325
 lea rsi,[rip+records]
 mov ecx,[rip+nops]
 shl ecx,4
 .hash_code:
 movzx rdx,byte ptr [rsi]
 xor rax,rdx
 movabs r10,0x100000001b3
 imul rax,r10
 inc rsi
 dec ecx
 jne .hash_code
 # header
 lea rdi,[rip+header]
 mov dword ptr [rdi],0x31555651
 mov dword ptr [rdi+4],1
 mov edx,[rip+nq]
 mov [rdi+8],edx
 mov edx,[rip+nc]
 mov [rdi+12],edx
 mov edx,[rip+nops]
 mov [rdi+16],edx
 mov dword ptr [rdi+20],1
 mov [rdi+24],r12
 mov [rdi+32],rax
 mov rdi,r14
 lea rsi,[rip+wmode]
 call fopen@PLT
 test rax,rax
 jz bad_io
 mov [rip+outfile],rax
 # Lock native compiler after parsing, source closure and exclusive output open.
 mov eax,157
 mov edi,38
 mov esi,1
 xor edx,edx
 xor r10d,r10d
 xor r8d,r8d
 syscall
 test eax,eax
 jne bad_io
 mov eax,317
 mov edi,1
 xor esi,esi
 lea rdx,[rip+native_filter_program]
 syscall
 test eax,eax
 jne bad_io
 .ifdef SECURITY_PROBE
 mov eax,39
 syscall
 cmp rax,-1
 jne bad_io
 .endif
 lea rdi,[rip+header]
 mov esi,1
 mov edx,48
 mov rcx,[rip+outfile]
 call fwrite@PLT
 cmp rax,48
 jne bad_io
 lea rdi,[rip+records]
 mov esi,16
 mov edx,[rip+nops]
 mov rcx,[rip+outfile]
 call fwrite@PLT
 cmp eax,[rip+nops]
 jne bad_io
 mov rdi,[rip+outfile]
 call fclose@PLT
 test eax,eax
 jne bad_io
 lea rdi,[rip+fmt_ok]
 mov esi,[rip+nq]
 mov edx,[rip+nc]
 mov ecx,[rip+nops]
 mov r8,r12
 xor eax,eax
 call printf@PLT
 xor eax,eax
 jmp quit
bad_args:
 lea rdi,[rip+err_args]
 call puts@PLT
 mov eax,2
 jmp quit
bad_parse:
 mov rdi,[rip+stderr]
 lea rsi,[rip+fmt_err]
 mov edx,[rip+line_num]
 lea rcx,[rip+err_parse]
 xor eax,eax
 call fprintf@PLT
 mov eax,3
 jmp quit
bad_io:
 mov rdi,[rip+stderr]
 lea rsi,[rip+fmt_err]
 mov edx,[rip+line_num]
 lea rcx,[rip+err_io]
 xor eax,eax
 call fprintf@PLT
 mov eax,4
quit:
 add rsp,40
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
