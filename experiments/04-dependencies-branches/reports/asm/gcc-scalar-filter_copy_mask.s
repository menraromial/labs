; filter_copy_mask, gcc-scalar, syntaxe Intel (objdump -M intel)
  2d90:  endbr64
  2d94:  mov    rax,rsi
  2d97:  mov    rsi,rdx
  2d9a:  test   rax,rax
  2d9d:  je     2de0 <filter_copy_mask+0x50>
  2d9f:  lea    r8,[rdi+rax*8]
  2da3:  xor    eax,eax
  2da5:  nop    DWORD PTR [rax+rax*1+0x0]
  2daa:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2db5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2dc0:  mov    rdx,QWORD PTR [rdi]
  2dc3:  cmp    rdx,rsi
  2dc6:  mov    QWORD PTR [rcx+rax*8],rdx
  2dca:  sbb    rax,0xffffffffffffffff
  2dce:  add    rdi,0x8
  2dd2:  cmp    r8,rdi
  2dd5:  jne    2dc0 <filter_copy_mask+0x30>
  2dd7:  ret
  2dd8:  nop    DWORD PTR [rax+rax*1+0x0]
  2de0:  xor    eax,eax
  2de2:  ret
