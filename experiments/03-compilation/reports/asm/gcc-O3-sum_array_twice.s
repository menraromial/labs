; sum_array_twice, gcc -O3, syntaxe Intel (objdump -M intel)
  24b0:  endbr64
  24b4:  test   rsi,rsi
  24b7:  je     2560 <sum_array_twice+0xb0>
  24bd:  cmp    rsi,0x1
  24c1:  je     2563 <sum_array_twice+0xb3>
  24c7:  mov    rcx,rsi
  24ca:  mov    rax,rdi
  24cd:  pxor   xmm0,xmm0
  24d1:  mov    rdx,rdi
  24d4:  shr    rcx,1
  24d7:  shl    rcx,0x4
  24db:  add    rcx,rdi
  24de:  xchg   ax,ax
  24e0:  movdqu xmm3,XMMWORD PTR [rdx]
  24e4:  add    rdx,0x10
  24e8:  paddq  xmm0,xmm3
  24ec:  cmp    rdx,rcx
  24ef:  jne    24e0 <sum_array_twice+0x30>
  24f1:  movdqa xmm1,xmm0
  24f5:  mov    rdx,rsi
  24f8:  psrldq xmm1,0x8
  24fd:  and    rdx,0xfffffffffffffffe
  2501:  paddq  xmm0,xmm1
  2505:  movdqa xmm1,xmm0
  2509:  test   sil,0x1
  250d:  je     2518 <sum_array_twice+0x68>
  250f:  movq   xmm0,QWORD PTR [rdi+rdx*8]
  2514:  paddq  xmm1,xmm0
  2518:  pxor   xmm0,xmm0
  251c:  nop    DWORD PTR [rax+0x0]
  2520:  movdqu xmm4,XMMWORD PTR [rax]
  2524:  add    rax,0x10
  2528:  paddq  xmm0,xmm4
  252c:  cmp    rax,rcx
  252f:  jne    2520 <sum_array_twice+0x70>
  2531:  movdqa xmm2,xmm0
  2535:  and    esi,0x1
  2538:  psrldq xmm2,0x8
  253d:  paddq  xmm0,xmm2
  2541:  paddq  xmm0,xmm1
  2545:  movq   rax,xmm0
  254a:  je     2562 <sum_array_twice+0xb2>
  254c:  movq   xmm1,QWORD PTR [rdi+rdx*8]
  2551:  paddq  xmm0,xmm1
  2555:  movq   rax,xmm0
  255a:  ret
  255b:  nop    DWORD PTR [rax+rax*1+0x0]
  2560:  xor    eax,eax
  2562:  ret
  2563:  movq   xmm0,QWORD PTR [rdi]
  2567:  xor    edx,edx
  2569:  jmp    254c <sum_array_twice+0x9c>
  256b:  nop    DWORD PTR [rax+rax*1+0x0]
