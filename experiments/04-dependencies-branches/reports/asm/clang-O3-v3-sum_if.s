; sum_if, clang-O3-v3, syntaxe Intel (objdump -M intel)
  3090:  test   rsi,rsi
  3093:  je     30a4 <sum_if+0x14>
  3095:  cmp    rsi,0x3
  3099:  ja     30a7 <sum_if+0x17>
  309b:  xor    ecx,ecx
  309d:  xor    eax,eax
  309f:  jmp    31ed <sum_if+0x15d>
  30a4:  xor    eax,eax
  30a6:  ret
  30a7:  vmovq  xmm0,rdx
  30ac:  cmp    rsi,0x10
  30b0:  jae    30bb <sum_if+0x2b>
  30b2:  xor    ecx,ecx
  30b4:  xor    eax,eax
  30b6:  jmp    318a <sum_if+0xfa>
  30bb:  mov    rcx,rsi
  30be:  and    rcx,0xfffffffffffffff0
  30c2:  vpbroadcastq ymm3,xmm0
  30c7:  vpxor  xmm1,xmm1,xmm1
  30cb:  xor    eax,eax
  30cd:  vpbroadcastq ymm2,QWORD PTR [rip+0x1502]        # 45d8 <SMALL_SIZES+0x578>
  30d6:  vpxor  ymm3,ymm3,ymm2
  30da:  vpxor  xmm4,xmm4,xmm4
  30de:  vpxor  xmm5,xmm5,xmm5
  30e2:  vpxor  xmm6,xmm6,xmm6
  30e6:  cs nop WORD PTR [rax+rax*1+0x0]
  30f0:  vmovdqu ymm7,YMMWORD PTR [rdi+rax*8]
  30f5:  vmovdqu ymm8,YMMWORD PTR [rdi+rax*8+0x20]
  30fb:  vmovdqu ymm9,YMMWORD PTR [rdi+rax*8+0x40]
  3101:  vmovdqu ymm10,YMMWORD PTR [rdi+rax*8+0x60]
  3107:  vpxor  ymm11,ymm7,ymm2
  310b:  vpcmpgtq ymm11,ymm3,ymm11
  3110:  vpandn ymm7,ymm11,ymm7
  3114:  vpaddq ymm1,ymm7,ymm1
  3118:  vpxor  ymm7,ymm8,ymm2
  311c:  vpcmpgtq ymm7,ymm3,ymm7
  3121:  vpandn ymm7,ymm7,ymm8
  3126:  vpaddq ymm4,ymm7,ymm4
  312a:  vpxor  ymm7,ymm9,ymm2
  312e:  vpcmpgtq ymm7,ymm3,ymm7
  3133:  vpandn ymm7,ymm7,ymm9
  3138:  vpaddq ymm5,ymm7,ymm5
  313c:  vpxor  ymm7,ymm10,ymm2
  3140:  vpcmpgtq ymm7,ymm3,ymm7
  3145:  vpandn ymm7,ymm7,ymm10
  314a:  vpaddq ymm6,ymm7,ymm6
  314e:  add    rax,0x10
  3152:  cmp    rcx,rax
  3155:  jne    30f0 <sum_if+0x60>
  3157:  vpaddq ymm1,ymm4,ymm1
  315b:  vpaddq ymm1,ymm5,ymm1
  315f:  vpaddq ymm1,ymm6,ymm1
  3163:  vextracti128 xmm2,ymm1,0x1
  3169:  vpaddq xmm1,xmm1,xmm2
  316d:  vpshufd xmm2,xmm1,0xee
  3172:  vpaddq xmm1,xmm1,xmm2
  3176:  vmovq  rax,xmm1
  317b:  cmp    rsi,rcx
  317e:  je     3206 <sum_if+0x176>
  3184:  test   sil,0xc
  3188:  je     31ed <sum_if+0x15d>
  318a:  mov    r8,rcx
  318d:  mov    rcx,rsi
  3190:  and    rcx,0xfffffffffffffffc
  3194:  vmovq  xmm1,rax
  3199:  vpbroadcastq ymm2,xmm0
  319e:  vpbroadcastq ymm0,QWORD PTR [rip+0x1431]        # 45d8 <SMALL_SIZES+0x578>
  31a7:  vpxor  ymm2,ymm2,ymm0
  31ab:  nop    DWORD PTR [rax+rax*1+0x0]
  31b0:  vmovdqu ymm3,YMMWORD PTR [rdi+r8*8]
  31b6:  vpxor  ymm4,ymm3,ymm0
  31ba:  vpcmpgtq ymm4,ymm2,ymm4
  31bf:  vpandn ymm3,ymm4,ymm3
  31c3:  vpaddq ymm1,ymm3,ymm1
  31c7:  add    r8,0x4
  31cb:  cmp    rcx,r8
  31ce:  jne    31b0 <sum_if+0x120>
  31d0:  vextracti128 xmm0,ymm1,0x1
  31d6:  vpaddq xmm0,xmm1,xmm0
  31da:  vpshufd xmm1,xmm0,0xee
  31df:  vpaddq xmm0,xmm0,xmm1
  31e3:  vmovq  rax,xmm0
  31e8:  cmp    rsi,rcx
  31eb:  je     3206 <sum_if+0x176>
  31ed:  xor    r8d,r8d
  31f0:  mov    r9,QWORD PTR [rdi+rcx*8]
  31f4:  cmp    r9,rdx
  31f7:  cmovb  r9,r8
  31fb:  add    rax,r9
  31fe:  inc    rcx
  3201:  cmp    rsi,rcx
  3204:  jne    31f0 <sum_if+0x160>
  3206:  vzeroupper
  3209:  ret
  320a:  nop    WORD PTR [rax+rax*1+0x0]
