; split_xor_mul, gcc-scalar, syntaxe Intel (objdump -M intel)
  2ba0:  endbr64
  2ba4:  test   rsi,rsi
  2ba7:  je     2bd8 <split_xor_mul+0x38>
  2ba9:  movabs rcx,0x9e3779b97f4a7c15
  2bb3:  lea    rsi,[rdi+rsi*8]
  2bb7:  xor    eax,eax
  2bb9:  nop    DWORD PTR [rax+0x0]
  2bc0:  mov    rdx,QWORD PTR [rdi]
  2bc3:  add    rdi,0x8
  2bc7:  imul   rdx,rcx
  2bcb:  xor    rax,rdx
  2bce:  cmp    rdi,rsi
  2bd1:  jne    2bc0 <split_xor_mul+0x20>
  2bd3:  ret
  2bd4:  nop    DWORD PTR [rax+0x0]
  2bd8:  xor    eax,eax
  2bda:  ret
  2bdb:  nop    DWORD PTR [rax+rax*1+0x0]
