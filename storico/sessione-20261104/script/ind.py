# independent check: table-driven CRC, plus find the natural init/xorout, plus sensitivity
import sys
fs=['storico/produttore/MTLH-NB06-ec-250322/MTLH-NB06_E03-250322.BIN','dumps/EC0416.BIN','dumps/EC-V0.4.0-20250723-lettura1.bin','dumps/EC-V0.4.0-iso-jis-fn-ctrl-swap.bin','dumps/EC-V0.4.0-iso-jis.bin','dumps/EC-V0.4.0-fn-ctrl-swap.bin']
T=[]
for b in range(256):
    c=b<<8
    for _ in range(8): c=((c<<1)^0x8005 if c&0x8000 else c<<1)&0xffff
    T.append(c)
def crc(m,i=0):
    c=i
    for v in m: c=((c<<8)&0xffff)^T[((c>>8)^v)&255]
    return c
for f in fs:
    d=open(f,'rb').read(); m=d[:0x40]+d[0x50:]
    print(len(d),'stored %02X%02X calc %04X'%(d[0x4A],d[0x4B],crc(m)^0x820F),f)
d=open(fs[1],'rb').read(); m=d[:0x40]+d[0x50:]; t=(d[0x4A]<<8)|d[0x4B]
print('natural inits (xorout 0):',[hex(i) for i in range(65536) if crc(m[:0],i)==i and False])
base=crc(m); 
# find init giving xorout 0: crc(m,i)^crc(m,0) is linear in i
hit=[]
one={b:crc(m,1<<b)^base for b in range(16)}
for i in range(65536):
    x=0
    for b in range(16):
        if i>>b&1:x^=one[b]
    if x==0x820F: hit.append(i)
print('init for xorout=0',[hex(i) for i in hit])
x0=0
for b in range(16):
    if 0xFFFF>>b&1:x0^=one[b]
print('with init FFFF xorout',hex(x0^0x820F))
a=open(fs[2],'rb').read();p=open(fs[3],'rb').read()
print('diff vs V0.4.0',[(hex(i),hex(a[i]),hex(p[i])) for i in range(len(a)) if a[i]!=p[i]])
