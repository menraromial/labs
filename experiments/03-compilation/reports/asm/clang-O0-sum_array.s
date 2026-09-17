; sum_array, clang -O0, syntaxe Intel (objdump -M intel)
  22d0:  push   rbp
  22d1:  mov    rbp,rsp
  22d4:  mov    QWORD PTR [rbp-0x8],rdi
  22d8:  mov    QWORD PTR [rbp-0x10],rsi
  22dc:  mov    QWORD PTR [rbp-0x18],0x0
  22e4:  mov    QWORD PTR [rbp-0x20],0x0
  22ec:  mov    rax,QWORD PTR [rbp-0x20]
  22f0:  cmp    rax,QWORD PTR [rbp-0x10]
  22f4:  jae    2318 <sum_array+0x48>
  22f6:  mov    rax,QWORD PTR [rbp-0x8]
  22fa:  mov    rcx,QWORD PTR [rbp-0x20]
  22fe:  mov    rax,QWORD PTR [rax+rcx*8]
  2302:  add    rax,QWORD PTR [rbp-0x18]
  2306:  mov    QWORD PTR [rbp-0x18],rax
  230a:  mov    rax,QWORD PTR [rbp-0x20]
  230e:  add    rax,0x1
  2312:  mov    QWORD PTR [rbp-0x20],rax
  2316:  jmp    22ec <sum_array+0x1c>
  2318:  mov    rax,QWORD PTR [rbp-0x18]
  231c:  pop    rbp
  231d:  ret
  231e:  xchg   ax,ax
