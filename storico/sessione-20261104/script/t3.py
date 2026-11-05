from keys import *
exec(open('t2.py').read().split("# locate LShift cell")[0])
M=0x2EB9
SH=[(s,d) for s,d in cells if ORIG[M+(s<<4)+d]==0x88][0]
# exact expected: cell -> (set 2 make, set 2 break, set 1 make, set 1 break)
X={(5,1):('61','F0 61','56','D6'),(6,7):('5D','F0 5D','2B','AB'),(2,8):('6A','F0 6A','7D','FD'),(7,5):('51','F0 51','73','F3'),
   (7,0):('67','F0 67','7B','FB'),(5,6):('64','F0 64','79','F9'),(7,6):('13','F0 13','70','F0'),
   (6,11):('E0 38','E0 F0 38','E0 6A','E0 EA'),(7,11):('E0 30','E0 F0 30','E0 69','E0 E9'),(5,10):('08','F0 08','64','E4')}
def exact(P):
    fails=[]
    for cl,e in X.items():
        for hold in (None,'shift','fn','ctrl'):
            c=base(P)
            if hold=='shift': matrix(c,*SH,0)
            if hold=='fn': lc(c,1)
            if hold=='ctrl': fnp(c,1)
            m,b=tap(c,*cl)
            got=(hx(m),hx(b),hx(set1(c,m)),hx(set1(c,b)))
            if got!=e: fails.append((cl,hold,got))
    return fails
def full(P,l):
    f=suite(ORIG,P,l)+exact(P); return f
f=full(PATCH,'all-keys'); print('difformi totali',len(f)); print('esatti: 40 casi su 10 tasti')
def mut(p):
    d=bytearray(PATCH)
    for a,v in p:d[a]=v
    return bytes(d)
ms=[('Back codice errato',[(0x306E,0x39)]),('<> codice errato',[(0x2F0A,0x1C)]),('Fn non scambiato',[(0xC461,0x8E)]),('Fn rilascio non scambiato',[(0xC468,0x8E)]),('Forward tipo errato',[(0x307F,0x00)]),
    ('cella esistente rotta',[(0x2EB9+0x31,0x00)]),('ù in cella sbagliata',[(0x2F20,0),(0x2F21,0x5D)]),('LCtrl non spostato',[(0x2EC8,0x8C)]),('ThinkVantage assente',[(0x2F13,0)])]
det=0
for nm,m in ms:
    import io,contextlib
    with contextlib.redirect_stdout(io.StringIO()): r=full(mut(m),nm)
    det+=bool(r); print(f'{nm:28}', 'rilevato' if r else 'NON RILEVATO', len(r))
print(f'mutazioni rilevate {det}/{len(ms)}')
