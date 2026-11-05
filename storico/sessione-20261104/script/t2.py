from keys import *
import struct,hashlib
NEW={(5,1),(6,7),(2,8),(7,5),(7,0),(5,6),(7,6),(6,11),(7,11),(5,10)}
LC=(0,15)
cells=[(s,d) for s in range(8) for d in range(16)]
def tap(c,s,d):
    c.out.clear(); matrix(c,s,d,0); m=c.out[:]; c.out.clear(); matrix(c,s,d,1); return m,c.out[:]
def fnp(c,down): c.out.clear(); call(c,0xC45E if down else 0xC465); return c.out[:]
def lc(c,down): c.out.clear(); matrix(c,*LC,0 if down else 1); return c.out[:]
def expected_cells(a,b):
    bad=[]
    return bad
def suite(O,P,label):
    fails=[]; n=0
    # A: no modifier
    for cl in cells:
        n+=1; o=tap(base(O),*cl); p=tap(base(P),*cl)
        if cl in NEW:
            if o!=([],[]) or p==([],[]): fails.append(('A',cl,o,p))
        elif cl==LC:
            if p!=([],[]): fails.append(('A',cl,o,p))
        elif o!=p: fails.append(('A',cl,o,p))
    # B: Fn layer  orig physical Fn == patch physical LCtrl
    for cl in cells:
        if cl==LC: continue
        n+=1
        co=base(O); a=fnp(co,1); o=tap(co,*cl); a2=fnp(co,0); fo=co.iram[0xBC]&0x40
        cp=base(P); b=lc(cp,1); p=tap(cp,*cl); b2=lc(cp,0); fp=cp.iram[0xBC]&0x40
        if a!=b or a2!=b2 or fo or fp: fails.append(('B-stato',cl,a,b,a2,b2,fo,fp))
        if cl not in NEW and o!=p: fails.append(('B',cl,o,p))
    # C: Ctrl  orig physical LCtrl == patch physical Fn
    for cl in cells:
        if cl==LC: continue
        n+=1
        co=base(O); a=lc(co,1); o=tap(co,*cl); a2=lc(co,0)
        cp=base(P); b=fnp(cp,1); p=tap(cp,*cl); b2=fnp(cp,0)
        if a!=b or a2!=b2: fails.append(('C-stato',cl,a,b,a2,b2))
        if cl not in NEW and o!=p: fails.append(('C',cl,o,p))
    # D: with Shift held, existing keys unchanged, new keys emit make and break
    for cl in cells:
        if cl==LC: continue
        n+=1
        co=base(O); matrix(co,*SH,0); o=tap(co,*cl)
        cp=base(P); matrix(cp,*SH,0); p=tap(cp,*cl)
        if cl in NEW:
            if p==([],[]): fails.append(('D',cl,o,p))
        elif o!=p: fails.append(('D',cl,o,p))
    print(f'{label}: {n} casi, {len(fails)} difformi'); return fails
# locate LShift cell
M=0x2EB9
SH=[(s,d) for s,d in cells if ORIG[M+(s<<4)+d]==0x88][0]; print('LShift cella',SH)
f=suite(ORIG,PATCH,'all-keys contro originale')
for x in f[:12]: print(x)
print('\n-- tasti nuovi con modificatori (patch)')
for nm,cl in [('Back',(6,11)),('Forward',(7,11)),('ThinkVantage',(5,10)),('<>',(5,1)),('ù',(6,7))]:
    c=base(PATCH); fnp(c,1); a=tap(c,*cl); c2=base(PATCH); lc(c2,1); b=tap(c2,*cl); c3=base(PATCH); matrix(c3,*SH,0); e=tap(c3,*cl)
    print(f'{nm:13} Ctrl:{hx(a[0])}/{hx(a[1])}  Fn:{hx(b[0])}/{hx(b[1])}  Shift:{hx(e[0])}/{hx(e[1])}')
print('\n-- controlli negativi: il test deve fallire')
def mut(pairs):
    d=bytearray(PATCH)
    for a,v in pairs:d[a]=v
    return bytes(d)
for nm,m in [('Back col codice sbagliato',[(0x306E,0x39)]),('tasto a su cella errata',[(0x2F0A,0x1C)]),('Fn non scambiato',[(0xC461,0x8E)]),('Forward tipo sbagliato',[(0x307F,0x00)]),('cella esistente rotta',[(0x2EB9+0x31,0x00)])]:
    r=suite(ORIG,mut(m),nm); print('   rilevato' if r else '   NON RILEVATO')
