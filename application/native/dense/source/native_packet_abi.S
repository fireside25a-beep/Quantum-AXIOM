.intel_syntax noprefix
# native quantum QVU1 independently reusable, pure native x86-64 System V ABI.
# No libc, heap, syscall, dynamic loading or host-struct-dependent packet layout.
# int qvu_abi_packet_validate(const uint8_t *buf, uint64_t byte_len)
# int qvu_abi_seed_validate(const uint8_t *buf, uint64_t byte_len)
# return 0 on accepted canonical input; -1 on any refusal.
.section .text
.globl qvu_abi_seed_validate
.type qvu_abi_seed_validate,@function
qvu_abi_seed_validate:
 test rdi,rdi
 jz .seed_bad
 cmp rsi,64
 jne .seed_bad
 movabs rax,0x0031304445455351
 cmp [rdi],rax
 jne .seed_bad
 cmp dword ptr [rdi+8],1
 jne .seed_bad
 mov eax,[rdi+12]
 test eax,1                 # mandatory operating-system entropy provenance
 jz .seed_bad
 test eax,0xfffffff8       # currently defined OS + RDSEED + CPUID bits
 jnz .seed_bad
 xor eax,eax
 ret
.seed_bad:
 mov eax,-1
 ret
.size qvu_abi_seed_validate,.-qvu_abi_seed_validate
.globl qvu_abi_packet_validate
.type qvu_abi_packet_validate,@function
qvu_abi_packet_validate:
 test rdi,rdi
 jz .bad
 cmp rsi,64
 jb .bad
 cmp rsi,65584
 ja .bad
 cmp dword ptr [rdi],0x31555651
 jne .bad
 cmp dword ptr [rdi+4],1
 jne .bad
 cmp dword ptr [rdi+20],1
 jne .bad
 cmp qword ptr [rdi+40],0
 jne .bad
 mov ecx,[rdi+8]           # qubits
 cmp ecx,1
 jb .bad
 cmp ecx,256
 ja .bad
 mov ecx,[rdi+12]          # classical bits
 cmp ecx,1
 jb .bad
 cmp ecx,32
 ja .bad
 mov ecx,[rdi+16]          # records
 cmp ecx,1
 jb .bad
 cmp ecx,4096
 ja .bad
 mov eax,ecx
 shl rax,4
 add rax,48
 cmp rax,rsi
 jne .bad
 # Canonical byte-level checksum over records.
 lea r8,[rdi+48]
 mov r9d,[rdi+16]
 shl r9,4
 movabs rax,0xcbf29ce484222325
 movabs r11,0x100000001b3
.hash:
 movzx edx,byte ptr [r8]
 xor rax,rdx
 imul rax,r11
 inc r8
 dec r9
 jnz .hash
 cmp rax,[rdi+32]
 jne .bad
 # Validate all record fields without consuming entropy or allocating state.
 mov r8d,[rdi+16]  # count
 lea r9,[rdi+48]  # pointer
 mov esi,[rdi+8]   # qubits
 mov edi,[rdi+12]  # classical bits
.records:
 cmp dword ptr [r9+8],0
 jne .bad
 cmp dword ptr [r9+12],0
 jne .bad
 movzx ecx,byte ptr [r9]
 cmp ecx,1
 jb .bad
 cmp ecx,16
 ja .bad
 movzx eax,byte ptr [r9+1]  # q0
 movzx edx,byte ptr [r9+2]  # q1
 movzx r10d,byte ptr [r9+3] # c0
 cmp ecx,16
 je .barrier
 cmp eax,esi
 jae .bad
 cmp ecx,13
 je .if
 cmp ecx,14
 je .if
 cmp ecx,9
 je .pair
 cmp ecx,10
 je .pair
 cmp ecx,11
 je .measure
 # singles / reset / phase must have zero q1 and c0.
 test edx,edx
 jnz .bad
 test r10d,r10d
 jnz .bad
 cmp ecx,15
 je .rz
 cmp dword ptr [r9+4],0
 jne .bad
 jmp .next
.rz:
 movsxd r10,dword ptr [r9+4]
 cmp r10,65535
 jg .bad
 cmp r10,-65535
 jl .bad
 jmp .next
.barrier:
 test eax,eax
 jnz .bad
 test edx,edx
 jnz .bad
 test r10d,r10d
 jnz .bad
 cmp dword ptr [r9+4],0
 jne .bad
 jmp .next
.if:
 test edx,edx
 jnz .bad
 cmp r10d,edi
 jae .bad
 mov edx,[r9+4]
 cmp edx,1
 jb .bad
 cmp edx,8
 ja .bad
 jmp .next
.pair:
 cmp edx,esi
 jae .bad
 cmp edx,eax
 je .bad
 test r10d,r10d
 jnz .bad
 cmp dword ptr [r9+4],0
 jne .bad
 jmp .next
.measure:
 test edx,edx
 jnz .bad
 cmp r10d,edi
 jae .bad
 cmp dword ptr [r9+4],0
 jne .bad
.next:
 add r9,16
 dec r8
 jnz .records
 xor eax,eax
 ret
.bad:
 mov eax,-1
 ret
.size qvu_abi_packet_validate,.-qvu_abi_packet_validate
.section .note.GNU-stack,"",@progbits
