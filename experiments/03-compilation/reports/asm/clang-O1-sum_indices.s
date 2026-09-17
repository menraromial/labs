; sum_indices, clang -O1, syntaxe Intel (objdump -M intel)
  2340:  test   rsi,rsi
  2343:  je     235d <sum_indices+0x1d>
  2345:  lea    rax,[rsi-0x1]
  2349:  lea    rcx,[rsi-0x2]
  234d:  mul    rcx
  2350:  shld   rdx,rax,0x3f
  2355:  lea    rax,[rsi+rdx*1]
  2359:  dec    rax
  235c:  ret
  235d:  xor    eax,eax
  235f:  ret
