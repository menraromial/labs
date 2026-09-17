; sum_if, gcc-O2, syntaxe Intel (objdump -M intel)
  2d10:  endbr64
  2d14:  mov    rax,rsi
  2d17:  mov    rsi,rdx
  2d1a:  test   rax,rax
  2d1d:  je     2d60 <sum_if+0x50>
  2d1f:  lea    r8,[rdi+rax*8]
  2d23:  xor    eax,eax
  2d25:  nop    DWORD PTR [rax+rax*1+0x0]
  2d2a:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2d35:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2d40:  mov    rdx,QWORD PTR [rdi]
  2d43:  cmp    rdx,rsi
  2d46:  lea    rcx,[rax+rdx*1]
  2d4a:  cmovae rax,rcx
  2d4e:  add    rdi,0x8
  2d52:  cmp    r8,rdi
  2d55:  jne    2d40 <sum_if+0x30>
  2d57:  ret
  2d58:  nop    DWORD PTR [rax+rax*1+0x0]
  2d60:  xor    eax,eax
  2d62:  ret
  2d63:  xchg   ax,ax
  2d65:  data16 cs nop WORD PTR [rax+rax*1+0x0]
