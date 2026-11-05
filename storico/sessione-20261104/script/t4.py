from keys import *
import hashlib
CH={i for i in range(0x20000) if ORIG[i]!=PATCH[i]}
class T(CPU):
    pass
def boot(img,N):
    c=CPU(img); h=hashlib.sha256(); seen=set(); reads={}
    orig=c.code
    def code(a):
        v=orig(a); ph=(a&0xFFFF) if (a&0xFFFF)<0x8000 else ((a&0xFFFF)-0x8000)+0x8000*(1+(c.sfr[0x90]&7))
        if ph in CH: reads.setdefault(ph,set()).add(c.pc)
        return v
    c.code=code
    log=[]
    c.xw=lambda a,v: h.update(bytes([a>>8,a&255,v]))
    pcs=[]
    for i in range(N):
        seen.add(c.pc); 
        if i%500000==0: pcs.append(c.pc)
        c.step()
        h.update(c.pc.to_bytes(2,'little'))
    return h.hexdigest(),len(seen),hex(c.pc),{hex(k):sorted(hex(x) for x in v)[:3] for k,v in reads.items()},0x0400 in seen,[hex(p) for p in pcs]
N=3000000
a=boot(ORIG,N); b=boot(PATCH,N)
print('stessa traccia boot:',a[0]==b[0],'| istruzioni',N,'| PC distinti',a[1],b[1],'| pc finale',a[2],b[2],'| main 0x0400',a[4],b[4])
print('campioni',a[5]); print('byte cambiati letti al boot orig',a[3]); print('byte cambiati letti al boot patch',b[3])
