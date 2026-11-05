from keys import *
import random,re
M=0x2EB9
cells=[(s,d) for s in range(8) for d in range(16) if PATCH[M+(s<<4)+d] and (s,d)!=(0,15)]
def tokens(bs):
    # (code,is_break) for a set 2 stream, E0 prefix and F0 break
    i=0;r=[];e=0;b=0
    for v in bs:
        if v==0xE0:e=1
        elif v==0xF0:b=1
        else: r.append(((e<<8)|v,b)); e=b=0
    return r
def fuzz(img,fn_cell,seed,steps):
    rnd=random.Random(seed)
    c=base(img); held=set(); fn=False; down=set()
    def fnset(v):
        c.out.clear()
        if fn_cell: matrix(c,0,15,0 if v else 1)
        else: call(c,0xC45E if v else 0xC465)
        return c.out[:]
    def feed(o):
        for code,b in tokens(o):
            (down.discard if b else down.add)(code)
    for i in range(steps):
        r=rnd.random()
        if r<.3:
            fn=not fn; feed(fnset(fn))
        elif held and r<.65:
            k=rnd.choice(sorted(held)); held.discard(k); c.out.clear(); matrix(c,*k,1); feed(c.out)
        elif len(held)<4:
            k=rnd.choice(cells)
            if k not in held:
                held.add(k); c.out.clear(); matrix(c,*k,0); feed(c.out)
    for k in sorted(held):
        c.out.clear(); matrix(c,*k,1); feed(c.out)
    if fn: feed(fnset(False))
    return down
tot={}
for nm,img,fc in (('originale',ORIG,False),('patch',PATCH,True)):
    stuck=0;runs=200;ex=set()
    for s in range(runs):
        d=fuzz(img,fc,s,400)
        if d: stuck+=1; ex|=d
    print(f'{nm}: {runs} sequenze da 400 eventi, con tasti bloccati a fine sequenza: {stuck}; codici: {sorted(hex(x) for x in ex)[:14]}')
# mutations of the new code
def mut(p):
    d=bytearray(PATCH)
    for a,v in p:d[a]=v
    return bytes(d)
import io,contextlib
src=open('t7.py').read().split('bad={}')[0]
g={}; exec(src,g)
def rel(img):
    bad=0
    for cl in g['cells']:
        if cl==(0,15):continue
        if g['seq'](img,g['dn_p'],g['up_p'],cl,'fn_up_first')!=g['seq'](img,g['dn_p'],g['up_p'],cl,'fn_held'):bad+=1
        if g['seq'](img,g['dn_p'],g['up_p'],cl,'fn_late')!=g['seq'](img,g['dn_p'],g['up_p'],cl,'none'):bad+=1
    return bad
print('riferimento',rel(PATCH))
for nm,m in [('salto disattivato',[(0x8CFA,0x90),(0x8CFB,0x08),(0x8CFC,0x0E)]),('salva sempre 0',[(0x5628,0x80)]),('maschera sbagliata',[(0x5646,0x02)]),('bitmap altrove',[(0x561A,0xD0)]),('rilascio senza stato',[(0x5621,0x00),(0x5622,0x00)])]:
    print(f'{nm:24}',rel(mut(m)),'errori')
print('\n### JIS fino ai codici Linux')
t=[int(x) for x in re.findall(r'\d+',open('../net/atkbd.c').read().split('atkbd_set2_keycode[ATKBD_KEYMAP_SIZE] = {')[1].split('};')[0].split('#')[0])]
for nm,sc,exp in [('Yen',0x6A,124),('Ro',0x51,89),('Muhenkan',0x67,94),('Henkan',0x64,92),('Kana',0x13,93),('Zenkaku',0x0E,41),('ISO <>',0x61,86),('ISO #/ù',0x5D,43),('ThinkVantage',0x08,183)]:
    print(f'{nm:13} set2 {sc:02X} -> Linux {t[sc]} atteso {exp}','OK' if t[sc]==exp else 'NO')
