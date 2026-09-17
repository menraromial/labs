; split_xor_mul, clang-scalar, syntaxe Intel (objdump -M intel)
  2aa0:  test   rsi,rsi
  2aa3:  je     2ac1 <split_xor_mul+0x21>
  2aa5:  movabs rcx,0x9e3779b97f4a7c15
  2aaf:  mov    edx,esi
  2ab1:  and    edx,0x3
  2ab4:  cmp    rsi,0x4
  2ab8:  jae    2ac4 <split_xor_mul+0x24>
  2aba:  xor    r8d,r8d
  2abd:  xor    eax,eax
  2abf:  jmp    2b08 <split_xor_mul+0x68>
  2ac1:  xor    eax,eax
  2ac3:  ret
  2ac4:  and    rsi,0xfffffffffffffffc
  2ac8:  xor    r8d,r8d
  2acb:  xor    eax,eax
  2acd:  nop    DWORD PTR [rax]
  2ad0:  mov    r9,QWORD PTR [rdi+r8*8]
  2ad4:  imul   r9,rcx
  2ad8:  xor    r9,rax
  2adb:  mov    rax,QWORD PTR [rdi+r8*8+0x8]
  2ae0:  imul   rax,rcx
  2ae4:  mov    r10,QWORD PTR [rdi+r8*8+0x10]
  2ae9:  imul   r10,rcx
  2aed:  xor    r10,rax
  2af0:  xor    r10,r9
  2af3:  mov    rax,QWORD PTR [rdi+r8*8+0x18]
  2af8:  imul   rax,rcx
  2afc:  xor    rax,r10
  2aff:  add    r8,0x4
  2b03:  cmp    rsi,r8
  2b06:  jne    2ad0 <split_xor_mul+0x30>
  2b08:  test   rdx,rdx
  2b0b:  je     2b33 <split_xor_mul+0x93>
  2b0d:  lea    rsi,[rdi+r8*8]
  2b11:  xor    edi,edi
  2b13:  data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  2b20:  mov    r8,QWORD PTR [rsi+rdi*8]
  2b24:  imul   r8,rcx
  2b28:  xor    rax,r8
  2b2b:  inc    rdi
  2b2e:  cmp    rdx,rdi
  2b31:  jne    2b20 <split_xor_mul+0x80>
  2b33:  ret
  2b34:  data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
