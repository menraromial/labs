; sum_twice, clang-O3-v3, syntaxe Intel (objdump -M intel)
  2ee0:  test   rsi,rsi
  2ee3:  je     2ef4 <sum_twice+0x14>
  2ee5:  cmp    rsi,0x4
  2ee9:  jae    2ef7 <sum_twice+0x17>
  2eeb:  xor    ecx,ecx
  2eed:  xor    eax,eax
  2eef:  jmp    2fa8 <sum_twice+0xc8>
  2ef4:  xor    eax,eax
  2ef6:  ret
  2ef7:  cmp    rsi,0x10
  2efb:  jae    2f03 <sum_twice+0x23>
  2efd:  xor    ecx,ecx
  2eff:  xor    eax,eax
  2f01:  jmp    2f6f <sum_twice+0x8f>
  2f03:  mov    rcx,rsi
  2f06:  and    rcx,0xfffffffffffffff0
  2f0a:  vpxor  xmm0,xmm0,xmm0
  2f0e:  xor    eax,eax
  2f10:  vpxor  xmm1,xmm1,xmm1
  2f14:  vpxor  xmm2,xmm2,xmm2
  2f18:  vpxor  xmm3,xmm3,xmm3
  2f1c:  nop    DWORD PTR [rax+0x0]
  2f20:  vpaddq ymm0,ymm0,YMMWORD PTR [rdi+rax*8]
  2f25:  vpaddq ymm1,ymm1,YMMWORD PTR [rdi+rax*8+0x20]
  2f2b:  vpaddq ymm2,ymm2,YMMWORD PTR [rdi+rax*8+0x40]
  2f31:  vpaddq ymm3,ymm3,YMMWORD PTR [rdi+rax*8+0x60]
  2f37:  add    rax,0x10
  2f3b:  cmp    rcx,rax
  2f3e:  jne    2f20 <sum_twice+0x40>
  2f40:  vpaddq ymm0,ymm1,ymm0
  2f44:  vpaddq ymm1,ymm3,ymm2
  2f48:  vpaddq ymm0,ymm1,ymm0
  2f4c:  vextracti128 xmm1,ymm0,0x1
  2f52:  vpaddq xmm0,xmm0,xmm1
  2f56:  vpshufd xmm1,xmm0,0xee
  2f5b:  vpaddq xmm0,xmm0,xmm1
  2f5f:  vmovq  rax,xmm0
  2f64:  cmp    rsi,rcx
  2f67:  je     2fb4 <sum_twice+0xd4>
  2f69:  test   sil,0xc
  2f6d:  je     2fa8 <sum_twice+0xc8>
  2f6f:  mov    rdx,rcx
  2f72:  mov    rcx,rsi
  2f75:  and    rcx,0xfffffffffffffffc
  2f79:  vmovq  xmm0,rax
  2f7e:  xchg   ax,ax
  2f80:  vpaddq ymm0,ymm0,YMMWORD PTR [rdi+rdx*8]
  2f85:  add    rdx,0x4
  2f89:  cmp    rcx,rdx
  2f8c:  jne    2f80 <sum_twice+0xa0>
  2f8e:  vextracti128 xmm1,ymm0,0x1
  2f94:  vpaddq xmm0,xmm0,xmm1
  2f98:  vpshufd xmm1,xmm0,0xee
  2f9d:  vpaddq xmm0,xmm0,xmm1
  2fa1:  vmovq  rax,xmm0
  2fa6:  jmp    2faf <sum_twice+0xcf>
  2fa8:  add    rax,QWORD PTR [rdi+rcx*8]
  2fac:  inc    rcx
  2faf:  cmp    rsi,rcx
  2fb2:  jne    2fa8 <sum_twice+0xc8>
  2fb4:  cmp    rsi,0x3
  2fb8:  ja     2fc1 <sum_twice+0xe1>
  2fba:  xor    ecx,ecx
  2fbc:  jmp    3078 <sum_twice+0x198>
  2fc1:  cmp    rsi,0x10
  2fc5:  jae    2fcb <sum_twice+0xeb>
  2fc7:  xor    ecx,ecx
  2fc9:  jmp    303f <sum_twice+0x15f>
  2fcb:  mov    rcx,rsi
  2fce:  and    rcx,0xfffffffffffffff0
  2fd2:  vmovq  xmm0,rax
  2fd7:  vpxor  xmm1,xmm1,xmm1
  2fdb:  xor    eax,eax
  2fdd:  vpxor  xmm2,xmm2,xmm2
  2fe1:  vpxor  xmm3,xmm3,xmm3
  2fe5:  data16 cs nop WORD PTR [rax+rax*1+0x0]
  2ff0:  vpaddq ymm0,ymm0,YMMWORD PTR [rdi+rax*8]
  2ff5:  vpaddq ymm1,ymm1,YMMWORD PTR [rdi+rax*8+0x20]
  2ffb:  vpaddq ymm2,ymm2,YMMWORD PTR [rdi+rax*8+0x40]
  3001:  vpaddq ymm3,ymm3,YMMWORD PTR [rdi+rax*8+0x60]
  3007:  add    rax,0x10
  300b:  cmp    rcx,rax
  300e:  jne    2ff0 <sum_twice+0x110>
  3010:  vpaddq ymm0,ymm1,ymm0
  3014:  vpaddq ymm1,ymm3,ymm2
  3018:  vpaddq ymm0,ymm1,ymm0
  301c:  vextracti128 xmm1,ymm0,0x1
  3022:  vpaddq xmm0,xmm0,xmm1
  3026:  vpshufd xmm1,xmm0,0xee
  302b:  vpaddq xmm0,xmm0,xmm1
  302f:  vmovq  rax,xmm0
  3034:  cmp    rsi,rcx
  3037:  je     3084 <sum_twice+0x1a4>
  3039:  test   sil,0xc
  303d:  je     3078 <sum_twice+0x198>
  303f:  mov    rdx,rcx
  3042:  mov    rcx,rsi
  3045:  and    rcx,0xfffffffffffffffc
  3049:  vmovq  xmm0,rax
  304e:  xchg   ax,ax
  3050:  vpaddq ymm0,ymm0,YMMWORD PTR [rdi+rdx*8]
  3055:  add    rdx,0x4
  3059:  cmp    rcx,rdx
  305c:  jne    3050 <sum_twice+0x170>
  305e:  vextracti128 xmm1,ymm0,0x1
  3064:  vpaddq xmm0,xmm0,xmm1
  3068:  vpshufd xmm1,xmm0,0xee
  306d:  vpaddq xmm0,xmm0,xmm1
  3071:  vmovq  rax,xmm0
  3076:  jmp    307f <sum_twice+0x19f>
  3078:  add    rax,QWORD PTR [rdi+rcx*8]
  307c:  inc    rcx
  307f:  cmp    rsi,rcx
  3082:  jne    3078 <sum_twice+0x198>
  3084:  vzeroupper
  3087:  ret
  3088:  nop    DWORD PTR [rax+rax*1+0x0]
