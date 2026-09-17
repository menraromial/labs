; filter_copy_mask, clang-O2, syntaxe Intel (objdump -M intel)
  2eb0:  test   rsi,rsi
  2eb3:  je     2ec2 <filter_copy_mask+0x12>
  2eb5:  cmp    rsi,0x1
  2eb9:  jne    2ec5 <filter_copy_mask+0x15>
  2ebb:  xor    r8d,r8d
  2ebe:  xor    eax,eax
  2ec0:  jmp    2f08 <filter_copy_mask+0x58>
  2ec2:  xor    eax,eax
  2ec4:  ret
  2ec5:  mov    r9,rsi
  2ec8:  and    r9,0xfffffffffffffffe
  2ecc:  xor    r8d,r8d
  2ecf:  xor    eax,eax
  2ed1:  data16 data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  2ee0:  mov    r10,QWORD PTR [rdi+r8*8]
  2ee4:  mov    QWORD PTR [rcx+rax*8],r10
  2ee8:  cmp    r10,rdx
  2eeb:  sbb    rax,0xffffffffffffffff
  2eef:  mov    r10,QWORD PTR [rdi+r8*8+0x8]
  2ef4:  mov    QWORD PTR [rcx+rax*8],r10
  2ef8:  cmp    r10,rdx
  2efb:  sbb    rax,0xffffffffffffffff
  2eff:  add    r8,0x2
  2f03:  cmp    r9,r8
  2f06:  jne    2ee0 <filter_copy_mask+0x30>
  2f08:  test   sil,0x1
  2f0c:  je     2f1d <filter_copy_mask+0x6d>
  2f0e:  mov    rsi,QWORD PTR [rdi+r8*8]
  2f12:  mov    QWORD PTR [rcx+rax*8],rsi
  2f16:  cmp    rsi,rdx
  2f19:  sbb    rax,0xffffffffffffffff
  2f1d:  ret
