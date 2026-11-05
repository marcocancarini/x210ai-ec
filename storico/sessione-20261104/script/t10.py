from keys import *
import random,itertools
exec(open('t8.py').read().split('tot={}')[0])
# Pause: E1 14 77 has no normal break. E0 12 / E0 59 are fake shifts, which Linux ignores
# (atkbd: code 0 in its table). Show when each appears, then ignore only these.
import re
t=[int(x) for x in re.findall(r'\d+',open('../net/atkbd.c').read().split('atkbd_set2_keycode[ATKBD_KEYMAP_SIZE] = {')[1].split('};')[0].split('#')[0])]
print('Linux per E0 12, E0 59:',t[0x80|0x12],t[0x80|0x59])
c=base(PATCH); 
print('cella Pausa, PrtSc e frecce: quali celle generano i codici residui')
src={}
for cl in cells:
    for st,set_ in (('nudo',None),('shift',(3,14))):
        c=base(PATCH)
        if set_: matrix(c,*set_,0)
        c.out.clear(); matrix(c,*cl,0); m=c.out[:]; c.out.clear(); matrix(c,*cl,1); b=c.out[:]
        for k,_ in tokens(m+b):
            if k in (0x112,0x159,0x14,0x77,0xE1): src.setdefault(hex(k),set()).add((cl,st,hx(m),hx(b)))
for k,v in src.items(): print(k,sorted(v)[:3])
IGN={0x112,0x159}
def run(img,fc,seeds=300,steps=600):
    st=0;ex=set()
    for s in range(seeds):
        d=fuzz(img,fc,s,steps)-IGN
        d={x for x in d}
        if img is not None and d-{0x14,0x77,0xE1}:
            st+=1; ex|=d
    return st,sorted(hex(x) for x in ex)
print('originale',run(ORIG,False)); print('patch    ',run(PATCH,True))
# Fixed reference + pairs
g={}; exec(open('t7.py').read().split('bad={}')[0],g)
FNC=[c for c in g['cells'] if c!=(0,15) and g['seq'](ORIG,g['dn_o'],g['up_o'],c,'fn_held')!=g['seq'](ORIG,g['dn_o'],g['up_o'],c,'none')]
print('tasti con variante Fn:',len(FNC))
def strict(img):
    bad=0; w=set()
    def wr(a,v):
        if PC[0]: w.add(a)
    for cl in g['cells']:
        if cl==(0,15):continue
        for o in ('fn_up_first','fn_held','fn_late','none'):
            if g['seq'](img,g['dn_p'],g['up_p'],cl,o)!=g['seq'](PATCH,g['dn_p'],g['up_p'],cl,o): bad+=1
    for a,b in itertools.permutations(FNC,2):
        for im in (img,):
            r=[]
            for I in (im,PATCH):
                c=base(I); o=[]
                def k(x,bk):
                    c.out.clear(); matrix(c,*x,bk); o.append(c.out[:])
                matrix(c,0,15,0); k(a,0); matrix(c,0,15,1); k(b,0); k(a,1); k(b,1); r.append(o)
            if r[0]!=r[1]: bad+=1
    # writes done by the new code must stay inside the bitmap
    c=base(img); wr=[]
    orig_x=c.xwr
    def xwr(a,v):
        if 0x5600<=c.pc<0x5660: wr.append(a)
        orig_x(a,v)
    c.xwr=xwr
    matrix(c,0,15,0)
    for cl in FNC: matrix(c,*cl,0)
    for cl in FNC: matrix(c,*cl,1)
    out=sorted({a for a in wr if not (0xE0<=a<=0xEC or a==0x80E)})
    return bad,[hex(a) for a in out]
print('riferimento',strict(PATCH))
def mut(p):
    d=bytearray(PATCH)
    for a,v in p:d[a]=v
    return bytes(d)
n=0;M=[('salto disattivato',[(0x8CFA,0x90),(0x8CFB,0x08),(0x8CFC,0x0E)]),('salva sempre 0',[(0x5628,0x80)]),('maschera sbagliata',[(0x5646,0x02)]),('bitmap altrove',[(0x561A,0xD0)]),('rilascio senza stato',[(0x5621,0x00),(0x5622,0x00)]),('indice errato',[(0x5616,0x00)])]
for nm,m in M:
    r=strict(mut(m)); ok=bool(r[0] or r[1]); n+=ok; print(f'{nm:24}',r,'rilevato' if ok else 'NON RILEVATO')
print(f'{n}/{len(M)} mutazioni rilevate')
