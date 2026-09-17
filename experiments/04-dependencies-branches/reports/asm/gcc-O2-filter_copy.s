; filter_copy, gcc-O2, syntaxe Intel (objdump -M intel)
  2d70:  endbr64
  2d74:  mov    rax,rsi
  2d77:  mov    r8,rcx
  2d7a:  mov    rsi,rdx
  2d7d:  test   rax,rax
  2d80:  je     2dc0 <filter_copy+0x50>
  2d82:  lea    rcx,[rdi+rax*8]
  2d86:  xor    edx,edx
  2d88:  xchg   ax,ax
  2d8a:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2d95:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2da0:  mov    rax,QWORD PTR [rdi]
  2da3:  cmp    rax,rsi
  2da6:  jb     2db0 <filter_copy+0x40>
  2da8:  mov    QWORD PTR [r8+rdx*8],rax
  2dac:  add    rdx,0x1
  2db0:  add    rdi,0x8
  2db4:  cmp    rdi,rcx
  2db7:  jne    2da0 <filter_copy+0x30>
  2db9:  mov    rax,rdx
  2dbc:  ret
  2dbd:  nop    DWORD PTR [rax]
  2dc0:  xor    edx,edx
  2dc2:  mov    rax,rdx
  2dc5:  ret
  2dc6:  cs nop WORD PTR [rax+rax*1+0x0]
