; sum_array_twice, gcc -O1, syntaxe Intel (objdump -M intel)
  2441:  endbr64
  2445:  test   rsi,rsi
  2448:  je     247d <sum_array_twice+0x3c>
  244a:  mov    rdx,rdi
  244d:  lea    rcx,[rdi+rsi*8]
  2451:  mov    eax,0x0
  2456:  cs nop WORD PTR [rax+rax*1+0x0]
  2460:  add    rax,QWORD PTR [rdi]
  2463:  add    rdi,0x8
  2467:  cmp    rdi,rcx
  246a:  jne    2460 <sum_array_twice+0x1f>
  246c:  nop    DWORD PTR [rax+0x0]
  2470:  add    rax,QWORD PTR [rdx]
  2473:  add    rdx,0x8
  2477:  cmp    rdx,rcx
  247a:  jne    2470 <sum_array_twice+0x2f>
  247c:  ret
  247d:  mov    rax,rsi
  2480:  ret
