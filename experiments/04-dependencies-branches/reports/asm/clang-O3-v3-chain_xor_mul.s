; chain_xor_mul, clang-O3-v3, syntaxe Intel (objdump -M intel)
  2a10:  test   rsi,rsi
  2a13:  je     2a31 <chain_xor_mul+0x21>
  2a15:  movabs rcx,0x9e3779b97f4a7c15
  2a1f:  mov    edx,esi
  2a21:  and    edx,0x7
  2a24:  cmp    rsi,0x8
  2a28:  jae    2a34 <chain_xor_mul+0x24>
  2a2a:  xor    r8d,r8d
  2a2d:  xor    eax,eax
  2a2f:  jmp    2a90 <chain_xor_mul+0x80>
  2a31:  xor    eax,eax
  2a33:  ret
  2a34:  and    rsi,0xfffffffffffffff8
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
  2a63:  xor    rax,QWORD PTR [rdi+r8*8+0x20]
  2a68:  imul   rax,rcx
  2a6c:  xor    rax,QWORD PTR [rdi+r8*8+0x28]
  2a71:  imul   rax,rcx
  2a75:  xor    rax,QWORD PTR [rdi+r8*8+0x30]
  2a7a:  imul   rax,rcx
  2a7e:  xor    rax,QWORD PTR [rdi+r8*8+0x38]
  2a83:  imul   rax,rcx
  2a87:  add    r8,0x8
  2a8b:  cmp    rsi,r8
  2a8e:  jne    2a40 <chain_xor_mul+0x30>
  2a90:  test   rdx,rdx
  2a93:  je     2ab0 <chain_xor_mul+0xa0>
  2a95:  lea    rsi,[rdi+r8*8]
  2a99:  xor    edi,edi
  2a9b:  nop    DWORD PTR [rax+rax*1+0x0]
  2aa0:  xor    rax,QWORD PTR [rsi+rdi*8]
  2aa4:  imul   rax,rcx
  2aa8:  inc    rdi
  2aab:  cmp    rdx,rdi
  2aae:  jne    2aa0 <chain_xor_mul+0x90>
  2ab0:  ret
  2ab1:  data16 data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
