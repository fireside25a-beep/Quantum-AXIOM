.intel_syntax noprefix
.section .rodata
usage: .ascii "usage: native_q_seed OUT.seed (exclusive create)\n"
.set usagelen, . - usage
err: .ascii "native_q_seed: entropy or output failure\n"
.set errlen, . - err
.section .bss
.align 16
seedbuf: .skip 64
.section .text
.global _start
_start:
  mov rbp, rsp
  mov rax, [rbp]
  cmp rax, 2
  jne bad_usage
  # QSEED01\0, version 1, provenance bitfield; little endian
  lea rdi, [rip+seedbuf]
  mov rax, 0x0031304445455351
  mov [rdi], rax
  mov DWORD PTR [rdi+8], 1
  # OS getrandom must provide all 32 bytes; no weak fallback.
  lea r12, [rdi+16]
  xor r13, r13
read_random:
  mov eax, 318
  lea rdi, [r12+r13]
  mov edx, 0
  mov esi, 32
  sub rsi, r13
  syscall
  cmp rax, 0
  jle fail
  add r13, rax
  cmp r13, 32
  jb read_random
  lea r12, [rip+seedbuf]
  mov DWORD PTR [r12+12], 1   # bit 0 OS entropy
  # CPUID is a hardware instruction giving the CPU vendor and capabilities.
  push rbx
  xor eax, eax
  cpuid
  mov r15d,eax  # highest supported basic CPUID leaf
  mov DWORD PTR [r12+48], ebx
  mov DWORD PTR [r12+52], edx
  mov DWORD PTR [r12+56], ecx
  mov DWORD PTR [r12+12], 5  # bit 2 CPUID recorded
  # Native RDSEED attempted only when reported as available.
  cmp r15d,7
  jb no_rdseed
  xor ecx, ecx
  mov eax, 7
  cpuid
  bt ebx, 18
  jnc no_rdseed
  mov r8d, 16
rdseed_try:
  rdseed rax
  jc got_rdseed
  dec r8d
  jnz rdseed_try
  jmp no_rdseed
got_rdseed:
  xor QWORD PTR [r12+16], rax
  or DWORD PTR [r12+12], 2
no_rdseed:
  pop rbx
  # Mix recorded machine identity into an auxiliary machine tag, not the
  # OS randomness security claim. Nonsecret seed material is replayable.
  mov rax, [r12+48]
  mov r9, 0x4e53464142524943
  xor rax, r9
  rol rax, 13
  mov [r12+60], eax  # retain all 12 vendor bytes at offsets 48..59
  # openat(AT_FDCWD, argv[1], O_WRONLY|O_CREAT|O_EXCL, 0600)
  mov rax, [rbp+16]
  mov rsi, rax
  mov eax, 257
  mov edi, -100
  mov edx, 193
  mov r10d, 384
  syscall
  test rax, rax
  js fail
  mov r14, rax
  mov eax, 1
  mov rdi, r14
  lea rsi, [rip+seedbuf]
  mov edx, 64
  syscall
  cmp rax, 64
  jne cleanup_fail
  mov eax, 3
  mov rdi, r14
  syscall
  xor edi, edi
  mov eax, 60
  syscall
cleanup_fail:
  mov eax, 3
  mov rdi, r14
  syscall
fail:
  mov eax, 1
  mov edi, 2
  lea rsi, [rip+err]
  mov edx, errlen
  syscall
  mov edi, 1
  mov eax, 60
  syscall
bad_usage:
  mov eax, 1
  mov edi, 2
  lea rsi, [rip+usage]
  mov edx, usagelen
  syscall
  mov edi, 2
  mov eax, 60
  syscall
