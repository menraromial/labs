; sum_one, clang-O3-v3, syntaxe Intel (objdump -M intel)
  2cb0:  test   rsi,rsi
  2cb3:  je     2cc4 <sum_one+0x14>
  2cb5:  cmp    rsi,0x3
  2cb9:  ja     2cc7 <sum_one+0x17>
  2cbb:  xor    ecx,ecx
  2cbd:  xor    eax,eax
  2cbf:  jmp    2d78 <sum_one+0xc8>
  2cc4:  xor    eax,eax
  2cc6:  ret
  2cc7:  cmp    rsi,0x10
  2ccb:  jae    2cd3 <sum_one+0x23>
  2ccd:  xor    ecx,ecx
  2ccf:  xor    eax,eax
  2cd1:  jmp    2d3f <sum_one+0x8f>
  2cd3:  mov    rcx,rsi
  2cd6:  and    rcx,0xfffffffffffffff0
  2cda:  vpxor  xmm0,xmm0,xmm0
  2cde:  xor    eax,eax
  2ce0:  vpxor  xmm1,xmm1,xmm1
  2ce4:  vpxor  xmm2,xmm2,xmm2
  2ce8:  vpxor  xmm3,xmm3,xmm3
  2cec:  nop    DWORD PTR [rax+0x0]
  2cf0:  vpaddq ymm0,ymm0,YMMWORD PTR [rdi+rax*8]
  2cf5:  vpaddq ymm1,ymm1,YMMWORD PTR [rdi+rax*8+0x20]
  2cfb:  vpaddq ymm2,ymm2,YMMWORD PTR [rdi+rax*8+0x40]
  2d01:  vpaddq ymm3,ymm3,YMMWORD PTR [rdi+rax*8+0x60]
  2d07:  add    rax,0x10
  2d0b:  cmp    rcx,rax
  2d0e:  jne    2cf0 <sum_one+0x40>
  2d10:  vpaddq ymm0,ymm1,ymm0
  2d14:  vpaddq ymm1,ymm3,ymm2
  2d18:  vpaddq ymm0,ymm1,ymm0
  2d1c:  vextracti128 xmm1,ymm0,0x1
  2d22:  vpaddq xmm0,xmm0,xmm1
  2d26:  vpshufd xmm1,xmm0,0xee
  2d2b:  vpaddq xmm0,xmm0,xmm1
  2d2f:  vmovq  rax,xmm0
  2d34:  cmp    rsi,rcx
  2d37:  je     2d84 <sum_one+0xd4>
  2d39:  test   sil,0xc
  2d3d:  je     2d78 <sum_one+0xc8>
  2d3f:  mov    rdx,rcx
  2d42:  mov    rcx,rsi
  2d45:  and    rcx,0xfffffffffffffffc
  2d49:  vmovq  xmm0,rax
  2d4e:  xchg   ax,ax
  2d50:  vpaddq ymm0,ymm0,YMMWORD PTR [rdi+rdx*8]
  2d55:  add    rdx,0x4
  2d59:  cmp    rcx,rdx
  2d5c:  jne    2d50 <sum_one+0xa0>
  2d5e:  vextracti128 xmm1,ymm0,0x1
  2d64:  vpaddq xmm0,xmm0,xmm1
  2d68:  vpshufd xmm1,xmm0,0xee
  2d6d:  vpaddq xmm0,xmm0,xmm1
  2d71:  vmovq  rax,xmm0
  2d76:  jmp    2d7f <sum_one+0xcf>
  2d78:  add    rax,QWORD PTR [rdi+rcx*8]
  2d7c:  inc    rcx
  2d7f:  cmp    rsi,rcx
  2d82:  jne    2d78 <sum_one+0xc8>
  2d84:  vzeroupper
  2d87:  ret
  2d88:  nop    DWORD PTR [rax+rax*1+0x0]
