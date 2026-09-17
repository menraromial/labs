; sum_array_twice, clang -O1, syntaxe Intel (objdump -M intel)
  22f0:  test   rsi,rsi
  22f3:  je     2313 <sum_array_twice+0x23>
  22f5:  xor    ecx,ecx
  22f7:  xor    eax,eax
  22f9:  nop    DWORD PTR [rax+0x0]
  2300:  add    rax,QWORD PTR [rdi+rcx*8]
  2304:  inc    rcx
  2307:  cmp    rsi,rcx
  230a:  jne    2300 <sum_array_twice+0x10>
  230c:  test   rsi,rsi
  230f:  jne    231a <sum_array_twice+0x2a>
  2311:  jmp    232c <sum_array_twice+0x3c>
  2313:  xor    eax,eax
  2315:  test   rsi,rsi
  2318:  je     232c <sum_array_twice+0x3c>
  231a:  xor    ecx,ecx
  231c:  nop    DWORD PTR [rax+0x0]
  2320:  add    rax,QWORD PTR [rdi+rcx*8]
  2324:  inc    rcx
  2327:  cmp    rsi,rcx
  232a:  jne    2320 <sum_array_twice+0x30>
  232c:  ret
  232d:  nop    DWORD PTR [rax]
