; sum_four, gcc-O2, syntaxe Intel (objdump -M intel)
  2c10:  endbr64
  2c14:  mov    r8,rdi
  2c17:  mov    rdi,rsi
  2c1a:  cmp    rsi,0x3
  2c1e:  jbe    2ca8 <sum_four+0x98>
  2c24:  lea    rsi,[rsi-0x4]
  2c28:  pxor   xmm0,xmm0
  2c2c:  mov    rax,r8
  2c2f:  xor    edx,edx
  2c31:  mov    rcx,rsi
  2c34:  movdqa xmm1,xmm0
  2c38:  shr    rcx,0x2
  2c3c:  add    rcx,0x1
  2c40:  movdqu xmm4,XMMWORD PTR [rax]
  2c44:  movdqu xmm5,XMMWORD PTR [rax+0x10]
  2c49:  add    rdx,0x1
  2c4d:  add    rax,0x20
  2c51:  paddq  xmm1,xmm4
  2c55:  paddq  xmm0,xmm5
  2c59:  cmp    rdx,rcx
  2c5c:  jb     2c40 <sum_four+0x30>
  2c5e:  movdqa xmm2,xmm1
  2c62:  psrldq xmm1,0x8
  2c67:  and    rsi,0xfffffffffffffffc
  2c6b:  paddq  xmm1,xmm0
  2c6f:  psrldq xmm0,0x8
  2c74:  lea    rax,[rsi+0x4]
  2c78:  paddq  xmm1,xmm0
  2c7c:  cmp    rax,rdi
  2c7f:  jae    2c9a <sum_four+0x8a>
  2c81:  lea    rax,[r8+rax*8]
  2c85:  lea    rdx,[r8+rdi*8]
  2c89:  movq   xmm0,QWORD PTR [rax]
  2c8d:  add    rax,0x8
  2c91:  paddq  xmm2,xmm0
  2c95:  cmp    rdx,rax
  2c98:  jne    2c89 <sum_four+0x79>
  2c9a:  paddq  xmm2,xmm1
  2c9e:  movq   rax,xmm2
  2ca3:  ret
  2ca4:  nop    DWORD PTR [rax+0x0]
  2ca8:  pxor   xmm1,xmm1
  2cac:  xor    eax,eax
  2cae:  movdqa xmm2,xmm1
  2cb2:  jmp    2c7c <sum_four+0x6c>
  2cb4:  nop
  2cb5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
