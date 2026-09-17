; sum_four, gcc-scalar, syntaxe Intel (objdump -M intel)
  2c10:  endbr64
  2c14:  mov    r11,rdi
  2c17:  mov    r10,rsi
  2c1a:  cmp    rsi,0x3
  2c1e:  jbe    2c88 <sum_four+0x78>
  2c20:  lea    r9,[rsi-0x4]
  2c24:  mov    rdx,rdi
  2c27:  xor    esi,esi
  2c29:  xor    ecx,ecx
  2c2b:  mov    rax,r9
  2c2e:  shr    rax,0x2
  2c32:  shl    rax,0x5
  2c36:  lea    r8,[rdi+rax*1+0x20]
  2c3b:  xor    edi,edi
  2c3d:  xor    eax,eax
  2c3f:  nop
  2c40:  add    rax,QWORD PTR [rdx]
  2c43:  add    rcx,QWORD PTR [rdx+0x8]
  2c47:  add    rdx,0x20
  2c4b:  add    rdi,QWORD PTR [rdx-0x10]
  2c4f:  add    rsi,QWORD PTR [rdx-0x8]
  2c53:  cmp    r8,rdx
  2c56:  jne    2c40 <sum_four+0x30>
  2c58:  and    r9,0xfffffffffffffffc
  2c5c:  add    rcx,rdi
  2c5f:  lea    rdx,[r9+0x4]
  2c63:  add    rcx,rsi
  2c66:  cmp    rdx,r10
  2c69:  jae    2c7f <sum_four+0x6f>
  2c6b:  lea    rdx,[r11+rdx*8]
  2c6f:  lea    rsi,[r11+r10*8]
  2c73:  add    rax,QWORD PTR [rdx]
  2c76:  add    rdx,0x8
  2c7a:  cmp    rsi,rdx
  2c7d:  jne    2c73 <sum_four+0x63>
  2c7f:  add    rax,rcx
  2c82:  ret
  2c83:  nop    DWORD PTR [rax+rax*1+0x0]
  2c88:  xor    ecx,ecx
  2c8a:  xor    edx,edx
  2c8c:  xor    eax,eax
  2c8e:  jmp    2c66 <sum_four+0x56>
