; sum_four, clang-scalar, syntaxe Intel (objdump -M intel)
  2bc0:  cmp    rsi,0x4
  2bc4:  jae    2bd4 <sum_four+0x14>
  2bc6:  xor    ecx,ecx
  2bc8:  xor    r8d,r8d
  2bcb:  xor    eax,eax
  2bcd:  xor    edx,edx
  2bcf:  xor    r9d,r9d
  2bd2:  jmp    2c03 <sum_four+0x43>
  2bd4:  xor    r10d,r10d
  2bd7:  xor    edx,edx
  2bd9:  xor    eax,eax
  2bdb:  xor    r8d,r8d
  2bde:  xor    ecx,ecx
  2be0:  add    rcx,QWORD PTR [rdi+r10*8]
  2be4:  add    r8,QWORD PTR [rdi+r10*8+0x8]
  2be9:  add    rax,QWORD PTR [rdi+r10*8+0x10]
  2bee:  add    rdx,QWORD PTR [rdi+r10*8+0x18]
  2bf3:  lea    r9,[r10+0x4]
  2bf7:  add    r10,0x8
  2bfb:  cmp    r10,rsi
  2bfe:  mov    r10,r9
  2c01:  jbe    2be0 <sum_four+0x20>
  2c03:  mov    r10,r9
  2c06:  sub    r10,rsi
  2c09:  jae    2c70 <sum_four+0xb0>
  2c0b:  mov    r11d,esi
  2c0e:  sub    r11d,r9d
  2c11:  and    r11d,0x7
  2c15:  je     2c2c <sum_four+0x6c>
  2c17:  nop    WORD PTR [rax+rax*1+0x0]
  2c20:  add    rcx,QWORD PTR [rdi+r9*8]
  2c24:  inc    r9
  2c27:  dec    r11
  2c2a:  jne    2c20 <sum_four+0x60>
  2c2c:  cmp    r10,0xfffffffffffffff8
  2c30:  ja     2c70 <sum_four+0xb0>
  2c32:  data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  2c40:  add    rcx,QWORD PTR [rdi+r9*8]
  2c44:  add    rcx,QWORD PTR [rdi+r9*8+0x8]
  2c49:  add    rcx,QWORD PTR [rdi+r9*8+0x10]
  2c4e:  add    rcx,QWORD PTR [rdi+r9*8+0x18]
  2c53:  add    rcx,QWORD PTR [rdi+r9*8+0x20]
  2c58:  add    rcx,QWORD PTR [rdi+r9*8+0x28]
  2c5d:  add    rcx,QWORD PTR [rdi+r9*8+0x30]
  2c62:  add    rcx,QWORD PTR [rdi+r9*8+0x38]
  2c67:  add    r9,0x8
  2c6b:  cmp    rsi,r9
  2c6e:  jne    2c40 <sum_four+0x80>
  2c70:  add    rax,r8
  2c73:  add    rax,rdx
  2c76:  add    rax,rcx
  2c79:  ret
  2c7a:  nop    WORD PTR [rax+rax*1+0x0]
