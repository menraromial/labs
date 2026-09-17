; filter_copy, gcc-scalar, syntaxe Intel (objdump -M intel)
  2d30:  endbr64
  2d34:  mov    rax,rsi
  2d37:  mov    r8,rcx
  2d3a:  mov    rsi,rdx
  2d3d:  test   rax,rax
  2d40:  je     2d80 <filter_copy+0x50>
  2d42:  lea    rcx,[rdi+rax*8]
  2d46:  xor    edx,edx
  2d48:  xchg   ax,ax
  2d4a:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2d55:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2d60:  mov    rax,QWORD PTR [rdi]
  2d63:  cmp    rax,rsi
  2d66:  jb     2d70 <filter_copy+0x40>
  2d68:  mov    QWORD PTR [r8+rdx*8],rax
  2d6c:  add    rdx,0x1
  2d70:  add    rdi,0x8
  2d74:  cmp    rdi,rcx
  2d77:  jne    2d60 <filter_copy+0x30>
  2d79:  mov    rax,rdx
  2d7c:  ret
  2d7d:  nop    DWORD PTR [rax]
  2d80:  xor    edx,edx
  2d82:  mov    rax,rdx
  2d85:  ret
  2d86:  cs nop WORD PTR [rax+rax*1+0x0]
