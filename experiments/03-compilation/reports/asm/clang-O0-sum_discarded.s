; sum_discarded, clang -O0, syntaxe Intel (objdump -M intel)
  23b0:  push   rbp
  23b1:  mov    rbp,rsp
  23b4:  mov    QWORD PTR [rbp-0x8],rdi
  23b8:  mov    QWORD PTR [rbp-0x10],rsi
  23bc:  mov    QWORD PTR [rbp-0x18],0x0
  23c4:  mov    QWORD PTR [rbp-0x20],0x0
  23cc:  mov    rax,QWORD PTR [rbp-0x20]
  23d0:  cmp    rax,QWORD PTR [rbp-0x10]
  23d4:  jae    23f8 <sum_discarded+0x48>
  23d6:  mov    rax,QWORD PTR [rbp-0x8]
  23da:  mov    rcx,QWORD PTR [rbp-0x20]
  23de:  mov    rax,QWORD PTR [rax+rcx*8]
  23e2:  add    rax,QWORD PTR [rbp-0x18]
  23e6:  mov    QWORD PTR [rbp-0x18],rax
  23ea:  mov    rax,QWORD PTR [rbp-0x20]
  23ee:  add    rax,0x1
  23f2:  mov    QWORD PTR [rbp-0x20],rax
  23f6:  jmp    23cc <sum_discarded+0x1c>
  23f8:  xor    eax,eax
  23fa:  pop    rbp
  23fb:  ret
  23fc:  nop    DWORD PTR [rax+0x0]
