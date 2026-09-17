; sum_if, gcc-scalar, syntaxe Intel (objdump -M intel)
  2ce0:  endbr64
  2ce4:  mov    rcx,rdx
  2ce7:  test   rsi,rsi
  2cea:  je     2d20 <sum_if+0x40>
  2cec:  lea    rsi,[rdi+rsi*8]
  2cf0:  xor    edx,edx
  2cf2:  nop    DWORD PTR [rax]
  2cf5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2d00:  mov    rax,QWORD PTR [rdi]
  2d03:  cmp    rax,rcx
  2d06:  jb     2d0b <sum_if+0x2b>
  2d08:  add    rdx,rax
  2d0b:  add    rdi,0x8
  2d0f:  cmp    rdi,rsi
  2d12:  jne    2d00 <sum_if+0x20>
  2d14:  mov    rax,rdx
  2d17:  ret
  2d18:  nop    DWORD PTR [rax+rax*1+0x0]
  2d20:  xor    edx,edx
  2d22:  mov    rax,rdx
  2d25:  ret
  2d26:  cs nop WORD PTR [rax+rax*1+0x0]
