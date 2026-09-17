; sum_four, clang-O3-v3, syntaxe Intel (objdump -M intel)
  2d90:  vpxor  xmm0,xmm0,xmm0
  2d94:  cmp    rsi,0x4
  2d98:  jae    2d9e <sum_four+0xe>
  2d9a:  xor    ecx,ecx
  2d9c:  jmp    2db5 <sum_four+0x25>
  2d9e:  xor    eax,eax
  2da0:  vpaddq ymm0,ymm0,YMMWORD PTR [rdi+rax*8]
  2da5:  lea    rcx,[rax+0x4]
  2da9:  add    rax,0x8
  2dad:  cmp    rax,rsi
  2db0:  mov    rax,rcx
  2db3:  jbe    2da0 <sum_four+0x10>
  2db5:  mov    rax,rsi
  2db8:  vmovq  r8,xmm0
  2dbd:  sub    rax,rcx
  2dc0:  jbe    2eac <sum_four+0x11c>
  2dc6:  cmp    rax,0x3
  2dca:  ja     2dd4 <sum_four+0x44>
  2dcc:  mov    rax,rcx
  2dcf:  jmp    2ea0 <sum_four+0x110>
  2dd4:  cmp    rax,0x10
  2dd8:  jae    2dde <sum_four+0x4e>
  2dda:  xor    edx,edx
  2ddc:  jmp    2e51 <sum_four+0xc1>
  2dde:  mov    rdx,rax
  2de1:  and    rdx,0xfffffffffffffff0
  2de5:  vmovq  xmm1,xmm0
  2de9:  lea    r8,[rdi+rcx*8]
  2ded:  add    r8,0x60
  2df1:  vpxor  xmm2,xmm2,xmm2
  2df5:  xor    r9d,r9d
  2df8:  vpxor  xmm3,xmm3,xmm3
  2dfc:  vpxor  xmm4,xmm4,xmm4
  2e00:  vpaddq ymm1,ymm1,YMMWORD PTR [r8+r9*8-0x60]
  2e07:  vpaddq ymm2,ymm2,YMMWORD PTR [r8+r9*8-0x40]
  2e0e:  vpaddq ymm3,ymm3,YMMWORD PTR [r8+r9*8-0x20]
  2e15:  vpaddq ymm4,ymm4,YMMWORD PTR [r8+r9*8]
  2e1b:  add    r9,0x10
  2e1f:  cmp    rdx,r9
  2e22:  jne    2e00 <sum_four+0x70>
  2e24:  vpaddq ymm1,ymm2,ymm1
  2e28:  vpaddq ymm2,ymm4,ymm3
  2e2c:  vpaddq ymm1,ymm2,ymm1
  2e30:  vextracti128 xmm2,ymm1,0x1
  2e36:  vpaddq xmm1,xmm1,xmm2
  2e3a:  vpshufd xmm2,xmm1,0xee
  2e3f:  vpaddq xmm1,xmm1,xmm2
  2e43:  vmovq  r8,xmm1
  2e48:  cmp    rax,rdx
  2e4b:  je     2eac <sum_four+0x11c>
  2e4d:  test   al,0xc
  2e4f:  je     2ecd <sum_four+0x13d>
  2e51:  mov    r9d,esi
  2e54:  and    r9d,0x3
  2e58:  sub    rax,r9
  2e5b:  add    rax,rcx
  2e5e:  vmovq  xmm1,r8
  2e63:  add    rdx,rcx
  2e66:  cs nop WORD PTR [rax+rax*1+0x0]
  2e70:  vpaddq ymm1,ymm1,YMMWORD PTR [rdi+rdx*8]
  2e75:  add    rdx,0x4
  2e79:  cmp    rax,rdx
  2e7c:  jne    2e70 <sum_four+0xe0>
  2e7e:  vextracti128 xmm2,ymm1,0x1
  2e84:  vpaddq xmm1,xmm1,xmm2
  2e88:  vpshufd xmm2,xmm1,0xee
  2e8d:  vpaddq xmm1,xmm1,xmm2
  2e91:  vmovq  r8,xmm1
  2e96:  test   r9,r9
  2e99:  je     2eac <sum_four+0x11c>
  2e9b:  nop    DWORD PTR [rax+rax*1+0x0]
  2ea0:  add    r8,QWORD PTR [rdi+rax*8]
  2ea4:  inc    rax
  2ea7:  cmp    rsi,rax
  2eaa:  jne    2ea0 <sum_four+0x110>
  2eac:  vpermq ymm1,ymm0,0xaa
  2eb2:  vextracti128 xmm2,ymm0,0x1
  2eb8:  vpaddq xmm0,xmm1,xmm0
  2ebc:  vpaddq xmm0,xmm0,xmm2
  2ec0:  vpextrq rax,xmm0,0x1
  2ec6:  add    rax,r8
  2ec9:  vzeroupper
  2ecc:  ret
  2ecd:  add    rcx,rdx
  2ed0:  mov    rax,rcx
  2ed3:  jmp    2ea0 <sum_four+0x110>
  2ed5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
