; sum_if, clang-O2, syntaxe Intel (objdump -M intel)
  2da0:  test   rsi,rsi
  2da3:  je     2dbf <sum_if+0x1f>
  2da5:  mov    ecx,esi
  2da7:  and    ecx,0x3
  2daa:  cmp    rsi,0x4
  2dae:  jae    2dc2 <sum_if+0x22>
  2db0:  xor    r8d,r8d
  2db3:  xor    eax,eax
  2db5:  test   rcx,rcx
  2db8:  jne    2e1a <sum_if+0x7a>
  2dba:  jmp    2e3c <sum_if+0x9c>
  2dbf:  xor    eax,eax
  2dc1:  ret
  2dc2:  push   rbx
  2dc3:  and    rsi,0xfffffffffffffffc
  2dc7:  xor    r9d,r9d
  2dca:  xor    r8d,r8d
  2dcd:  xor    eax,eax
  2dcf:  nop
  2dd0:  mov    r10,QWORD PTR [rdi+r8*8]
  2dd4:  mov    r11,QWORD PTR [rdi+r8*8+0x8]
  2dd9:  cmp    r10,rdx
  2ddc:  cmovb  r10,r9
  2de0:  add    r10,rax
  2de3:  cmp    r11,rdx
  2de6:  cmovb  r11,r9
  2dea:  mov    rbx,QWORD PTR [rdi+r8*8+0x10]
  2def:  cmp    rbx,rdx
  2df2:  cmovb  rbx,r9
  2df6:  add    rbx,r11
  2df9:  add    rbx,r10
  2dfc:  mov    rax,QWORD PTR [rdi+r8*8+0x18]
  2e01:  cmp    rax,rdx
  2e04:  cmovb  rax,r9
  2e08:  add    rax,rbx
  2e0b:  add    r8,0x4
  2e0f:  cmp    rsi,r8
  2e12:  jne    2dd0 <sum_if+0x30>
  2e14:  pop    rbx
  2e15:  test   rcx,rcx
  2e18:  je     2e3c <sum_if+0x9c>
  2e1a:  lea    rsi,[rdi+r8*8]
  2e1e:  xor    edi,edi
  2e20:  mov    r8,QWORD PTR [rsi+rdi*8]
  2e24:  cmp    r8,rdx
  2e27:  mov    r9d,0x0
  2e2d:  cmovae r9,r8
  2e31:  add    rax,r9
  2e34:  inc    rdi
  2e37:  cmp    rcx,rdi
  2e3a:  jne    2e20 <sum_if+0x80>
  2e3c:  ret
  2e3d:  nop    DWORD PTR [rax]
