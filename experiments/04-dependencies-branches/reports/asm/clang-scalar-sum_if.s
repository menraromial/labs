; sum_if, clang-scalar, syntaxe Intel (objdump -M intel)
  2d60:  test   rsi,rsi
  2d63:  je     2d7f <sum_if+0x1f>
  2d65:  mov    ecx,esi
  2d67:  and    ecx,0x3
  2d6a:  cmp    rsi,0x4
  2d6e:  jae    2d82 <sum_if+0x22>
  2d70:  xor    r8d,r8d
  2d73:  xor    eax,eax
  2d75:  test   rcx,rcx
  2d78:  jne    2dda <sum_if+0x7a>
  2d7a:  jmp    2dfc <sum_if+0x9c>
  2d7f:  xor    eax,eax
  2d81:  ret
  2d82:  push   rbx
  2d83:  and    rsi,0xfffffffffffffffc
  2d87:  xor    r9d,r9d
  2d8a:  xor    r8d,r8d
  2d8d:  xor    eax,eax
  2d8f:  nop
  2d90:  mov    r10,QWORD PTR [rdi+r8*8]
  2d94:  mov    r11,QWORD PTR [rdi+r8*8+0x8]
  2d99:  cmp    r10,rdx
  2d9c:  cmovb  r10,r9
  2da0:  add    r10,rax
  2da3:  cmp    r11,rdx
  2da6:  cmovb  r11,r9
  2daa:  mov    rbx,QWORD PTR [rdi+r8*8+0x10]
  2daf:  cmp    rbx,rdx
  2db2:  cmovb  rbx,r9
  2db6:  add    rbx,r11
  2db9:  add    rbx,r10
  2dbc:  mov    rax,QWORD PTR [rdi+r8*8+0x18]
  2dc1:  cmp    rax,rdx
  2dc4:  cmovb  rax,r9
  2dc8:  add    rax,rbx
  2dcb:  add    r8,0x4
  2dcf:  cmp    rsi,r8
  2dd2:  jne    2d90 <sum_if+0x30>
  2dd4:  pop    rbx
  2dd5:  test   rcx,rcx
  2dd8:  je     2dfc <sum_if+0x9c>
  2dda:  lea    rsi,[rdi+r8*8]
  2dde:  xor    edi,edi
  2de0:  mov    r8,QWORD PTR [rsi+rdi*8]
  2de4:  cmp    r8,rdx
  2de7:  mov    r9d,0x0
  2ded:  cmovae r9,r8
  2df1:  add    rax,r9
  2df4:  inc    rdi
  2df7:  cmp    rcx,rdi
  2dfa:  jne    2de0 <sum_if+0x80>
  2dfc:  ret
  2dfd:  nop    DWORD PTR [rax]
