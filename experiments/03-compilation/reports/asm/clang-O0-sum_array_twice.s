; sum_array_twice, clang -O0, syntaxe Intel (objdump -M intel)
  2320:  push   rbp
  2321:  mov    rbp,rsp
  2324:  mov    QWORD PTR [rbp-0x8],rdi
  2328:  mov    QWORD PTR [rbp-0x10],rsi
  232c:  mov    QWORD PTR [rbp-0x18],0x0
  2334:  mov    QWORD PTR [rbp-0x20],0x0
  233c:  mov    rax,QWORD PTR [rbp-0x20]
  2340:  cmp    rax,QWORD PTR [rbp-0x10]
  2344:  jae    2368 <sum_array_twice+0x48>
  2346:  mov    rax,QWORD PTR [rbp-0x8]
  234a:  mov    rcx,QWORD PTR [rbp-0x20]
  234e:  mov    rax,QWORD PTR [rax+rcx*8]
  2352:  add    rax,QWORD PTR [rbp-0x18]
  2356:  mov    QWORD PTR [rbp-0x18],rax
  235a:  mov    rax,QWORD PTR [rbp-0x20]
  235e:  add    rax,0x1
  2362:  mov    QWORD PTR [rbp-0x20],rax
  2366:  jmp    233c <sum_array_twice+0x1c>
  2368:  mov    QWORD PTR [rbp-0x28],0x0
  2370:  mov    rax,QWORD PTR [rbp-0x28]
  2374:  cmp    rax,QWORD PTR [rbp-0x10]
  2378:  jae    239c <sum_array_twice+0x7c>
  237a:  mov    rax,QWORD PTR [rbp-0x8]
  237e:  mov    rcx,QWORD PTR [rbp-0x28]
  2382:  mov    rax,QWORD PTR [rax+rcx*8]
  2386:  add    rax,QWORD PTR [rbp-0x18]
  238a:  mov    QWORD PTR [rbp-0x18],rax
  238e:  mov    rax,QWORD PTR [rbp-0x28]
  2392:  add    rax,0x1
  2396:  mov    QWORD PTR [rbp-0x28],rax
  239a:  jmp    2370 <sum_array_twice+0x50>
  239c:  mov    rax,QWORD PTR [rbp-0x18]
  23a0:  pop    rbp
  23a1:  ret
  23a2:  data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
