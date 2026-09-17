; filter_copy, clang-O3-v3, syntaxe Intel (objdump -M intel)
  3210:  test   rsi,rsi
  3213:  je     325b <filter_copy+0x4b>
  3215:  mov    r8d,esi
  3218:  and    r8d,0x3
  321c:  cmp    rsi,0x4
  3220:  jae    325e <filter_copy+0x4e>
  3222:  xor    r9d,r9d
  3225:  xor    eax,eax
  3227:  test   r8,r8
  322a:  je     325a <filter_copy+0x4a>
  322c:  lea    rsi,[rdi+r9*8]
  3230:  xor    edi,edi
  3232:  jmp    3248 <filter_copy+0x38>
  3234:  data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  3240:  inc    rdi
  3243:  cmp    r8,rdi
  3246:  je     325a <filter_copy+0x4a>
  3248:  mov    r9,QWORD PTR [rsi+rdi*8]
  324c:  cmp    r9,rdx
  324f:  jb     3240 <filter_copy+0x30>
  3251:  mov    QWORD PTR [rcx+rax*8],r9
  3255:  inc    rax
  3258:  jmp    3240 <filter_copy+0x30>
  325a:  ret
  325b:  xor    eax,eax
  325d:  ret
  325e:  and    rsi,0xfffffffffffffffc
  3262:  xor    r9d,r9d
  3265:  xor    eax,eax
  3267:  jmp    3279 <filter_copy+0x69>
  3269:  nop    DWORD PTR [rax+0x0]
  3270:  add    r9,0x4
  3274:  cmp    rsi,r9
  3277:  je     3227 <filter_copy+0x17>
  3279:  mov    r10,QWORD PTR [rdi+r9*8]
  327d:  cmp    r10,rdx
  3280:  jae    32b0 <filter_copy+0xa0>
  3282:  mov    r10,QWORD PTR [rdi+r9*8+0x8]
  3287:  cmp    r10,rdx
  328a:  jae    32c1 <filter_copy+0xb1>
  328c:  mov    r10,QWORD PTR [rdi+r9*8+0x10]
  3291:  cmp    r10,rdx
  3294:  jae    32d2 <filter_copy+0xc2>
  3296:  mov    r10,QWORD PTR [rdi+r9*8+0x18]
  329b:  cmp    r10,rdx
  329e:  jb     3270 <filter_copy+0x60>
  32a0:  jmp    32e3 <filter_copy+0xd3>
  32a2:  data16 data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  32b0:  mov    QWORD PTR [rcx+rax*8],r10
  32b4:  inc    rax
  32b7:  mov    r10,QWORD PTR [rdi+r9*8+0x8]
  32bc:  cmp    r10,rdx
  32bf:  jb     328c <filter_copy+0x7c>
  32c1:  mov    QWORD PTR [rcx+rax*8],r10
  32c5:  inc    rax
  32c8:  mov    r10,QWORD PTR [rdi+r9*8+0x10]
  32cd:  cmp    r10,rdx
  32d0:  jb     3296 <filter_copy+0x86>
  32d2:  mov    QWORD PTR [rcx+rax*8],r10
  32d6:  inc    rax
  32d9:  mov    r10,QWORD PTR [rdi+r9*8+0x18]
  32de:  cmp    r10,rdx
  32e1:  jb     3270 <filter_copy+0x60>
  32e3:  mov    QWORD PTR [rcx+rax*8],r10
  32e7:  inc    rax
  32ea:  jmp    3270 <filter_copy+0x60>
  32ec:  nop    DWORD PTR [rax+0x0]
