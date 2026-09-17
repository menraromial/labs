; chain_xor_mul, gcc-scalar, syntaxe Intel (objdump -M intel)
  2b60:  endbr64
  2b64:  test   rsi,rsi
  2b67:  je     2b98 <chain_xor_mul+0x38>
  2b69:  movabs rdx,0x9e3779b97f4a7c15
  2b73:  lea    rcx,[rdi+rsi*8]
  2b77:  xor    eax,eax
  2b79:  nop    DWORD PTR [rax+0x0]
  2b80:  xor    rax,QWORD PTR [rdi]
  2b83:  add    rdi,0x8
  2b87:  imul   rax,rdx
  2b8b:  cmp    rdi,rcx
  2b8e:  jne    2b80 <chain_xor_mul+0x20>
  2b90:  ret
  2b91:  nop    DWORD PTR [rax+0x0]
  2b98:  xor    eax,eax
  2b9a:  ret
  2b9b:  nop    DWORD PTR [rax+rax*1+0x0]
