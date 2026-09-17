; sum_discarded, gcc -O1, syntaxe Intel (objdump -M intel)
  2481:  endbr64
  2485:  test   rsi,rsi
  2488:  je     2499 <sum_discarded+0x18>
  248a:  mov    eax,0x0
  248f:  nop
  2490:  add    rax,0x1
  2494:  cmp    rsi,rax
  2497:  jne    2490 <sum_discarded+0xf>
  2499:  mov    eax,0x0
  249e:  ret
