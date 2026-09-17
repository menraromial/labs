; sum_one, clang-O2, syntaxe Intel (objdump -M intel)
  2b90:  test   rsi,rsi
  2b93:  je     2ba1 <sum_one+0x11>
  2b95:  cmp    rsi,0x4
  2b99:  jae    2ba4 <sum_one+0x14>
  2b9b:  xor    ecx,ecx
  2b9d:  xor    eax,eax
  2b9f:  jmp    2bf0 <sum_one+0x60>
  2ba1:  xor    eax,eax
  2ba3:  ret
  2ba4:  mov    rcx,rsi
  2ba7:  and    rcx,0xfffffffffffffffc
  2bab:  pxor   xmm0,xmm0
  2baf:  xor    eax,eax
  2bb1:  pxor   xmm1,xmm1
  2bb5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2bc0:  movdqu xmm2,XMMWORD PTR [rdi+rax*8]
  2bc5:  paddq  xmm0,xmm2
  2bc9:  movdqu xmm2,XMMWORD PTR [rdi+rax*8+0x10]
  2bcf:  paddq  xmm1,xmm2
  2bd3:  add    rax,0x4
  2bd7:  cmp    rcx,rax
  2bda:  jne    2bc0 <sum_one+0x30>
  2bdc:  paddq  xmm1,xmm0
  2be0:  pshufd xmm0,xmm1,0xee
  2be5:  paddq  xmm0,xmm1
  2be9:  movq   rax,xmm0
  2bee:  jmp    2bf7 <sum_one+0x67>
  2bf0:  add    rax,QWORD PTR [rdi+rcx*8]
  2bf4:  inc    rcx
  2bf7:  cmp    rsi,rcx
  2bfa:  jne    2bf0 <sum_one+0x60>
  2bfc:  ret
  2bfd:  nop    DWORD PTR [rax]
