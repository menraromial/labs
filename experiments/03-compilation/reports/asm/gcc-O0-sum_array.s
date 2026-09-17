; sum_array, gcc -O0, syntaxe Intel (objdump -M intel)
  2404:  endbr64
  2408:  push   rbp
  2409:  mov    rbp,rsp
  240c:  mov    QWORD PTR [rbp-0x18],rdi
  2410:  mov    QWORD PTR [rbp-0x20],rsi
  2414:  mov    QWORD PTR [rbp-0x10],0x0
  241c:  mov    QWORD PTR [rbp-0x8],0x0
  2424:  jmp    2445 <sum_array+0x41>
  2426:  mov    rax,QWORD PTR [rbp-0x8]
  242a:  lea    rdx,[rax*8+0x0]
  2432:  mov    rax,QWORD PTR [rbp-0x18]
  2436:  add    rax,rdx
  2439:  mov    rax,QWORD PTR [rax]
  243c:  add    QWORD PTR [rbp-0x10],rax
  2440:  add    QWORD PTR [rbp-0x8],0x1
  2445:  mov    rax,QWORD PTR [rbp-0x8]
  2449:  cmp    rax,QWORD PTR [rbp-0x20]
  244d:  jb     2426 <sum_array+0x22>
  244f:  mov    rax,QWORD PTR [rbp-0x10]
  2453:  pop    rbp
  2454:  ret
