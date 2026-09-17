; sum_array, gcc -O2, syntaxe Intel (objdump -M intel)
  2410:  endbr64
  2414:  test   rsi,rsi
  2417:  je     2430 <sum_array+0x20>
  2419:  lea    rdx,[rdi+rsi*8]
  241d:  xor    eax,eax
  241f:  nop
  2420:  add    rax,QWORD PTR [rdi]
  2423:  add    rdi,0x8
  2427:  cmp    rdi,rdx
  242a:  jne    2420 <sum_array+0x10>
  242c:  ret
  242d:  nop    DWORD PTR [rax]
  2430:  xor    eax,eax
  2432:  ret
  2433:  xchg   ax,ax
  2435:  data16 cs nop WORD PTR [rax+rax*1+0x0]
