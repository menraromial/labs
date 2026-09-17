; chain_xor_mul, clang-O2, syntaxe Intel (objdump -M intel)
  2a10:  test   rsi,rsi
  2a13:  je     2a31 <chain_xor_mul+0x21>
  2a15:  movabs rcx,0x9e3779b97f4a7c15
  2a1f:  mov    edx,esi
  2a21:  and    edx,0x3
  2a24:  cmp    rsi,0x4
  2a28:  jae    2a34 <chain_xor_mul+0x24>
  2a2a:  xor    r8d,r8d
  2a2d:  xor    eax,eax
  2a2f:  jmp    2a6c <chain_xor_mul+0x5c>
  2a31:  xor    eax,eax
  2a33:  ret
  2a34:  and    rsi,0xfffffffffffffffc
  2a38:  xor    r8d,r8d
  2a3b:  xor    eax,eax
  2a3d:  nop    DWORD PTR [rax]
  2a40:  xor    rax,QWORD PTR [rdi+r8*8]
  2a44:  imul   rax,rcx
  2a48:  xor    rax,QWORD PTR [rdi+r8*8+0x8]
  2a4d:  imul   rax,rcx
  2a51:  xor    rax,QWORD PTR [rdi+r8*8+0x10]
  2a56:  imul   rax,rcx
  2a5a:  xor    rax,QWORD PTR [rdi+r8*8+0x18]
  2a5f:  imul   rax,rcx
  2a63:  add    r8,0x4
  2a67:  cmp    rsi,r8
  2a6a:  jne    2a40 <chain_xor_mul+0x30>
  2a6c:  test   rdx,rdx
  2a6f:  je     2a90 <chain_xor_mul+0x80>
  2a71:  lea    rsi,[rdi+r8*8]
  2a75:  xor    edi,edi
  2a77:  nop    WORD PTR [rax+rax*1+0x0]
  2a80:  xor    rax,QWORD PTR [rsi+rdi*8]
  2a84:  imul   rax,rcx
  2a88:  inc    rdi
  2a8b:  cmp    rdx,rdi
  2a8e:  jne    2a80 <chain_xor_mul+0x70>
  2a90:  ret
  2a91:  data16 data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
