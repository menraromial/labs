; sum_array, clang -O1, syntaxe Intel (objdump -M intel)
  22d0:  test   rsi,rsi
  22d3:  je     22ed <sum_array+0x1d>
  22d5:  xor    ecx,ecx
  22d7:  xor    eax,eax
  22d9:  nop    DWORD PTR [rax+0x0]
  22e0:  add    rax,QWORD PTR [rdi+rcx*8]
  22e4:  inc    rcx
  22e7:  cmp    rsi,rcx
  22ea:  jne    22e0 <sum_array+0x10>
  22ec:  ret
  22ed:  xor    eax,eax
  22ef:  ret
