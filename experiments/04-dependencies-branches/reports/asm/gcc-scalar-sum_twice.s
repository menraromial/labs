; sum_twice, gcc-scalar, syntaxe Intel (objdump -M intel)
  2c90:  endbr64
  2c94:  test   rsi,rsi
  2c97:  je     2cd0 <sum_twice+0x40>
  2c99:  lea    rcx,[rdi+rsi*8]
  2c9d:  mov    rdx,rdi
  2ca0:  xor    eax,eax
  2ca2:  nop    DWORD PTR [rax]
  2ca5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2cb0:  add    rax,QWORD PTR [rdx]
  2cb3:  add    rdx,0x8
  2cb7:  cmp    rdx,rcx
  2cba:  jne    2cb0 <sum_twice+0x20>
  2cbc:  nop    DWORD PTR [rax+0x0]
  2cc0:  add    rax,QWORD PTR [rdi]
  2cc3:  add    rdi,0x8
  2cc7:  cmp    rdi,rcx
  2cca:  jne    2cc0 <sum_twice+0x30>
  2ccc:  ret
  2ccd:  nop    DWORD PTR [rax]
  2cd0:  xor    eax,eax
  2cd2:  ret
  2cd3:  xchg   ax,ax
  2cd5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
