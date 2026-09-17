; sum_four, clang-O2, syntaxe Intel (objdump -M intel)
  2c00:  cmp    rsi,0x4
  2c04:  jae    2c14 <sum_four+0x14>
  2c06:  xor    r8d,r8d
  2c09:  xor    edx,edx
  2c0b:  xor    eax,eax
  2c0d:  xor    ecx,ecx
  2c0f:  xor    r10d,r10d
  2c12:  jmp    2c43 <sum_four+0x43>
  2c14:  xor    r9d,r9d
  2c17:  xor    ecx,ecx
  2c19:  xor    eax,eax
  2c1b:  xor    edx,edx
  2c1d:  xor    r8d,r8d
  2c20:  add    r8,QWORD PTR [rdi+r9*8]
  2c24:  add    rdx,QWORD PTR [rdi+r9*8+0x8]
  2c29:  add    rax,QWORD PTR [rdi+r9*8+0x10]
  2c2e:  add    rcx,QWORD PTR [rdi+r9*8+0x18]
  2c33:  lea    r10,[r9+0x4]
  2c37:  add    r9,0x8
  2c3b:  cmp    r9,rsi
  2c3e:  mov    r9,r10
  2c41:  jbe    2c20 <sum_four+0x20>
  2c43:  mov    r9,rsi
  2c46:  sub    r9,r10
  2c49:  jbe    2cbc <sum_four+0xbc>
  2c4b:  cmp    r9,0x4
  2c4f:  jae    2c56 <sum_four+0x56>
  2c51:  mov    r9,r10
  2c54:  jmp    2cb0 <sum_four+0xb0>
  2c56:  mov    r11d,esi
  2c59:  and    r11d,0x3
  2c5d:  sub    r9,r11
  2c60:  add    r9,r10
  2c63:  movq   xmm1,r8
  2c68:  pxor   xmm0,xmm0
  2c6c:  nop    DWORD PTR [rax+0x0]
  2c70:  movdqu xmm2,XMMWORD PTR [rdi+r10*8]
  2c76:  paddq  xmm1,xmm2
  2c7a:  movdqu xmm2,XMMWORD PTR [rdi+r10*8+0x10]
  2c81:  paddq  xmm0,xmm2
  2c85:  add    r10,0x4
  2c89:  cmp    r9,r10
  2c8c:  jne    2c70 <sum_four+0x70>
  2c8e:  paddq  xmm0,xmm1
  2c92:  pshufd xmm1,xmm0,0xee
  2c97:  paddq  xmm1,xmm0
  2c9b:  movq   r8,xmm1
  2ca0:  test   r11,r11
  2ca3:  je     2cbc <sum_four+0xbc>
  2ca5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2cb0:  add    r8,QWORD PTR [rdi+r9*8]
  2cb4:  inc    r9
  2cb7:  cmp    rsi,r9
  2cba:  jne    2cb0 <sum_four+0xb0>
  2cbc:  add    rax,rdx
  2cbf:  add    rax,rcx
  2cc2:  add    rax,r8
  2cc5:  ret
  2cc6:  cs nop WORD PTR [rax+rax*1+0x0]
