; sum_indices, gcc -O1, syntaxe Intel (objdump -M intel)
  249f:  endbr64
  24a3:  test   rsi,rsi
  24a6:  je     24d0 <sum_indices+0x31>
  24a8:  mov    eax,0x0
  24ad:  mov    edx,0x0
  24b2:  nop    DWORD PTR [rax]
  24b5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  24c0:  add    rdx,rax
  24c3:  add    rax,0x1
  24c7:  cmp    rsi,rax
  24ca:  jne    24c0 <sum_indices+0x21>
  24cc:  mov    rax,rdx
  24cf:  ret
  24d0:  mov    rdx,rsi
  24d3:  jmp    24cc <sum_indices+0x2d>
