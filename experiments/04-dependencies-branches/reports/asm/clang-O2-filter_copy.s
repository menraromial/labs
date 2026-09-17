; filter_copy, clang-O2, syntaxe Intel (objdump -M intel)
  2e40:  test   rsi,rsi
  2e43:  je     2e67 <filter_copy+0x27>
  2e45:  cmp    rsi,0x1
  2e49:  jne    2e6a <filter_copy+0x2a>
  2e4b:  xor    r8d,r8d
  2e4e:  xor    eax,eax
  2e50:  test   sil,0x1
  2e54:  je     2e66 <filter_copy+0x26>
  2e56:  mov    rsi,QWORD PTR [rdi+r8*8]
  2e5a:  cmp    rsi,rdx
  2e5d:  jb     2e66 <filter_copy+0x26>
  2e5f:  mov    QWORD PTR [rcx+rax*8],rsi
  2e63:  inc    rax
  2e66:  ret
  2e67:  xor    eax,eax
  2e69:  ret
  2e6a:  mov    r9,rsi
  2e6d:  and    r9,0xfffffffffffffffe
  2e71:  xor    r8d,r8d
  2e74:  xor    eax,eax
  2e76:  jmp    2e89 <filter_copy+0x49>
  2e78:  nop    DWORD PTR [rax+rax*1+0x0]
  2e80:  add    r8,0x2
  2e84:  cmp    r9,r8
  2e87:  je     2e50 <filter_copy+0x10>
  2e89:  mov    r10,QWORD PTR [rdi+r8*8]
  2e8d:  cmp    r10,rdx
  2e90:  jb     2e99 <filter_copy+0x59>
  2e92:  mov    QWORD PTR [rcx+rax*8],r10
  2e96:  inc    rax
  2e99:  mov    r10,QWORD PTR [rdi+r8*8+0x8]
  2e9e:  cmp    r10,rdx
  2ea1:  jb     2e80 <filter_copy+0x40>
  2ea3:  mov    QWORD PTR [rcx+rax*8],r10
  2ea7:  inc    rax
  2eaa:  jmp    2e80 <filter_copy+0x40>
  2eac:  nop    DWORD PTR [rax+0x0]
