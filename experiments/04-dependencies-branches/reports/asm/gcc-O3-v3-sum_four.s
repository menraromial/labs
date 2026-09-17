; sum_four, gcc-O3-v3, syntaxe Intel (objdump -M intel)
  2d90:  endbr64
  2d94:  mov    r8,rsi
  2d97:  cmp    rsi,0x3
  2d9b:  jbe    2e40 <sum_four+0xb0>
  2da1:  lea    rsi,[rsi-0x4]
  2da5:  xor    eax,eax
  2da7:  vpxor  xmm0,xmm0,xmm0
  2dab:  mov    rcx,rsi
  2dae:  shr    rcx,0x2
  2db2:  add    rcx,0x1
  2db6:  cs nop WORD PTR [rax+rax*1+0x0]
  2dc0:  mov    rdx,rax
  2dc3:  add    rax,0x1
  2dc7:  shl    rdx,0x5
  2dcb:  vpaddq ymm0,ymm0,YMMWORD PTR [rdi+rdx*1]
  2dd0:  cmp    rax,rcx
  2dd3:  jb     2dc0 <sum_four+0x30>
  2dd5:  vmovdqa xmm3,xmm0
  2dd9:  vmovdqa xmm1,xmm0
  2ddd:  vextracti128 xmm0,ymm0,0x1
  2de3:  and    rsi,0xfffffffffffffffc
  2de7:  vpsrldq xmm3,xmm3,0x8
  2dec:  lea    rax,[rsi+0x4]
  2df0:  vpaddq xmm2,xmm0,xmm3
  2df4:  vpsrldq xmm0,xmm0,0x8
  2df9:  vpaddq xmm0,xmm2,xmm0
  2dfd:  vzeroupper
  2e00:  cmp    rax,r8
  2e03:  jae    2e34 <sum_four+0xa4>
  2e05:  vmovq  xmm2,QWORD PTR [rdi+rax*8]
  2e0a:  lea    rdx,[rax+0x1]
  2e0e:  vpaddq xmm1,xmm1,xmm2
  2e12:  cmp    rdx,r8
  2e15:  jae    2e34 <sum_four+0xa4>
  2e17:  vmovq  xmm2,QWORD PTR [rdi+rax*8+0x8]
  2e1d:  lea    rdx,[rax+0x2]
  2e21:  vpaddq xmm1,xmm1,xmm2
  2e25:  cmp    rdx,r8
  2e28:  jae    2e34 <sum_four+0xa4>
  2e2a:  vmovq  xmm2,QWORD PTR [rdi+rax*8+0x10]
  2e30:  vpaddq xmm1,xmm1,xmm2
  2e34:  vpaddq xmm1,xmm1,xmm0
  2e38:  vmovq  rax,xmm1
  2e3d:  ret
  2e3e:  xchg   ax,ax
  2e40:  vpxor  xmm0,xmm0,xmm0
  2e44:  xor    eax,eax
  2e46:  vmovdqa xmm1,xmm0
  2e4a:  jmp    2e00 <sum_four+0x70>
  2e4c:  nop    DWORD PTR [rax+0x0]
