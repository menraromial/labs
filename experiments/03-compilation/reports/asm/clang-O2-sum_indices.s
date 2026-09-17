; sum_indices, clang -O2, syntaxe Intel (objdump -M intel)
  2420:  test   rsi,rsi
  2423:  je     243d <sum_indices+0x1d>
  2425:  lea    rax,[rsi-0x1]
  2429:  lea    rcx,[rsi-0x2]
  242d:  mul    rcx
  2430:  shld   rdx,rax,0x3f
  2435:  lea    rax,[rsi+rdx*1]
  2439:  dec    rax
  243c:  ret
  243d:  xor    eax,eax
  243f:  ret
