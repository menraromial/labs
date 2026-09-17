; sum_twice, clang-O2, syntaxe Intel (objdump -M intel)
  2cd0:  test   rsi,rsi
  2cd3:  je     2ce1 <sum_twice+0x11>
  2cd5:  cmp    rsi,0x4
  2cd9:  jae    2ce4 <sum_twice+0x14>
  2cdb:  xor    ecx,ecx
  2cdd:  xor    eax,eax
  2cdf:  jmp    2d30 <sum_twice+0x60>
  2ce1:  xor    eax,eax
  2ce3:  ret
  2ce4:  mov    rcx,rsi
  2ce7:  and    rcx,0xfffffffffffffffc
  2ceb:  pxor   xmm0,xmm0
  2cef:  xor    eax,eax
  2cf1:  pxor   xmm1,xmm1
  2cf5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2d00:  movdqu xmm2,XMMWORD PTR [rdi+rax*8]
  2d05:  paddq  xmm0,xmm2
  2d09:  movdqu xmm2,XMMWORD PTR [rdi+rax*8+0x10]
  2d0f:  paddq  xmm1,xmm2
  2d13:  add    rax,0x4
  2d17:  cmp    rcx,rax
  2d1a:  jne    2d00 <sum_twice+0x30>
  2d1c:  paddq  xmm1,xmm0
  2d20:  pshufd xmm0,xmm1,0xee
  2d25:  paddq  xmm0,xmm1
  2d29:  movq   rax,xmm0
  2d2e:  jmp    2d37 <sum_twice+0x67>
  2d30:  add    rax,QWORD PTR [rdi+rcx*8]
  2d34:  inc    rcx
  2d37:  cmp    rsi,rcx
  2d3a:  jne    2d30 <sum_twice+0x60>
  2d3c:  cmp    rsi,0x4
  2d40:  jae    2d46 <sum_twice+0x76>
  2d42:  xor    ecx,ecx
  2d44:  jmp    2d90 <sum_twice+0xc0>
  2d46:  mov    rcx,rsi
  2d49:  and    rcx,0xfffffffffffffffc
  2d4d:  movq   xmm1,rax
  2d52:  pxor   xmm0,xmm0
  2d56:  xor    eax,eax
  2d58:  nop    DWORD PTR [rax+rax*1+0x0]
  2d60:  movdqu xmm2,XMMWORD PTR [rdi+rax*8]
  2d65:  paddq  xmm1,xmm2
  2d69:  movdqu xmm2,XMMWORD PTR [rdi+rax*8+0x10]
  2d6f:  paddq  xmm0,xmm2
  2d73:  add    rax,0x4
  2d77:  cmp    rcx,rax
  2d7a:  jne    2d60 <sum_twice+0x90>
  2d7c:  paddq  xmm0,xmm1
  2d80:  pshufd xmm1,xmm0,0xee
  2d85:  paddq  xmm1,xmm0
  2d89:  movq   rax,xmm1
  2d8e:  jmp    2d97 <sum_twice+0xc7>
  2d90:  add    rax,QWORD PTR [rdi+rcx*8]
  2d94:  inc    rcx
  2d97:  cmp    rsi,rcx
  2d9a:  jne    2d90 <sum_twice+0xc0>
  2d9c:  ret
  2d9d:  nop    DWORD PTR [rax]
