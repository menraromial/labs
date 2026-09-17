; sum_twice, gcc-O2, syntaxe Intel (objdump -M intel)
  2cc0:  endbr64
  2cc4:  test   rsi,rsi
  2cc7:  je     2d00 <sum_twice+0x40>
  2cc9:  lea    rcx,[rdi+rsi*8]
  2ccd:  mov    rdx,rdi
  2cd0:  xor    eax,eax
  2cd2:  nop    DWORD PTR [rax]
  2cd5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2ce0:  add    rax,QWORD PTR [rdx]
  2ce3:  add    rdx,0x8
  2ce7:  cmp    rdx,rcx
  2cea:  jne    2ce0 <sum_twice+0x20>
  2cec:  nop    DWORD PTR [rax+0x0]
  2cf0:  add    rax,QWORD PTR [rdi]
  2cf3:  add    rdi,0x8
  2cf7:  cmp    rdi,rcx
  2cfa:  jne    2cf0 <sum_twice+0x30>
  2cfc:  ret
  2cfd:  nop    DWORD PTR [rax]
  2d00:  xor    eax,eax
  2d02:  ret
  2d03:  xchg   ax,ax
  2d05:  data16 cs nop WORD PTR [rax+rax*1+0x0]
