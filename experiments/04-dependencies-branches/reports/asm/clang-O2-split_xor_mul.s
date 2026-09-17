; split_xor_mul, clang-O2, syntaxe Intel (objdump -M intel)
  2aa0:  test   rsi,rsi
  2aa3:  je     2ab4 <split_xor_mul+0x14>
  2aa5:  cmp    rsi,0x4
  2aa9:  jae    2ab7 <split_xor_mul+0x17>
  2aab:  xor    ecx,ecx
  2aad:  xor    eax,eax
  2aaf:  jmp    2b5f <split_xor_mul+0xbf>
  2ab4:  xor    eax,eax
  2ab6:  ret
  2ab7:  mov    rcx,rsi
  2aba:  and    rcx,0xfffffffffffffffc
  2abe:  pxor   xmm0,xmm0
  2ac2:  xor    eax,eax
  2ac4:  movdqa xmm2,XMMWORD PTR [rip+0xaf4]        # 35c0 <SMALL_SIZES+0x560>
  2acc:  movdqa xmm3,XMMWORD PTR [rip+0xafc]        # 35d0 <SMALL_SIZES+0x570>
  2ad4:  pxor   xmm1,xmm1
  2ad8:  nop    DWORD PTR [rax+rax*1+0x0]
  2ae0:  movdqu xmm4,XMMWORD PTR [rdi+rax*8]
  2ae5:  movdqu xmm5,XMMWORD PTR [rdi+rax*8+0x10]
  2aeb:  movdqa xmm6,xmm4
  2aef:  pmuludq xmm6,xmm2
  2af3:  movdqa xmm7,xmm4
  2af7:  psrlq  xmm7,0x20
  2afc:  pmuludq xmm7,xmm3
  2b00:  paddq  xmm7,xmm6
  2b04:  psllq  xmm7,0x20
  2b09:  pmuludq xmm4,xmm3
  2b0d:  paddq  xmm4,xmm7
  2b11:  pxor   xmm0,xmm4
  2b15:  movdqa xmm4,xmm5
  2b19:  pmuludq xmm4,xmm2
  2b1d:  movdqa xmm6,xmm5
  2b21:  psrlq  xmm6,0x20
  2b26:  pmuludq xmm6,xmm3
  2b2a:  paddq  xmm6,xmm4
  2b2e:  psllq  xmm6,0x20
  2b33:  pmuludq xmm5,xmm3
  2b37:  paddq  xmm5,xmm6
  2b3b:  pxor   xmm1,xmm5
  2b3f:  add    rax,0x4
  2b43:  cmp    rcx,rax
  2b46:  jne    2ae0 <split_xor_mul+0x40>
  2b48:  pxor   xmm1,xmm0
  2b4c:  pshufd xmm0,xmm1,0xee
  2b51:  pxor   xmm0,xmm1
  2b55:  movq   rax,xmm0
  2b5a:  cmp    rsi,rcx
  2b5d:  je     2b83 <split_xor_mul+0xe3>
  2b5f:  movabs rdx,0x9e3779b97f4a7c15
  2b69:  nop    DWORD PTR [rax+0x0]
  2b70:  mov    r8,QWORD PTR [rdi+rcx*8]
  2b74:  imul   r8,rdx
  2b78:  xor    rax,r8
  2b7b:  inc    rcx
  2b7e:  cmp    rsi,rcx
  2b81:  jne    2b70 <split_xor_mul+0xd0>
  2b83:  ret
  2b84:  data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
