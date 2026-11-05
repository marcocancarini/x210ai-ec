import sys
from cpu8051 import CPU
R='dumps/'
ORIG=open(R+'EC-V0.4.0-20250723-lettura1.bin','rb').read()
PATCH=open(R+'EC-V0.4.0-all-keys.bin','rb').read()
END=0xDEAD
def base(img):
    c=CPU(img); c.sfr[0x81]=0xC0
    c.x[0x27]=0x2E; c.x[0x28]=0xB9
    c.out=[]
    def h(s): s.out.append(s.rget(7))
    c.hooks[0x990A]=h
    return c
def call(c,pc,r7=None,r5=None):
    c.push(END&255); c.push(END>>8); c.pc=pc
    if r7 is not None:c.rset(7,r7)
    if r5 is not None:c.rset(5,r5)
    n=0
    while c.pc!=END:
        c.step(); n+=1
        if n>200000: raise RuntimeError('hang at %x'%c.pc)
    return n
def matrix(c,sense,drive,brk):
    c.x[0x7FE]=(drive<<4)|sense; c.x[0x7FF]=brk
    call(c,0x8CB2)
def set1(c,bytes2):
    # real conversion routine 0x0C09, break flag carried by the F0 marker
    out=[];b=0
    for v in bytes2:
        call(c,0x0C09,v,b)
        r=c.rget(7)
        if r==0xFF: b=1; continue
        out.append(r); b=0
    return out
def hx(l): return ' '.join('%02X'%x for x in l)
