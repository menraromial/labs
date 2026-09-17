; sum_discarded, gcc -O0, syntaxe Intel (objdump -M intel)
  24d9:  endbr64
  24dd:  push   rbp
  24de:  mov    rbp,rsp
  24e1:  mov    QWORD PTR [rbp-0x18],rdi
  24e5:  mov    QWORD PTR [rbp-0x20],rsi
  24e9:  mov    QWORD PTR [rbp-0x10],0x0
  24f1:  mov    QWORD PTR [rbp-0x8],0x0
  24f9:  jmp    251a <sum_discarded+0x41>
  24fb:  mov    rax,QWORD PTR [rbp-0x8]
  24ff:  lea    rdx,[rax*8+0x0]
  2507:  mov    rax,QWORD PTR [rbp-0x18]
  250b:  add    rax,rdx
  250e:  mov    rax,QWORD PTR [rax]
  2511:  add    QWORD PTR [rbp-0x10],rax
  2515:  add    QWORD PTR [rbp-0x8],0x1
  251a:  mov    rax,QWORD PTR [rbp-0x8]
  251e:  cmp    rax,QWORD PTR [rbp-0x20]
  2522:  jb     24fb <sum_discarded+0x22>
  2524:  mov    eax,0x0
  2529:  pop    rbp
  252a:  ret
