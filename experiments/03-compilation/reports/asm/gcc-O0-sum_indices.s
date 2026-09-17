; sum_indices, gcc -O0, syntaxe Intel (objdump -M intel)
  252b:  endbr64
  252f:  push   rbp
  2530:  mov    rbp,rsp
  2533:  mov    QWORD PTR [rbp-0x18],rdi
  2537:  mov    QWORD PTR [rbp-0x20],rsi
  253b:  mov    QWORD PTR [rbp-0x10],0x0
  2543:  mov    QWORD PTR [rbp-0x8],0x0
  254b:  jmp    255a <sum_indices+0x2f>
  254d:  mov    rax,QWORD PTR [rbp-0x8]
  2551:  add    QWORD PTR [rbp-0x10],rax
  2555:  add    QWORD PTR [rbp-0x8],0x1
  255a:  mov    rax,QWORD PTR [rbp-0x8]
  255e:  cmp    rax,QWORD PTR [rbp-0x20]
  2562:  jb     254d <sum_indices+0x22>
  2564:  mov    rax,QWORD PTR [rbp-0x10]
  2568:  pop    rbp
  2569:  ret
