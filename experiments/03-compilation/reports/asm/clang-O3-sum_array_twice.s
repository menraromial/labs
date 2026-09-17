; sum_array_twice, clang -O3, syntaxe Intel (objdump -M intel)
  2340:  test   rsi,rsi
  2343:  je     2351 <sum_array_twice+0x11>
  2345:  cmp    rsi,0x4
  2349:  jae    2354 <sum_array_twice+0x14>
  234b:  xor    ecx,ecx
  234d:  xor    eax,eax
  234f:  jmp    23a0 <sum_array_twice+0x60>
  2351:  xor    eax,eax
  2353:  ret
  2354:  mov    rcx,rsi
  2357:  and    rcx,0xfffffffffffffffc
  235b:  pxor   xmm0,xmm0
  235f:  xor    eax,eax
  2361:  pxor   xmm1,xmm1
  2365:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2370:  movdqu xmm2,XMMWORD PTR [rdi+rax*8]
  2375:  paddq  xmm0,xmm2
  2379:  movdqu xmm2,XMMWORD PTR [rdi+rax*8+0x10]
  237f:  paddq  xmm1,xmm2
  2383:  add    rax,0x4
  2387:  cmp    rcx,rax
  238a:  jne    2370 <sum_array_twice+0x30>
  238c:  paddq  xmm1,xmm0
  2390:  pshufd xmm0,xmm1,0xee
  2395:  paddq  xmm0,xmm1
  2399:  movq   rax,xmm0
  239e:  jmp    23a7 <sum_array_twice+0x67>
  23a0:  add    rax,QWORD PTR [rdi+rcx*8]
  23a4:  inc    rcx
  23a7:  cmp    rsi,rcx
  23aa:  jne    23a0 <sum_array_twice+0x60>
  23ac:  cmp    rsi,0x4
  23b0:  jae    23b6 <sum_array_twice+0x76>
  23b2:  xor    ecx,ecx
  23b4:  jmp    2400 <sum_array_twice+0xc0>
  23b6:  mov    rcx,rsi
  23b9:  and    rcx,0xfffffffffffffffc
  23bd:  movq   xmm1,rax
  23c2:  pxor   xmm0,xmm0
  23c6:  xor    eax,eax
  23c8:  nop    DWORD PTR [rax+rax*1+0x0]
  23d0:  movdqu xmm2,XMMWORD PTR [rdi+rax*8]
  23d5:  paddq  xmm1,xmm2
  23d9:  movdqu xmm2,XMMWORD PTR [rdi+rax*8+0x10]
  23df:  paddq  xmm0,xmm2
  23e3:  add    rax,0x4
  23e7:  cmp    rcx,rax
  23ea:  jne    23d0 <sum_array_twice+0x90>
  23ec:  paddq  xmm0,xmm1
  23f0:  pshufd xmm1,xmm0,0xee
  23f5:  paddq  xmm1,xmm0
  23f9:  movq   rax,xmm1
  23fe:  jmp    2407 <sum_array_twice+0xc7>
  2400:  add    rax,QWORD PTR [rdi+rcx*8]
  2404:  inc    rcx
  2407:  cmp    rsi,rcx
  240a:  jne    2400 <sum_array_twice+0xc0>
  240c:  ret
  240d:  nop    DWORD PTR [rax]
