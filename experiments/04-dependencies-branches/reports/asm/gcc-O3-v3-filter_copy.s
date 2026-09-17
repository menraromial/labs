; filter_copy, gcc-O3-v3, syntaxe Intel (objdump -M intel)
  30f0:  endbr64
  30f4:  mov    rax,rsi
  30f7:  mov    r8,rcx
  30fa:  mov    rsi,rdx
  30fd:  test   rax,rax
  3100:  je     3140 <filter_copy+0x50>
  3102:  lea    rcx,[rdi+rax*8]
  3106:  xor    edx,edx
  3108:  xchg   ax,ax
  310a:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  3115:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  3120:  mov    rax,QWORD PTR [rdi]
  3123:  cmp    rax,rsi
  3126:  jb     3130 <filter_copy+0x40>
  3128:  mov    QWORD PTR [r8+rdx*8],rax
  312c:  add    rdx,0x1
  3130:  add    rdi,0x8
  3134:  cmp    rcx,rdi
  3137:  jne    3120 <filter_copy+0x30>
  3139:  mov    rax,rdx
  313c:  ret
  313d:  nop    DWORD PTR [rax]
  3140:  xor    edx,edx
  3142:  mov    rax,rdx
  3145:  ret
  3146:  cs nop WORD PTR [rax+rax*1+0x0]
