; chain_xor_mul, gcc-O3-v3, syntaxe Intel (objdump -M intel)
  2b80:  endbr64
  2b84:  test   rsi,rsi
  2b87:  je     2bb8 <chain_xor_mul+0x38>
  2b89:  movabs rdx,0x9e3779b97f4a7c15
  2b93:  lea    rcx,[rdi+rsi*8]
  2b97:  xor    eax,eax
  2b99:  nop    DWORD PTR [rax+0x0]
  2ba0:  xor    rax,QWORD PTR [rdi]
  2ba3:  add    rdi,0x8
  2ba7:  imul   rax,rdx
  2bab:  cmp    rcx,rdi
  2bae:  jne    2ba0 <chain_xor_mul+0x20>
  2bb0:  ret
  2bb1:  nop    DWORD PTR [rax+0x0]
  2bb8:  xor    eax,eax
  2bba:  ret
  2bbb:  nop    DWORD PTR [rax+rax*1+0x0]
