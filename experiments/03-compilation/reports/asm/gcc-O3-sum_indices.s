; sum_indices, gcc -O3, syntaxe Intel (objdump -M intel)
  2580:  endbr64
  2584:  test   rsi,rsi
  2587:  je     25b8 <sum_indices+0x38>
  2589:  xor    eax,eax
  258b:  xor    edx,edx
  258d:  test   sil,0x1
  2591:  je     25a0 <sum_indices+0x20>
  2593:  mov    eax,0x1
  2598:  cmp    rsi,0x1
  259c:  je     25ae <sum_indices+0x2e>
  259e:  xchg   ax,ax
  25a0:  lea    rdx,[rdx+rax*2+0x1]
  25a5:  add    rax,0x2
  25a9:  cmp    rsi,rax
  25ac:  jne    25a0 <sum_indices+0x20>
  25ae:  mov    rax,rdx
  25b1:  ret
  25b2:  nop    WORD PTR [rax+rax*1+0x0]
  25b8:  xor    edx,edx
  25ba:  mov    rax,rdx
  25bd:  ret
