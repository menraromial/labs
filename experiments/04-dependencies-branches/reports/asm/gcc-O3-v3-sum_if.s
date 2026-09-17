; sum_if, gcc-O3-v3, syntaxe Intel (objdump -M intel)
  2fd0:  endbr64
  2fd4:  mov    rcx,rdx
  2fd7:  test   rsi,rsi
  2fda:  je     30d8 <sum_if+0x108>
  2fe0:  lea    rax,[rsi-0x1]
  2fe4:  cmp    rax,0x2
  2fe8:  jbe    30db <sum_if+0x10b>
  2fee:  mov    rdx,rsi
  2ff1:  vmovq  xmm6,rcx
  2ff6:  vpxor  xmm2,xmm2,xmm2
  2ffa:  mov    rax,rdi
  2ffd:  vmovdqa ymm4,YMMWORD PTR [rip+0x15fb]        # 4600 <kernel_build+0x30>
  3005:  shr    rdx,0x2
  3009:  vpbroadcastq ymm3,xmm6
  300e:  vmovdqa ymm5,ymm2
  3012:  shl    rdx,0x5
  3016:  add    rdx,rdi
  3019:  vpsubq ymm3,ymm3,ymm4
  301d:  xchg   ax,ax
  301f:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  302a:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  3035:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  3040:  vmovdqu ymm1,YMMWORD PTR [rax]
  3044:  add    rax,0x20
  3048:  vpsubq ymm0,ymm1,ymm4
  304c:  vpcmpgtq ymm0,ymm3,ymm0
  3051:  vpcmpeqq ymm0,ymm0,ymm5
  3056:  vpand  ymm0,ymm0,ymm1
  305a:  vpaddq ymm2,ymm2,ymm0
  305e:  cmp    rdx,rax
  3061:  jne    3040 <sum_if+0x70>
  3063:  vextracti128 xmm0,ymm2,0x1
  3069:  vpaddq xmm0,xmm0,xmm2
  306d:  vpsrldq xmm1,xmm0,0x8
  3072:  vpaddq xmm0,xmm0,xmm1
  3076:  vmovq  rax,xmm0
  307b:  test   sil,0x3
  307f:  je     30d0 <sum_if+0x100>
  3081:  mov    rdx,rsi
  3084:  and    rdx,0xfffffffffffffffc
  3088:  vzeroupper
  308b:  mov    r8,QWORD PTR [rdi+rdx*8]
  308f:  lea    r9,[rax+r8*1]
  3093:  cmp    r8,rcx
  3096:  lea    r8,[rdx+0x1]
  309a:  cmovae rax,r9
  309e:  cmp    r8,rsi
  30a1:  jae    30d3 <sum_if+0x103>
  30a3:  mov    r8,QWORD PTR [rdi+rdx*8+0x8]
  30a8:  lea    r9,[rax+r8*1]
  30ac:  cmp    r8,rcx
  30af:  lea    r8,[rdx+0x2]
  30b3:  cmovae rax,r9
  30b7:  cmp    r8,rsi
  30ba:  jae    30d3 <sum_if+0x103>
  30bc:  mov    rdx,QWORD PTR [rdi+rdx*8+0x10]
  30c1:  lea    rsi,[rax+rdx*1]
  30c5:  cmp    rdx,rcx
  30c8:  cmovae rax,rsi
  30cc:  ret
  30cd:  nop    DWORD PTR [rax]
  30d0:  vzeroupper
  30d3:  ret
  30d4:  nop    DWORD PTR [rax+0x0]
  30d8:  xor    eax,eax
  30da:  ret
  30db:  xor    edx,edx
  30dd:  xor    eax,eax
  30df:  jmp    308b <sum_if+0xbb>
  30e1:  nop    DWORD PTR [rax+0x0]
  30e5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
