; sum_array, clang -O2, syntaxe Intel (objdump -M intel)
  22d0:  test   rsi,rsi
  22d3:  je     22e1 <sum_array+0x11>
  22d5:  cmp    rsi,0x4
  22d9:  jae    22e4 <sum_array+0x14>
  22db:  xor    ecx,ecx
  22dd:  xor    eax,eax
  22df:  jmp    2330 <sum_array+0x60>
  22e1:  xor    eax,eax
  22e3:  ret
  22e4:  mov    rcx,rsi
  22e7:  and    rcx,0xfffffffffffffffc
  22eb:  pxor   xmm0,xmm0
  22ef:  xor    eax,eax
  22f1:  pxor   xmm1,xmm1
  22f5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2300:  movdqu xmm2,XMMWORD PTR [rdi+rax*8]
  2305:  paddq  xmm0,xmm2
  2309:  movdqu xmm2,XMMWORD PTR [rdi+rax*8+0x10]
  230f:  paddq  xmm1,xmm2
  2313:  add    rax,0x4
  2317:  cmp    rcx,rax
  231a:  jne    2300 <sum_array+0x30>
  231c:  paddq  xmm1,xmm0
  2320:  pshufd xmm0,xmm1,0xee
  2325:  paddq  xmm0,xmm1
  2329:  movq   rax,xmm0
  232e:  jmp    2337 <sum_array+0x67>
  2330:  add    rax,QWORD PTR [rdi+rcx*8]
  2334:  inc    rcx
  2337:  cmp    rsi,rcx
  233a:  jne    2330 <sum_array+0x60>
  233c:  ret
  233d:  nop    DWORD PTR [rax]
