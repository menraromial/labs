; split_xor_mul, clang-O3-v3, syntaxe Intel (objdump -M intel)
  2ac0:  test   rsi,rsi
  2ac3:  je     2ad4 <split_xor_mul+0x14>
  2ac5:  cmp    rsi,0x3
  2ac9:  ja     2ad7 <split_xor_mul+0x17>
  2acb:  xor    ecx,ecx
  2acd:  xor    eax,eax
  2acf:  jmp    2c7d <split_xor_mul+0x1bd>
  2ad4:  xor    eax,eax
  2ad6:  ret
  2ad7:  cmp    rsi,0x10
  2adb:  jae    2ae6 <split_xor_mul+0x26>
  2add:  xor    ecx,ecx
  2adf:  xor    eax,eax
  2ae1:  jmp    2c03 <split_xor_mul+0x143>
  2ae6:  mov    rcx,rsi
  2ae9:  and    rcx,0xfffffffffffffff0
  2aed:  vpxor  xmm0,xmm0,xmm0
  2af1:  xor    eax,eax
  2af3:  vpbroadcastq ymm1,QWORD PTR [rip+0x1acc]        # 45c8 <SMALL_SIZES+0x568>
  2afc:  vpbroadcastq ymm2,QWORD PTR [rip+0x1acb]        # 45d0 <SMALL_SIZES+0x570>
  2b05:  vpxor  xmm3,xmm3,xmm3
  2b09:  vpxor  xmm4,xmm4,xmm4
  2b0d:  vpxor  xmm5,xmm5,xmm5
  2b11:  data16 data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  2b20:  vmovdqu ymm6,YMMWORD PTR [rdi+rax*8]
  2b25:  vmovdqu ymm7,YMMWORD PTR [rdi+rax*8+0x20]
  2b2b:  vmovdqu ymm8,YMMWORD PTR [rdi+rax*8+0x40]
  2b31:  vmovdqu ymm9,YMMWORD PTR [rdi+rax*8+0x60]
  2b37:  vpmuludq ymm10,ymm6,ymm1
  2b3b:  vpsrlq ymm11,ymm6,0x20
  2b40:  vpmuludq ymm11,ymm11,ymm2
  2b44:  vpaddq ymm10,ymm10,ymm11
  2b49:  vpsllq ymm10,ymm10,0x20
  2b4f:  vpmuludq ymm6,ymm6,ymm2
  2b53:  vpaddq ymm6,ymm10,ymm6
  2b57:  vpxor  ymm0,ymm6,ymm0
  2b5b:  vpmuludq ymm6,ymm7,ymm1
  2b5f:  vpsrlq ymm10,ymm7,0x20
  2b64:  vpmuludq ymm10,ymm10,ymm2
  2b68:  vpaddq ymm6,ymm10,ymm6
  2b6c:  vpsllq ymm6,ymm6,0x20
  2b71:  vpmuludq ymm7,ymm7,ymm2
  2b75:  vpaddq ymm6,ymm7,ymm6
  2b79:  vpxor  ymm3,ymm6,ymm3
  2b7d:  vpmuludq ymm6,ymm8,ymm1
  2b81:  vpsrlq ymm7,ymm8,0x20
  2b87:  vpmuludq ymm7,ymm7,ymm2
  2b8b:  vpaddq ymm6,ymm6,ymm7
  2b8f:  vpsllq ymm6,ymm6,0x20
  2b94:  vpmuludq ymm7,ymm8,ymm2
  2b98:  vpaddq ymm6,ymm7,ymm6
  2b9c:  vpxor  ymm4,ymm6,ymm4
  2ba0:  vpmuludq ymm6,ymm9,ymm1
  2ba4:  vpsrlq ymm7,ymm9,0x20
  2baa:  vpmuludq ymm7,ymm7,ymm2
  2bae:  vpaddq ymm6,ymm6,ymm7
  2bb2:  vpsllq ymm6,ymm6,0x20
  2bb7:  vpmuludq ymm7,ymm9,ymm2
  2bbb:  vpaddq ymm6,ymm7,ymm6
  2bbf:  vpxor  ymm5,ymm6,ymm5
  2bc3:  add    rax,0x10
  2bc7:  cmp    rcx,rax
  2bca:  jne    2b20 <split_xor_mul+0x60>
  2bd0:  vpxor  ymm0,ymm3,ymm0
  2bd4:  vpxor  ymm0,ymm4,ymm0
  2bd8:  vpxor  ymm0,ymm5,ymm0
  2bdc:  vextracti128 xmm1,ymm0,0x1
  2be2:  vpxor  xmm0,xmm0,xmm1
  2be6:  vpshufd xmm1,xmm0,0xee
  2beb:  vpxor  xmm0,xmm0,xmm1
  2bef:  vmovq  rax,xmm0
  2bf4:  cmp    rsi,rcx
  2bf7:  je     2ca3 <split_xor_mul+0x1e3>
  2bfd:  test   sil,0xc
  2c01:  je     2c7d <split_xor_mul+0x1bd>
  2c03:  mov    rdx,rcx
  2c06:  mov    rcx,rsi
  2c09:  and    rcx,0xfffffffffffffffc
  2c0d:  vmovq  xmm0,rax
  2c12:  vpbroadcastq ymm1,QWORD PTR [rip+0x19ad]        # 45c8 <SMALL_SIZES+0x568>
  2c1b:  vpbroadcastq ymm2,QWORD PTR [rip+0x19ac]        # 45d0 <SMALL_SIZES+0x570>
  2c24:  data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  2c30:  vmovdqu ymm3,YMMWORD PTR [rdi+rdx*8]
  2c35:  vpmuludq ymm4,ymm3,ymm1
  2c39:  vpsrlq ymm5,ymm3,0x20
  2c3e:  vpmuludq ymm5,ymm5,ymm2
  2c42:  vpaddq ymm4,ymm4,ymm5
  2c46:  vpsllq ymm4,ymm4,0x20
  2c4b:  vpmuludq ymm3,ymm3,ymm2
  2c4f:  vpaddq ymm3,ymm3,ymm4
  2c53:  vpxor  ymm0,ymm3,ymm0
  2c57:  add    rdx,0x4
  2c5b:  cmp    rcx,rdx
  2c5e:  jne    2c30 <split_xor_mul+0x170>
  2c60:  vextracti128 xmm1,ymm0,0x1
  2c66:  vpxor  xmm0,xmm0,xmm1
  2c6a:  vpshufd xmm1,xmm0,0xee
  2c6f:  vpxor  xmm0,xmm0,xmm1
  2c73:  vmovq  rax,xmm0
  2c78:  cmp    rsi,rcx
  2c7b:  je     2ca3 <split_xor_mul+0x1e3>
  2c7d:  movabs rdx,0x9e3779b97f4a7c15
  2c87:  nop    WORD PTR [rax+rax*1+0x0]
  2c90:  mov    r8,QWORD PTR [rdi+rcx*8]
  2c94:  imul   r8,rdx
  2c98:  xor    rax,r8
  2c9b:  inc    rcx
  2c9e:  cmp    rsi,rcx
  2ca1:  jne    2c90 <split_xor_mul+0x1d0>
  2ca3:  vzeroupper
  2ca6:  ret
  2ca7:  nop    WORD PTR [rax+rax*1+0x0]
