.intel_syntax noprefix
# BSTBIT01: magic, u32 decoded length, u32 FNV1a, 3 encoded lanes.
# Standalone Linux x86-64 decoder/emitter. No libc or runtime interpreter.
# Each lane byte is bitreverse(decoded XOR 0xa5). Max 16384 output bytes.
# Read to EOF (including pipes/short reads), validate before any output.
.section .bss
.balign 16
input: .skip 49169
output: .skip 16384
.section .text
.global _start
_start:
 xor r12d,r12d
read_more:
 xor eax,eax
 xor edi,edi
 lea rsi,[rip+input]
 add rsi,r12
 mov edx,49169
 sub rdx,r12
 syscall
 cmp rax,-4
 je read_more
 test rax,rax
 js fail
 jz read_done
 add r12,rax
 cmp r12,49169
 jae fail
 jmp read_more
read_done:
 cmp r12,19
 jb fail
 lea rsi,[rip+input]
 movabs rax,0x3130544942545342
 cmp [rsi],rax
 jne fail
 mov r13d,[rsi+8]
 test r13d,r13d
 jz fail
 cmp r13d,16384
 ja fail
 lea rax,[r13+r13*2+16]
 cmp rax,r12
 jne fail
 mov r10d,[rsi+12]
 add rsi,16
 lea r14,[rsi+r13]
 lea r15,[r14+r13]
 lea rdi,[rip+output]
 mov r9d,0x811c9dc5
 mov rcx,r13
decode:
 mov al,[rsi]
 mov bl,[r14]
 mov dl,[r15]
 mov r8b,al
 and r8b,bl
 mov r11b,al
 and r11b,dl
 or r8b,r11b
 and bl,dl
 or r8b,bl
 mov al,r8b
 # Bit reversal in three swap stages, then undo XOR encoding.
 mov bl,al
 shr bl,1
 and bl,0x55
 and al,0x55
 shl al,1
 or al,bl
 mov bl,al
 shr bl,2
 and bl,0x33
 and al,0x33
 shl al,2
 or al,bl
 rol al,4
 xor al,0xa5
 mov [rdi],al
 movzx eax,al
 xor r9d,eax
 imul r9d,r9d,0x1000193
 inc rsi
 inc r14
 inc r15
 inc rdi
 dec rcx
 jnz decode
 cmp r9d,r10d
 jne fail
 # Stackable BPF confinement, compatible with an existing host filter.
 mov eax,157
 mov edi,38
 mov esi,1
 xor edx,edx
 xor r10d,r10d
 xor r8d,r8d
 syscall
 test eax,eax
 jnz fail
 mov eax,317
 mov edi,1
 xor esi,esi
 lea rdx,[rip+filter_program]
 syscall
 test eax,eax
 jnz fail
 .ifdef SECURITY_PROBE
 mov eax,39
 syscall
 jmp fail
 .endif
 lea r14,[rip+output]
write_more:
 mov eax,1
 mov edi,1
 mov rsi,r14
 mov rdx,r13
 syscall
 cmp rax,-4
 je write_more
 test rax,rax
 jle fail
 add r14,rax
 sub r13,rax
 jnz write_more
 xor edi,edi
 jmp quit
fail:
 mov edi,1
quit:
 mov eax,60
 syscall
.section .rodata
.balign 8
filter:
 .short 0x20; .byte 0,0; .long 4
 .short 0x15; .byte 1,0; .long 0xc000003e
 .short 0x06; .byte 0,0; .long 0x80000000
 .short 0x20; .byte 0,0; .long 0
 .short 0x15; .byte 2,0; .long 1
 .short 0x15; .byte 1,0; .long 60
 .short 0x06; .byte 0,0; .long 0x80000000
 .short 0x06; .byte 0,0; .long 0x7fff0000
filter_end:
.balign 8
filter_program:
 .short (filter_end-filter)/8
 .zero 6
 .quad filter
.section .note.GNU-stack,"",@progbits
