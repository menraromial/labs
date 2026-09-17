; sum_indices, gcc -O2, syntaxe Intel (objdump -M intel)
  24a0:  endbr64
  24a4:  test   rsi,rsi
  24a7:  je     24d8 <sum_indices+0x38>
  24a9:  xor    eax,eax
  24ab:  xor    edx,edx
  24ad:  test   sil,0x1
  24b1:  je     24c0 <sum_indices+0x20>
  24b3:  mov    eax,0x1
  24b8:  cmp    rsi,0x1
  24bc:  je     24ce <sum_indices+0x2e>
  24be:  xchg   ax,ax
  24c0:  lea    rdx,[rdx+rax*2+0x1]
  24c5:  add    rax,0x2
  24c9:  cmp    rsi,rax
  24cc:  jne    24c0 <sum_indices+0x20>
  24ce:  mov    rax,rdx
  24d1:  ret
  24d2:  nop    WORD PTR [rax+rax*1+0x0]
  24d8:  xor    edx,edx
  24da:  mov    rax,rdx
  24dd:  ret
