; sum_one, clang-scalar, syntaxe Intel (objdump -M intel)
  2b40:  test   rsi,rsi
  2b43:  je     2b56 <sum_one+0x16>
  2b45:  mov    ecx,esi
  2b47:  and    ecx,0x7
  2b4a:  cmp    rsi,0x8
  2b4e:  jae    2b59 <sum_one+0x19>
  2b50:  xor    edx,edx
  2b52:  xor    eax,eax
  2b54:  jmp    2ba0 <sum_one+0x60>
  2b56:  xor    eax,eax
  2b58:  ret
  2b59:  and    rsi,0xfffffffffffffff8
  2b5d:  xor    edx,edx
  2b5f:  xor    eax,eax
  2b61:  data16 data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  2b70:  add    rax,QWORD PTR [rdi+rdx*8]
  2b74:  add    rax,QWORD PTR [rdi+rdx*8+0x8]
  2b79:  add    rax,QWORD PTR [rdi+rdx*8+0x10]
  2b7e:  add    rax,QWORD PTR [rdi+rdx*8+0x18]
  2b83:  add    rax,QWORD PTR [rdi+rdx*8+0x20]
  2b88:  add    rax,QWORD PTR [rdi+rdx*8+0x28]
  2b8d:  add    rax,QWORD PTR [rdi+rdx*8+0x30]
  2b92:  add    rax,QWORD PTR [rdi+rdx*8+0x38]
  2b97:  add    rdx,0x8
  2b9b:  cmp    rsi,rdx
  2b9e:  jne    2b70 <sum_one+0x30>
  2ba0:  test   rcx,rcx
  2ba3:  je     2bbc <sum_one+0x7c>
  2ba5:  lea    rdx,[rdi+rdx*8]
  2ba9:  xor    esi,esi
  2bab:  nop    DWORD PTR [rax+rax*1+0x0]
  2bb0:  add    rax,QWORD PTR [rdx+rsi*8]
  2bb4:  inc    rsi
  2bb7:  cmp    rcx,rsi
  2bba:  jne    2bb0 <sum_one+0x70>
  2bbc:  ret
  2bbd:  nop    DWORD PTR [rax]
