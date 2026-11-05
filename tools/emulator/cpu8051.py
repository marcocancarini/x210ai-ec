# Complete 8051 interpreter with the X210AI code banking (P1.0-2 select the 0x8000 window)
class CPU:
    def __init__(s,image):
        s.rom=image; s.iram=bytearray(256); s.sfr=bytearray(256); s.x=bytearray(65536)
        s.pc=0; s.sfr[0x81]=7; s.count=0; s.hooks={}; s.xw=None
    def clone(s):
        c=CPU(s.rom); c.iram[:]=s.iram; c.sfr[:]=s.sfr; c.x[:]=s.x; c.pc=s.pc; c.hooks=dict(s.hooks); return c
    def code(s,a):
        a&=0xFFFF
        if a<0x8000: return s.rom[a]
        return s.rom[(a-0x8000)+0x8000*(1+(s.sfr[0x90]&7))&0x1FFFF]
    def rget(s,n): return s.iram[(s.sfr[0xD0]&0x18)+n]
    def rset(s,n,v): s.iram[(s.sfr[0xD0]&0x18)+n]=v&255
    def dget(s,a):
        if a<0x80: return s.iram[a]
        if a==0xD0: return s.psw()
        return s.sfr[a]
    def dset(s,a,v):
        v&=255
        if a<0x80: s.iram[a]=v
        else: s.sfr[a]=v
    def psw(s):
        v=s.sfr[0xD0]&0xFE
        return v|(bin(s.sfr[0xE0]).count('1')&1)
    def bit(s,b):
        a,m=(0x20+(b>>3),1<<(b&7)) if b<0x80 else (b&0xF8,1<<(b&7))
        return (s.dget(a)&m)!=0
    def bset(s,b,v):
        a,m=(0x20+(b>>3),1<<(b&7)) if b<0x80 else (b&0xF8,1<<(b&7))
        o=s.dget(a); s.dset(a,(o|m) if v else (o&~m))
    @property
    def c(s): return s.sfr[0xD0]>>7
    def setc(s,v): s.sfr[0xD0]=(s.sfr[0xD0]&0x7F)|(0x80 if v else 0)
    def dptr(s): return s.sfr[0x83]<<8|s.sfr[0x82]
    def setdptr(s,v): s.sfr[0x83]=(v>>8)&255; s.sfr[0x82]=v&255
    def push(s,v):
        s.sfr[0x81]=(s.sfr[0x81]+1)&255; s.iram[s.sfr[0x81]]=v&255
    def pop(s):
        v=s.iram[s.sfr[0x81]]; s.sfr[0x81]=(s.sfr[0x81]-1)&255; return v
    def fetch(s):
        v=s.code(s.pc); s.pc=(s.pc+1)&0xFFFF; return v
    def rel(s):
        r=s.fetch(); return (s.pc+(r-256 if r>127 else r))&0xFFFF
    def xr(s,a): return s.x[a&0xFFFF]
    def xwr(s,a,v):
        s.x[a&0xFFFF]=v&255
        if s.xw is not None: s.xw(a&0xFFFF,v&255)
    def add(s,v,cin=0):
        a=s.sfr[0xE0]; r=a+v+cin
        ov=((a^r)&(v^r)&0x80)!=0
        p=s.sfr[0xD0]&0x3B
        if r>255:p|=0x80
        if (a&15)+(v&15)+cin>15:p|=0x40
        if ov:p|=4
        s.sfr[0xD0]=p; s.sfr[0xE0]=r&255
    def subb(s,v):
        a=s.sfr[0xE0]; c=s.c; r=a-v-c
        ov=((a^v)&(a^r)&0x80)!=0
        p=s.sfr[0xD0]&0x3B
        if r<0:p|=0x80
        if (a&15)-(v&15)-c<0:p|=0x40
        if ov:p|=4
        s.sfr[0xD0]=p; s.sfr[0xE0]=r&255
    def src(s,o):
        l=o&15
        if l==4:return s.fetch()
        if l==5:return s.dget(s.fetch())
        if l in(6,7):return s.iram[s.rget(o&1)]
        return s.rget(o&7)
    def step(s):
        if s.pc in s.hooks: s.hooks[s.pc](s)
        o=s.fetch(); s.count+=1; A=s.sfr[0xE0]; h=o>>4; l=o&15
        if l==1:
            a=s.fetch(); t=(s.pc&0xF800)|((o>>5)<<8)|a
            if o&0x10:
                s.push(s.pc); s.push(s.pc>>8)
            s.pc=t; return
        if o==0:return
        if o==2:
            a=s.fetch()<<8; a|=s.fetch(); s.pc=a;return
        if o==3: s.sfr[0xE0]=(A>>1)|((A&1)<<7);return
        if o==0x12:
            a=s.fetch()<<8; a|=s.fetch(); s.push(s.pc); s.push(s.pc>>8); s.pc=a;return
        if o==0x13:
            c=A&1; s.sfr[0xE0]=(A>>1)|(s.c<<7); s.setc(c);return
        if o==0x22 or o==0x32:
            hi=s.pop(); s.pc=hi<<8|s.pop();return
        if o==0x23: s.sfr[0xE0]=((A<<1)|(A>>7))&255;return
        if o==0x33:
            c=A>>7; s.sfr[0xE0]=((A<<1)|s.c)&255; s.setc(c);return
        if o in(4,0x14):
            s.sfr[0xE0]=(A+(1 if o==4 else -1))&255;return
        if h in(0,1) and l>=5:
            d=1 if h==0 else -1
            if l==5:
                a=s.fetch(); s.dset(a,s.dget(a)+d)
            elif l<8:
                r=s.rget(l&1); s.iram[r]=(s.iram[r]+d)&255
            else: s.rset(l&7,s.rget(l&7)+d)
            return
        if o==0x10:
            b=s.fetch(); t=s.rel()
            if s.bit(b): s.bset(b,0); s.pc=t
            return
        if o in(0x20,0x30):
            b=s.fetch(); t=s.rel()
            if s.bit(b)==(o==0x20): s.pc=t
            return
        if o in(0x40,0x50,0x60,0x70,0x80):
            t=s.rel()
            if o==0x40 and s.c or o==0x50 and not s.c or o==0x60 and A==0 or o==0x70 and A!=0 or o==0x80: s.pc=t
            return
        if h in(2,3) and l>=4: s.add(s.src(o),s.c if h==3 else 0);return
        if h==9 and l>=4 and True: s.subb(s.src(o));return
        if h in(4,5,6):
            if l==2 or l==3:
                a=s.fetch(); v=s.sfr[0xE0] if l==2 else s.fetch(); d=s.dget(a)
                s.dset(a,d|v if h==4 else d&v if h==5 else d^v);return
            if l>=4:
                v=s.src(o); s.sfr[0xE0]=A|v if h==4 else A&v if h==5 else A^v;return
        if o==0x72: s.setc(s.c or s.bit(s.fetch()));return
        if o==0x82: s.setc(s.c and s.bit(s.fetch()));return
        if o==0xA0: s.setc(s.c or not s.bit(s.fetch()));return
        if o==0xB0: s.setc(s.c and not s.bit(s.fetch()));return
        if o==0x73: s.pc=(A+s.dptr())&0xFFFF;return
        if o==0x74: s.sfr[0xE0]=s.fetch();return
        if o==0x75:
            a=s.fetch(); s.dset(a,s.fetch());return
        if h==7 and l>=6:
            v=s.fetch()
            if l<8: s.iram[s.rget(l&1)]=v
            else: s.rset(l&7,v)
            return
        if o==0x83: s.sfr[0xE0]=s.code(A+s.pc);return
        if o==0x84:
            B=s.sfr[0xF0]; s.sfr[0xD0]&=0x7B
            if B==0: s.sfr[0xD0]|=4
            else: s.sfr[0xE0]=A//B; s.sfr[0xF0]=A%B
            return
        if o==0x85:
            a=s.fetch(); b=s.fetch(); s.dset(b,s.dget(a));return
        if h==8 and l>=6:
            v=s.rget(l&7) if l>=8 else s.iram[s.rget(l&1)]
            s.dset(s.fetch(),v);return
        if o==0x90:
            a=s.fetch()<<8; a|=s.fetch(); s.setdptr(a);return
        if o==0x92: s.bset(s.fetch(),s.c);return
        if o==0x93: s.sfr[0xE0]=s.code(A+s.dptr());return
        if o==0xA2: s.setc(s.bit(s.fetch()));return
        if o==0xA3: s.setdptr((s.dptr()+1)&0xFFFF);return
        if o==0xA4:
            r=A*s.sfr[0xF0]; s.sfr[0xE0]=r&255; s.sfr[0xF0]=r>>8
            s.sfr[0xD0]=(s.sfr[0xD0]&0x7B)|(4 if r>255 else 0);return
        if o==0xA5: raise RuntimeError('reserved opcode at %x'%(s.pc-1))
        if h==0xA and l>=6:
            v=s.dget(s.fetch())
            if l<8: s.iram[s.rget(l&1)]=v
            else: s.rset(l&7,v)
            return
        if o==0xB2:
            b=s.fetch(); s.bset(b,not s.bit(b));return
        if o==0xB3: s.setc(not s.c);return
        if h==0xB and l>=4:
            v=s.fetch() if l==4 else s.dget(s.fetch()) if l==5 else s.iram[s.rget(l&1)] if l<8 else s.rget(l&7)
            if l==5 or l==4: ref=A
            else: ref=s.iram[s.rget(l&1)] if l<8 else s.rget(l&7)
            if l>=6: v=s.fetch()
            t=s.rel(); s.setc(ref<v)
            if ref!=v: s.pc=t
            return
        if o==0xC0: s.push(s.dget(s.fetch()));return
        if o==0xC2: s.bset(s.fetch(),0);return
        if o==0xC3: s.setc(0);return
        if o==0xC4: s.sfr[0xE0]=((A<<4)|(A>>4))&255;return
        if o==0xC5 or (h==0xC and l>=6):
            if l==5:
                a=s.fetch(); v=s.dget(a); s.dset(a,A)
            elif l<8:
                r=s.rget(l&1); v=s.iram[r]; s.iram[r]=A
            else:
                v=s.rget(l&7); s.rset(l&7,A)
            s.sfr[0xE0]=v;return
        if o==0xD0:
            a=s.fetch(); s.dset(a,s.pop());return
        if o==0xD2: s.bset(s.fetch(),1);return
        if o==0xD3: s.setc(1);return
        if o==0xD4:
            a=A; c=s.c
            if a&15>9 or s.sfr[0xD0]&0x40:a+=6
            if a>0x99 or c or a>255:
                a+=0x60;c=1
            s.setc(c); s.sfr[0xE0]=a&255;return
        if o==0xD5 or (h==0xD and l>=8):
            if l==5:
                a=s.fetch(); v=(s.dget(a)-1)&255; s.dset(a,v)
            else:
                v=(s.rget(l&7)-1)&255; s.rset(l&7,v)
            t=s.rel()
            if v: s.pc=t
            return
        if o in(0xD6,0xD7):
            r=s.rget(l&1); v=s.iram[r]; s.iram[r]=(v&0xF0)|(A&15); s.sfr[0xE0]=(A&0xF0)|(v&15);return
        if o==0xE0: s.sfr[0xE0]=s.xr(s.dptr());return
        if o in(0xE2,0xE3): s.sfr[0xE0]=s.xr(s.rget(l&1));return
        if o==0xE4: s.sfr[0xE0]=0;return
        if o==0xE5: s.sfr[0xE0]=s.dget(s.fetch());return
        if h==0xE and l>=6: s.sfr[0xE0]=s.iram[s.rget(l&1)] if l<8 else s.rget(l&7);return
        if o==0xF0: s.xwr(s.dptr(),A);return
        if o in(0xF2,0xF3): s.xwr(s.rget(l&1),A);return
        if o==0xF4: s.sfr[0xE0]=A^255;return
        if o==0xF5: s.dset(s.fetch(),A);return
        if h==0xF and l>=6:
            if l<8: s.iram[s.rget(l&1)]=A
            else: s.rset(l&7,A)
            return
        raise RuntimeError('unhandled opcode %02x at %x'%(o,s.pc-1))
