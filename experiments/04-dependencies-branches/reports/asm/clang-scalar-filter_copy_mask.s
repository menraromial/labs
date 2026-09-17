; filter_copy_mask, clang-scalar, syntaxe Intel (objdump -M intel)
  2e70:  test   rsi,rsi
  2e73:  je     2e82 <filter_copy_mask+0x12>
  2e75:  cmp    rsi,0x1
  2e79:  jne    2e85 <filter_copy_mask+0x15>
  2e7b:  xor    r8d,r8d
  2e7e:  xor    eax,eax
  2e80:  jmp    2ec8 <filter_copy_mask+0x58>
  2e82:  xor    eax,eax
  2e84:  ret
  2e85:  mov    r9,rsi
  2e88:  and    r9,0xfffffffffffffffe
  2e8c:  xor    r8d,r8d
  2e8f:  xor    eax,eax
  2e91:  data16 data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  2ea0:  mov    r10,QWORD PTR [rdi+r8*8]
  2ea4:  mov    QWORD PTR [rcx+rax*8],r10
  2ea8:  cmp    r10,rdx
  2eab:  sbb    rax,0xffffffffffffffff
  2eaf:  mov    r10,QWORD PTR [rdi+r8*8+0x8]
  2eb4:  mov    QWORD PTR [rcx+rax*8],r10
  2eb8:  cmp    r10,rdx
  2ebb:  sbb    rax,0xffffffffffffffff
  2ebf:  add    r8,0x2
  2ec3:  cmp    r9,r8
  2ec6:  jne    2ea0 <filter_copy_mask+0x30>
  2ec8:  test   sil,0x1
  2ecc:  je     2edd <filter_copy_mask+0x6d>
  2ece:  mov    rsi,QWORD PTR [rdi+r8*8]
  2ed2:  mov    QWORD PTR [rcx+rax*8],rsi
  2ed6:  cmp    rsi,rdx
  2ed9:  sbb    rax,0xffffffffffffffff
  2edd:  ret
