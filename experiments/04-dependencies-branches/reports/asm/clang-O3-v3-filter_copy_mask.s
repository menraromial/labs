; filter_copy_mask, clang-O3-v3, syntaxe Intel (objdump -M intel)
  32f0:  test   rsi,rsi
  32f3:  je     3309 <filter_copy_mask+0x19>
  32f5:  mov    r8d,esi
  32f8:  and    r8d,0x3
  32fc:  cmp    rsi,0x4
  3300:  jae    330c <filter_copy_mask+0x1c>
  3302:  xor    r9d,r9d
  3305:  xor    eax,eax
  3307:  jmp    3368 <filter_copy_mask+0x78>
  3309:  xor    eax,eax
  330b:  ret
  330c:  and    rsi,0xfffffffffffffffc
  3310:  xor    r9d,r9d
  3313:  xor    eax,eax
  3315:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  3320:  mov    r10,QWORD PTR [rdi+r9*8]
  3324:  mov    QWORD PTR [rcx+rax*8],r10
  3328:  cmp    r10,rdx
  332b:  sbb    rax,0xffffffffffffffff
  332f:  mov    r10,QWORD PTR [rdi+r9*8+0x8]
  3334:  mov    QWORD PTR [rcx+rax*8],r10
  3338:  cmp    r10,rdx
  333b:  sbb    rax,0xffffffffffffffff
  333f:  mov    r10,QWORD PTR [rdi+r9*8+0x10]
  3344:  mov    QWORD PTR [rcx+rax*8],r10
  3348:  cmp    r10,rdx
  334b:  sbb    rax,0xffffffffffffffff
  334f:  mov    r10,QWORD PTR [rdi+r9*8+0x18]
  3354:  mov    QWORD PTR [rcx+rax*8],r10
  3358:  cmp    r10,rdx
  335b:  sbb    rax,0xffffffffffffffff
  335f:  add    r9,0x4
  3363:  cmp    rsi,r9
  3366:  jne    3320 <filter_copy_mask+0x30>
  3368:  test   r8,r8
  336b:  je     3397 <filter_copy_mask+0xa7>
  336d:  lea    rsi,[rdi+r9*8]
  3371:  xor    edi,edi
  3373:  data16 data16 data16 cs nop WORD PTR [rax+rax*1+0x0]
  3380:  mov    r9,QWORD PTR [rsi+rdi*8]
  3384:  mov    QWORD PTR [rcx+rax*8],r9
  3388:  cmp    r9,rdx
  338b:  sbb    rax,0xffffffffffffffff
  338f:  inc    rdi
  3392:  cmp    r8,rdi
  3395:  jne    3380 <filter_copy_mask+0x90>
  3397:  ret
