; filter_copy_mask, gcc-O3-v3, syntaxe Intel (objdump -M intel)
  3150:  endbr64
  3154:  mov    rax,rsi
  3157:  mov    rsi,rdx
  315a:  test   rax,rax
  315d:  je     31a0 <filter_copy_mask+0x50>
  315f:  lea    r8,[rdi+rax*8]
  3163:  xor    eax,eax
  3165:  nop    DWORD PTR [rax+rax*1+0x0]
  316a:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  3175:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  3180:  mov    rdx,QWORD PTR [rdi]
  3183:  cmp    rdx,rsi
  3186:  mov    QWORD PTR [rcx+rax*8],rdx
  318a:  sbb    rax,0xffffffffffffffff
  318e:  add    rdi,0x8
  3192:  cmp    r8,rdi
  3195:  jne    3180 <filter_copy_mask+0x30>
  3197:  ret
  3198:  nop    DWORD PTR [rax+rax*1+0x0]
  31a0:  xor    eax,eax
  31a2:  ret
