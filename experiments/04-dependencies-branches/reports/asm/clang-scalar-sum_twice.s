; sum_twice, clang-scalar, syntaxe Intel (objdump -M intel)
  2c80:  test   rsi,rsi
  2c83:  je     2c96 <sum_twice+0x16>
  2c85:  mov    ecx,esi
  2c87:  and    ecx,0x7
  2c8a:  cmp    rsi,0x8
  2c8e:  jae    2c99 <sum_twice+0x19>
  2c90:  xor    edx,edx
  2c92:  xor    eax,eax
  2c94:  jmp    2ce0 <sum_twice+0x60>
  2c96:  xor    eax,eax
  2c98:  ret
  2c99:  mov    r8,rsi
  2c9c:  and    r8,0xfffffffffffffff8
  2ca0:  xor    edx,edx
  2ca2:  xor    eax,eax
  2ca4:  data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  2cb0:  add    rax,QWORD PTR [rdi+rdx*8]
  2cb4:  add    rax,QWORD PTR [rdi+rdx*8+0x8]
  2cb9:  add    rax,QWORD PTR [rdi+rdx*8+0x10]
  2cbe:  add    rax,QWORD PTR [rdi+rdx*8+0x18]
  2cc3:  add    rax,QWORD PTR [rdi+rdx*8+0x20]
  2cc8:  add    rax,QWORD PTR [rdi+rdx*8+0x28]
  2ccd:  add    rax,QWORD PTR [rdi+rdx*8+0x30]
  2cd2:  add    rax,QWORD PTR [rdi+rdx*8+0x38]
  2cd7:  add    rdx,0x8
  2cdb:  cmp    r8,rdx
  2cde:  jne    2cb0 <sum_twice+0x30>
  2ce0:  test   rcx,rcx
  2ce3:  je     2cfc <sum_twice+0x7c>
  2ce5:  lea    rdx,[rdi+rdx*8]
  2ce9:  xor    r8d,r8d
  2cec:  nop    DWORD PTR [rax+0x0]
  2cf0:  add    rax,QWORD PTR [rdx+r8*8]
  2cf4:  inc    r8
  2cf7:  cmp    rcx,r8
  2cfa:  jne    2cf0 <sum_twice+0x70>
  2cfc:  cmp    rsi,0x8
  2d00:  jae    2d06 <sum_twice+0x86>
  2d02:  xor    edx,edx
  2d04:  jmp    2d40 <sum_twice+0xc0>
  2d06:  mov    r8,rsi
  2d09:  and    r8,0xfffffffffffffff8
  2d0d:  xor    edx,edx
  2d0f:  nop
  2d10:  add    rax,QWORD PTR [rdi+rdx*8]
  2d14:  add    rax,QWORD PTR [rdi+rdx*8+0x8]
  2d19:  add    rax,QWORD PTR [rdi+rdx*8+0x10]
  2d1e:  add    rax,QWORD PTR [rdi+rdx*8+0x18]
  2d23:  add    rax,QWORD PTR [rdi+rdx*8+0x20]
  2d28:  add    rax,QWORD PTR [rdi+rdx*8+0x28]
  2d2d:  add    rax,QWORD PTR [rdi+rdx*8+0x30]
  2d32:  add    rax,QWORD PTR [rdi+rdx*8+0x38]
  2d37:  add    rdx,0x8
  2d3b:  cmp    r8,rdx
  2d3e:  jne    2d10 <sum_twice+0x90>
  2d40:  test   sil,0x7
  2d44:  je     2d5c <sum_twice+0xdc>
  2d46:  lea    rdx,[rdi+rdx*8]
  2d4a:  xor    esi,esi
  2d4c:  nop    DWORD PTR [rax+0x0]
  2d50:  add    rax,QWORD PTR [rdx+rsi*8]
  2d54:  inc    rsi
  2d57:  cmp    rcx,rsi
  2d5a:  jne    2d50 <sum_twice+0xd0>
  2d5c:  ret
  2d5d:  nop    DWORD PTR [rax]
