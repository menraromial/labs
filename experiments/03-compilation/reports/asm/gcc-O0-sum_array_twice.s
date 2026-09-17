; sum_array_twice, gcc -O0, syntaxe Intel (objdump -M intel)
  2455:  endbr64
  2459:  push   rbp
  245a:  mov    rbp,rsp
  245d:  mov    QWORD PTR [rbp-0x28],rdi
  2461:  mov    QWORD PTR [rbp-0x30],rsi
  2465:  mov    QWORD PTR [rbp-0x18],0x0
  246d:  mov    QWORD PTR [rbp-0x10],0x0
  2475:  jmp    2496 <sum_array_twice+0x41>
  2477:  mov    rax,QWORD PTR [rbp-0x10]
  247b:  lea    rdx,[rax*8+0x0]
  2483:  mov    rax,QWORD PTR [rbp-0x28]
  2487:  add    rax,rdx
  248a:  mov    rax,QWORD PTR [rax]
  248d:  add    QWORD PTR [rbp-0x18],rax
  2491:  add    QWORD PTR [rbp-0x10],0x1
  2496:  mov    rax,QWORD PTR [rbp-0x10]
  249a:  cmp    rax,QWORD PTR [rbp-0x30]
  249e:  jb     2477 <sum_array_twice+0x22>
  24a0:  mov    QWORD PTR [rbp-0x8],0x0
  24a8:  jmp    24c9 <sum_array_twice+0x74>
  24aa:  mov    rax,QWORD PTR [rbp-0x8]
  24ae:  lea    rdx,[rax*8+0x0]
  24b6:  mov    rax,QWORD PTR [rbp-0x28]
  24ba:  add    rax,rdx
  24bd:  mov    rax,QWORD PTR [rax]
  24c0:  add    QWORD PTR [rbp-0x18],rax
  24c4:  add    QWORD PTR [rbp-0x8],0x1
  24c9:  mov    rax,QWORD PTR [rbp-0x8]
  24cd:  cmp    rax,QWORD PTR [rbp-0x30]
  24d1:  jb     24aa <sum_array_twice+0x55>
  24d3:  mov    rax,QWORD PTR [rbp-0x18]
  24d7:  pop    rbp
  24d8:  ret
