; sum_array_twice, gcc -O2, syntaxe Intel (objdump -M intel)
  2440:  endbr64
  2444:  test   rsi,rsi
  2447:  je     2480 <sum_array_twice+0x40>
  2449:  lea    rcx,[rdi+rsi*8]
  244d:  mov    rdx,rdi
  2450:  xor    eax,eax
  2452:  nop    DWORD PTR [rax]
  2455:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2460:  add    rax,QWORD PTR [rdx]
  2463:  add    rdx,0x8
  2467:  cmp    rdx,rcx
  246a:  jne    2460 <sum_array_twice+0x20>
  246c:  nop    DWORD PTR [rax+0x0]
  2470:  add    rax,QWORD PTR [rdi]
  2473:  add    rdi,0x8
  2477:  cmp    rdi,rcx
  247a:  jne    2470 <sum_array_twice+0x30>
  247c:  ret
  247d:  nop    DWORD PTR [rax]
  2480:  xor    eax,eax
  2482:  ret
  2483:  xchg   ax,ax
  2485:  data16 cs nop WORD PTR [rax+rax*1+0x0]
