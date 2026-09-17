; filter_copy, clang-scalar, syntaxe Intel (objdump -M intel)
  2e00:  test   rsi,rsi
  2e03:  je     2e27 <filter_copy+0x27>
  2e05:  cmp    rsi,0x1
  2e09:  jne    2e2a <filter_copy+0x2a>
  2e0b:  xor    r8d,r8d
  2e0e:  xor    eax,eax
  2e10:  test   sil,0x1
  2e14:  je     2e26 <filter_copy+0x26>
  2e16:  mov    rsi,QWORD PTR [rdi+r8*8]
  2e1a:  cmp    rsi,rdx
  2e1d:  jb     2e26 <filter_copy+0x26>
  2e1f:  mov    QWORD PTR [rcx+rax*8],rsi
  2e23:  inc    rax
  2e26:  ret
  2e27:  xor    eax,eax
  2e29:  ret
  2e2a:  mov    r9,rsi
  2e2d:  and    r9,0xfffffffffffffffe
  2e31:  xor    r8d,r8d
  2e34:  xor    eax,eax
  2e36:  jmp    2e49 <filter_copy+0x49>
  2e38:  nop    DWORD PTR [rax+rax*1+0x0]
  2e40:  add    r8,0x2
  2e44:  cmp    r9,r8
  2e47:  je     2e10 <filter_copy+0x10>
  2e49:  mov    r10,QWORD PTR [rdi+r8*8]
  2e4d:  cmp    r10,rdx
  2e50:  jb     2e59 <filter_copy+0x59>
  2e52:  mov    QWORD PTR [rcx+rax*8],r10
  2e56:  inc    rax
  2e59:  mov    r10,QWORD PTR [rdi+r8*8+0x8]
  2e5e:  cmp    r10,rdx
  2e61:  jb     2e40 <filter_copy+0x40>
  2e63:  mov    QWORD PTR [rcx+rax*8],r10
  2e67:  inc    rax
  2e6a:  jmp    2e40 <filter_copy+0x40>
  2e6c:  nop    DWORD PTR [rax+0x0]
