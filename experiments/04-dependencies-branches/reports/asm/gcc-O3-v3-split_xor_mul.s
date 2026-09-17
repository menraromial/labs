; split_xor_mul, gcc-O3-v3, syntaxe Intel (objdump -M intel)
  2bc0:  endbr64
  2bc4:  test   rsi,rsi
  2bc7:  je     2cc8 <split_xor_mul+0x108>
  2bcd:  lea    rax,[rsi-0x1]
  2bd1:  cmp    rax,0x4
  2bd5:  jbe    2ccb <split_xor_mul+0x10b>
  2bdb:  mov    rdx,rsi
  2bde:  vmovdqa ymm4,YMMWORD PTR [rip+0x19fa]        # 45e0 <kernel_build+0x10>
  2be6:  mov    rax,rdi
  2be9:  vpxor  xmm3,xmm3,xmm3
  2bed:  shr    rdx,0x2
  2bf1:  shl    rdx,0x5
  2bf5:  vpsrlq ymm5,ymm4,0x20
  2bfa:  add    rdx,rdi
  2bfd:  nop    DWORD PTR [rax]
  2c00:  vmovdqu ymm1,YMMWORD PTR [rax]
  2c04:  add    rax,0x20
  2c08:  vpsrlq ymm0,ymm1,0x20
  2c0d:  vpmuludq ymm2,ymm1,ymm4
  2c11:  vpmuludq ymm0,ymm0,ymm4
  2c15:  vpmuludq ymm1,ymm5,ymm1
  2c19:  vpaddq ymm0,ymm0,ymm1
  2c1d:  vpsllq ymm0,ymm0,0x20
  2c22:  vpaddq ymm0,ymm2,ymm0
  2c26:  vpxor  ymm3,ymm3,ymm0
  2c2a:  cmp    rax,rdx
  2c2d:  jne    2c00 <split_xor_mul+0x40>
  2c2f:  vextracti128 xmm0,ymm3,0x1
  2c35:  vpxor  xmm0,xmm0,xmm3
  2c39:  vpsrldq xmm1,xmm0,0x8
  2c3e:  vpxor  xmm0,xmm0,xmm1
  2c42:  vmovq  rax,xmm0
  2c47:  test   sil,0x3
  2c4b:  je     2cc0 <split_xor_mul+0x100>
  2c4d:  mov    rdx,rsi
  2c50:  and    rdx,0xfffffffffffffffc
  2c54:  vzeroupper
  2c57:  movabs rcx,0x9e3779b97f4a7c15
  2c61:  mov    r8,QWORD PTR [rdi+rdx*8]
  2c65:  imul   r8,rcx
  2c69:  xor    rax,r8
  2c6c:  lea    r8,[rdx+0x1]
  2c70:  cmp    r8,rsi
  2c73:  jae    2cc3 <split_xor_mul+0x103>
  2c75:  mov    r8,QWORD PTR [rdi+rdx*8+0x8]
  2c7a:  imul   r8,rcx
  2c7e:  xor    rax,r8
  2c81:  lea    r8,[rdx+0x2]
  2c85:  cmp    r8,rsi
  2c88:  jae    2cc3 <split_xor_mul+0x103>
  2c8a:  mov    r8,QWORD PTR [rdi+rdx*8+0x10]
  2c8f:  imul   r8,rcx
  2c93:  xor    rax,r8
  2c96:  lea    r8,[rdx+0x3]
  2c9a:  cmp    r8,rsi
  2c9d:  jae    2cc3 <split_xor_mul+0x103>
  2c9f:  mov    r8,QWORD PTR [rdi+rdx*8+0x18]
  2ca4:  imul   r8,rcx
  2ca8:  xor    rax,r8
  2cab:  lea    r8,[rdx+0x4]
  2caf:  cmp    r8,rsi
  2cb2:  jae    2cc3 <split_xor_mul+0x103>
  2cb4:  imul   rcx,QWORD PTR [rdi+rdx*8+0x20]
  2cba:  xor    rax,rcx
  2cbd:  ret
  2cbe:  xchg   ax,ax
  2cc0:  vzeroupper
  2cc3:  ret
  2cc4:  nop    DWORD PTR [rax+0x0]
  2cc8:  xor    eax,eax
  2cca:  ret
  2ccb:  xor    edx,edx
  2ccd:  xor    eax,eax
  2ccf:  jmp    2c57 <split_xor_mul+0x97>
  2cd1:  nop    DWORD PTR [rax+0x0]
  2cd5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
