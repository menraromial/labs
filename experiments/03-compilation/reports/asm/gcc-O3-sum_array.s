; sum_array, gcc -O3, syntaxe Intel (objdump -M intel)
  2420:  endbr64
  2424:  test   rsi,rsi
  2427:  je     2498 <sum_array+0x78>
  2429:  cmp    rsi,0x1
  242d:  je     249b <sum_array+0x7b>
  242f:  mov    rdx,rsi
  2432:  mov    rax,rdi
  2435:  pxor   xmm0,xmm0
  2439:  shr    rdx,1
  243c:  shl    rdx,0x4
  2440:  add    rdx,rdi
  2443:  nop    DWORD PTR [rax+0x0]
  244a:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2455:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2460:  movdqu xmm2,XMMWORD PTR [rax]
  2464:  add    rax,0x10
  2468:  paddq  xmm0,xmm2
  246c:  cmp    rdx,rax
  246f:  jne    2460 <sum_array+0x40>
  2471:  movdqa xmm1,xmm0
  2475:  psrldq xmm1,0x8
  247a:  paddq  xmm0,xmm1
  247e:  movq   rax,xmm0
  2483:  test   sil,0x1
  2487:  je     249a <sum_array+0x7a>
  2489:  and    rsi,0xfffffffffffffffe
  248d:  add    rax,QWORD PTR [rdi+rsi*8]
  2491:  ret
  2492:  nop    WORD PTR [rax+rax*1+0x0]
  2498:  xor    eax,eax
  249a:  ret
  249b:  xor    esi,esi
  249d:  xor    eax,eax
  249f:  jmp    248d <sum_array+0x6d>
  24a1:  nop    DWORD PTR [rax+0x0]
  24a5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
