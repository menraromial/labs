; sum_array, gcc -O1, syntaxe Intel (objdump -M intel)
  2410:  endbr64
  2414:  test   rsi,rsi
  2417:  je     243d <sum_array+0x2d>
  2419:  mov    rdx,rdi
  241c:  lea    rcx,[rdi+rsi*8]
  2420:  mov    eax,0x0
  2425:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2430:  add    rax,QWORD PTR [rdx]
  2433:  add    rdx,0x8
  2437:  cmp    rdx,rcx
  243a:  jne    2430 <sum_array+0x20>
  243c:  ret
  243d:  mov    rax,rsi
  2440:  ret
