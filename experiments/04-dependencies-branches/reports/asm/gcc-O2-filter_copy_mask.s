; filter_copy_mask, gcc-O2, syntaxe Intel (objdump -M intel)
  2dd0:  endbr64
  2dd4:  mov    rax,rsi
  2dd7:  mov    rsi,rdx
  2dda:  test   rax,rax
  2ddd:  je     2e20 <filter_copy_mask+0x50>
  2ddf:  lea    r8,[rdi+rax*8]
  2de3:  xor    eax,eax
  2de5:  nop    DWORD PTR [rax+rax*1+0x0]
  2dea:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2df5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2e00:  mov    rdx,QWORD PTR [rdi]
  2e03:  cmp    rdx,rsi
  2e06:  mov    QWORD PTR [rcx+rax*8],rdx
  2e0a:  sbb    rax,0xffffffffffffffff
  2e0e:  add    rdi,0x8
  2e12:  cmp    r8,rdi
  2e15:  jne    2e00 <filter_copy_mask+0x30>
  2e17:  ret
  2e18:  nop    DWORD PTR [rax+rax*1+0x0]
  2e20:  xor    eax,eax
  2e22:  ret
