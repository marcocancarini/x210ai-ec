import re
from keys import *
src=open('../ref/atkbd.c').read().split('atkbd_set2_keycode[ATKBD_KEYMAP_SIZE] = {')[1].split('};')[0]
src=src.split('#else')[0] if False else src
src=re.sub(r'#ifdef.*?#else','',src,flags=re.S); src=re.sub(r'#endif','',src); src=re.sub(r'/\*.*?\*/','',src,flags=re.S)
T=[int(x) for x in re.findall(r'\b\d+\b',src)]
names={}
for m in re.finditer(r'#define\s+(KEY_\w+)\s+(\d+|0x[0-9a-f]+)',open('../ref/ec.h').read()):
    names.setdefault(int(m[2],0),m[1])
def lin(bs):
    i=0;o=[];e=0
    for v in bs:
        if v==0xE0:e=1;continue
        if v==0xF0:continue
        if v==0xE1:o.append('PAUSE-seq');continue
        c=T[(0x80 if e else 0)|v] if ((0x80 if e else 0)|v)<len(T) else 0
        o.append(names.get(c,str(c)));e=0
    return ' + '.join(o)
print(len(T))
M=0x2EB9
for s in range(8):
  for d in range(16):
    if (s,d)==(0,15) or not PATCH[M+(s<<4)+d]:continue
    c=base(PATCH); matrix(c,s,d,0); n=c.out[:]
    f=base(PATCH); matrix(f,0,15,0); f.out.clear(); matrix(f,s,d,0); m=f.out[:]
    if n!=m: print(f'cella KSI{s}/KSO{d}: normale {hx(n):12} [{lin(n)}]  con Fn {hx(m):12} [{lin(m)}]')
