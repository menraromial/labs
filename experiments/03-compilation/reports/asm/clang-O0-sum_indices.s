; sum_indices, clang -O0, syntaxe Intel (objdump -M intel)
  2400:  push   rbp
  2401:  mov    rbp,rsp
  2404:  mov    QWORD PTR [rbp-0x8],rdi
  2408:  mov    QWORD PTR [rbp-0x10],rsi
  240c:  mov    QWORD PTR [rbp-0x18],0x0
  2414:  mov    QWORD PTR [rbp-0x20],0x0
  241c:  mov    rax,QWORD PTR [rbp-0x20]
  2420:  cmp    rax,QWORD PTR [rbp-0x10]
  2424:  jae    2440 <sum_indices+0x40>
  2426:  mov    rax,QWORD PTR [rbp-0x20]
  242a:  add    rax,QWORD PTR [rbp-0x18]
  242e:  mov    QWORD PTR [rbp-0x18],rax
  2432:  mov    rax,QWORD PTR [rbp-0x20]
  2436:  add    rax,0x1
  243a:  mov    QWORD PTR [rbp-0x20],rax
  243e:  jmp    241c <sum_indices+0x1c>
  2440:  mov    rax,QWORD PTR [rbp-0x18]
  2444:  pop    rbp
  2445:  ret
