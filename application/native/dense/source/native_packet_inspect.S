.intel_syntax noprefix
# Native native quantum ABI inspector: independent packet verifier and IR disassembler.
# Does NOT execute the quantum state; safe to run on untrusted program bytes.
.section .rodata
usage: .asciz "usage: qvui FILE.qvb"
reading: .asciz "rb"
refuse: .asciz "QVU_INSPECT_REFUSED invalid or noncanonical packet"
errio: .asciz "QVU_INSPECT_REFUSED file I/O"
hdrfmt: .asciz "QVU_IR_HEADER qubits=%u cbits=%u ops=%u seedtag=%016lx records_fnv64=%016lx\n"
recfmt: .asciz "QVU_IR step=%u op=%s q0=%u q1=%u c0=%u param=%d\n"
okfmt: .asciz "QVU_INSPECT_PASS records=%u\n"
op0: .asciz "INVALID"
op1: .asciz "H"
op2: .asciz "X"
op3: .asciz "Y"
op4: .asciz "Z"
op5: .asciz "S"
op6: .asciz "SDG"
op7: .asciz "T"
op8: .asciz "TDG"
op9: .asciz "CX"
op10: .asciz "CZ"
op11: .asciz "MEASURE"
op12: .asciz "RESET"
op13: .asciz "IF1"
op14: .asciz "IF0"
op15: .asciz "RZ8"
op16: .asciz "BARRIER"
.align 8
opnames: .quad op0,op1,op2,op3,op4,op5,op6,op7,op8,op9,op10,op11,op12,op13,op14,op15,op16
.section .bss
.align 16
program: .skip 65584
fh: .skip 8
p_len: .skip 8
.section .text
.globl main
.extern fopen
.extern fseek
.extern ftell
.extern rewind
.extern fread
.extern fclose
.extern puts
.extern printf
.extern qvu_abi_packet_validate
main:
 push rbp
 mov rbp,rsp
 push rbx
 push r12
 push r13
 push r14
 push r15
 sub rsp,8
 cmp edi,2
 jne .usage
 mov rdi,[rsi+8]
 lea rsi,[rip+reading]
 call fopen@PLT
 test rax,rax
 jz .io
 mov [rip+fh],rax
 mov rdi,rax
 xor esi,esi
 mov edx,2
 call fseek@PLT
 test eax,eax
 jne .io
 mov rdi,[rip+fh]
 call ftell@PLT
 cmp rax,64
 jl .refuse
 cmp rax,65584
 jg .refuse
 mov [rip+p_len],rax
 mov rdi,[rip+fh]
 call rewind@PLT
 lea rdi,[rip+program]
 mov esi,1
 mov rdx,[rip+p_len]
 mov rcx,[rip+fh]
 call fread@PLT
 cmp rax,[rip+p_len]
 jne .io
 mov rdi,[rip+fh]
 call fclose@PLT
 lea rdi,[rip+program]
 mov rsi,[rip+p_len]
 call qvu_abi_packet_validate
 test eax,eax
 jne .refuse
 lea rdi,[rip+hdrfmt]
 mov esi,[rip+program+8]
 mov edx,[rip+program+12]
 mov ecx,[rip+program+16]
 mov r8,[rip+program+24]
 mov r9,[rip+program+32]
 xor eax,eax
 call printf@PLT
 xor r12d,r12d
 mov r13d,[rip+program+16]
 lea r14,[rip+program+48]
 lea r15,[rip+opnames]
.records:
 cmp r12d,r13d
 jae .passed
 movzx eax,byte ptr [r14]
 mov rsi,[r15+rax*8]
 movzx edx,byte ptr [r14+1]
 movzx ecx,byte ptr [r14+2]
 movzx r8d,byte ptr [r14+3]
 movsxd r9,dword ptr [r14+4]
 lea rdi,[rip+recfmt]
 sub rsp,16
 mov [rsp],r9
 mov r9d,r8d
 mov r8d,ecx
 mov ecx,edx
 mov rdx,rsi
 mov esi,r12d
 xor eax,eax
 call printf@PLT
 add rsp,16
 add r14,16
 inc r12d
 jmp .records
.passed:
 lea rdi,[rip+okfmt]
 mov esi,r13d
 xor eax,eax
 call printf@PLT
 xor eax,eax
 jmp .exit
.refuse:
 lea rdi,[rip+refuse]
 call puts@PLT
 mov eax,3
 jmp .exit
.io:
 lea rdi,[rip+errio]
 call puts@PLT
 mov eax,4
 jmp .exit
.usage:
 lea rdi,[rip+usage]
 call puts@PLT
 mov eax,2
.exit:
 add rsp,8
 pop r15
 pop r14
 pop r13
 pop r12
 pop rbx
 pop rbp
 ret
.section .note.GNU-stack,"",@progbits
