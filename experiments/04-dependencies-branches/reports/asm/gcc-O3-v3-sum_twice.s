; sum_twice, gcc-O3-v3, syntaxe Intel (objdump -M intel)
  2e50:  endbr64
  2e54:  test   rsi,rsi
  2e57:  je     2f90 <sum_twice+0x140>
  2e5d:  lea    rax,[rsi-0x1]
  2e61:  cmp    rax,0x2
  2e65:  jbe    2f96 <sum_twice+0x146>
  2e6b:  mov    rdx,rsi
  2e6e:  mov    rax,rdi
  2e71:  vpxor  xmm0,xmm0,xmm0
  2e75:  shr    rdx,0x2
  2e79:  shl    rdx,0x5
  2e7d:  add    rdx,rdi
  2e80:  vpaddq ymm0,ymm0,YMMWORD PTR [rax]
  2e84:  add    rax,0x20
  2e88:  cmp    rdx,rax
  2e8b:  jne    2e80 <sum_twice+0x30>
  2e8d:  vextracti128 xmm2,ymm0,0x1
  2e93:  vpaddq xmm2,xmm2,xmm0
  2e97:  vpsrldq xmm0,xmm2,0x8
  2e9c:  vpaddq xmm2,xmm2,xmm0
  2ea0:  test   sil,0x3
  2ea4:  je     2edc <sum_twice+0x8c>
  2ea6:  mov    rax,rsi
  2ea9:  and    rax,0xfffffffffffffffc
  2ead:  vmovq  xmm0,QWORD PTR [rdi+rax*8]
  2eb2:  lea    rdx,[rax+0x1]
  2eb6:  vpaddq xmm2,xmm2,xmm0
  2eba:  cmp    rdx,rsi
  2ebd:  jae    2edc <sum_twice+0x8c>
  2ebf:  vmovq  xmm0,QWORD PTR [rdi+rax*8+0x8]
  2ec5:  lea    rdx,[rax+0x2]
  2ec9:  vpaddq xmm2,xmm2,xmm0
  2ecd:  cmp    rdx,rsi
  2ed0:  jae    2edc <sum_twice+0x8c>
  2ed2:  vmovq  xmm0,QWORD PTR [rdi+rax*8+0x10]
  2ed8:  vpaddq xmm2,xmm2,xmm0
  2edc:  mov    rdx,rsi
  2edf:  mov    rax,rdi
  2ee2:  vpxor  xmm0,xmm0,xmm0
  2ee6:  shr    rdx,0x2
  2eea:  shl    rdx,0x5
  2eee:  add    rdx,rdi
  2ef1:  nop    DWORD PTR [rax+0x0]
  2ef5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2f00:  vpaddq ymm0,ymm0,YMMWORD PTR [rax]
  2f04:  add    rax,0x20
  2f08:  cmp    rax,rdx
  2f0b:  jne    2f00 <sum_twice+0xb0>
  2f0d:  vextracti128 xmm1,ymm0,0x1
  2f13:  vpaddq xmm0,xmm1,xmm0
  2f17:  vpsrldq xmm1,xmm0,0x8
  2f1c:  vpaddq xmm0,xmm0,xmm1
  2f20:  vpaddq xmm0,xmm0,xmm2
  2f24:  vmovq  rdx,xmm0
  2f29:  test   sil,0x3
  2f2d:  je     2f88 <sum_twice+0x138>
  2f2f:  mov    rax,rsi
  2f32:  and    rax,0xfffffffffffffffc
  2f36:  vmovq  xmm1,QWORD PTR [rdi+rax*8]
  2f3b:  lea    r8,[rax+0x1]
  2f3f:  lea    rcx,[rax*8+0x0]
  2f47:  vpaddq xmm0,xmm0,xmm1
  2f4b:  vmovq  rdx,xmm0
  2f50:  cmp    r8,rsi
  2f53:  jae    2f88 <sum_twice+0x138>
  2f55:  vzeroupper
  2f58:  vmovq  xmm1,QWORD PTR [rdi+rcx*1+0x8]
  2f5e:  add    rax,0x2
  2f62:  vpaddq xmm0,xmm0,xmm1
  2f66:  vmovq  rdx,xmm0
  2f6b:  cmp    rax,rsi
  2f6e:  jae    2f7f <sum_twice+0x12f>
  2f70:  vmovq  xmm1,QWORD PTR [rdi+rcx*1+0x10]
  2f76:  vpaddq xmm0,xmm0,xmm1
  2f7a:  vmovq  rdx,xmm0
  2f7f:  mov    rax,rdx
  2f82:  ret
  2f83:  nop    DWORD PTR [rax+rax*1+0x0]
  2f88:  mov    rax,rdx
  2f8b:  vzeroupper
  2f8e:  ret
  2f8f:  nop
  2f90:  xor    edx,edx
  2f92:  mov    rax,rdx
  2f95:  ret
  2f96:  vmovq  xmm0,QWORD PTR [rdi]
  2f9a:  cmp    rsi,0x1
  2f9e:  je     2fc2 <sum_twice+0x172>
  2fa0:  vmovq  xmm1,QWORD PTR [rdi+0x8]
  2fa5:  vpaddq xmm1,xmm0,xmm1
  2fa9:  cmp    rsi,0x3
  2fad:  jne    2fb8 <sum_twice+0x168>
  2faf:  vmovq  xmm2,QWORD PTR [rdi+0x10]
  2fb4:  vpaddq xmm1,xmm1,xmm2
  2fb8:  vpaddq xmm0,xmm1,xmm0
  2fbc:  xor    eax,eax
  2fbe:  xor    ecx,ecx
  2fc0:  jmp    2f58 <sum_twice+0x108>
  2fc2:  vpsllq xmm0,xmm0,0x1
  2fc7:  vmovq  rdx,xmm0
  2fcc:  jmp    2f7f <sum_twice+0x12f>
  2fce:  xchg   ax,ax
