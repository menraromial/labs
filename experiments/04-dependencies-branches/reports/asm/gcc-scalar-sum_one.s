; sum_one, gcc-scalar, syntaxe Intel (objdump -M intel)
  2be0:  endbr64
  2be4:  test   rsi,rsi
  2be7:  je     2c00 <sum_one+0x20>
  2be9:  lea    rdx,[rdi+rsi*8]
  2bed:  xor    eax,eax
  2bef:  nop
  2bf0:  add    rax,QWORD PTR [rdi]
  2bf3:  add    rdi,0x8
  2bf7:  cmp    rdi,rdx
  2bfa:  jne    2bf0 <sum_one+0x10>
  2bfc:  ret
  2bfd:  nop    DWORD PTR [rax]
  2c00:  xor    eax,eax
  2c02:  ret
  2c03:  xchg   ax,ax
  2c05:  data16 cs nop WORD PTR [rax+rax*1+0x0]
