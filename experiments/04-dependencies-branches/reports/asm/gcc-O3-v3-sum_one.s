; sum_one, gcc-O3-v3, syntaxe Intel (objdump -M intel)
  2ce0:  endbr64
  2ce4:  test   rsi,rsi
  2ce7:  je     2d78 <sum_one+0x98>
  2ced:  lea    rax,[rsi-0x1]
  2cf1:  cmp    rax,0x2
  2cf5:  jbe    2d7b <sum_one+0x9b>
  2cfb:  mov    rdx,rsi
  2cfe:  mov    rax,rdi
  2d01:  vpxor  xmm0,xmm0,xmm0
  2d05:  shr    rdx,0x2
  2d09:  shl    rdx,0x5
  2d0d:  add    rdx,rdi
  2d10:  vpaddq ymm0,ymm0,YMMWORD PTR [rax]
  2d14:  add    rax,0x20
  2d18:  cmp    rax,rdx
  2d1b:  jne    2d10 <sum_one+0x30>
  2d1d:  vextracti128 xmm1,ymm0,0x1
  2d23:  vpaddq xmm0,xmm1,xmm0
  2d27:  vpsrldq xmm1,xmm0,0x8
  2d2c:  vpaddq xmm0,xmm0,xmm1
  2d30:  vmovq  rax,xmm0
  2d35:  test   sil,0x3
  2d39:  je     2d70 <sum_one+0x90>
  2d3b:  mov    rdx,rsi
  2d3e:  and    rdx,0xfffffffffffffffc
  2d42:  vzeroupper
  2d45:  lea    rcx,[rdx+0x1]
  2d49:  add    rax,QWORD PTR [rdi+rdx*8]
  2d4d:  cmp    rcx,rsi
  2d50:  jae    2d73 <sum_one+0x93>
  2d52:  lea    rcx,[rdx+0x2]
  2d56:  add    rax,QWORD PTR [rdi+rdx*8+0x8]
  2d5b:  cmp    rcx,rsi
  2d5e:  jae    2d73 <sum_one+0x93>
  2d60:  add    rax,QWORD PTR [rdi+rdx*8+0x10]
  2d65:  ret
  2d66:  cs nop WORD PTR [rax+rax*1+0x0]
  2d70:  vzeroupper
  2d73:  ret
  2d74:  nop    DWORD PTR [rax+0x0]
  2d78:  xor    eax,eax
  2d7a:  ret
  2d7b:  xor    edx,edx
  2d7d:  xor    eax,eax
  2d7f:  jmp    2d45 <sum_one+0x65>
  2d81:  nop    DWORD PTR [rax+0x0]
  2d85:  data16 cs nop WORD PTR [rax+rax*1+0x0]
