from keys import *
cells=[(s,d) for s in range(8) for d in range(16)]
X={(5,1):('61','F0 61','56','D6'),(6,7):('5D','F0 5D','2B','AB'),(2,8):('6A','F0 6A','7D','FD'),(7,5):('51','F0 51','73','F3'),
   (7,0):('67','F0 67','7B','FB'),(5,6):('64','F0 64','79','F9'),(7,6):('13','F0 13','70','F0')}
def tap(c,cl):
    c.out.clear(); matrix(c,*cl,0); m=c.out[:]; c.out.clear(); matrix(c,*cl,1); return m,c.out[:]
bad=[];n=0
for hold in (None,'shift','fn','ctrl'):
    for cl in cells:
        res=[]
        for img in (ORIG,PATCH):
            c=base(img)
            if hold=='shift': matrix(c,3,14,0)
            if hold=='fn': call(c,0xC45E)
            if hold=='ctrl': matrix(c,0,15,0)
            res.append((tap(c,cl),c))
        n+=1; o,p=res[0][0],res[1][0]
        if cl in X:
            c=res[1][1]; g=(hx(p[0]),hx(p[1]),hx(set1(c,p[0])),hx(set1(c,p[1])))
            if o!=([],[]) or g!=X[cl]: bad.append((hold,cl,o,g))
        elif o!=p: bad.append((hold,cl,o,p))
print(n,'casi, difformi',len(bad)); print(bad[:6])
for nm,img in (('orig',ORIG),('iso-jis',PATCH)):
    c=base(img); c.out.clear(); call(c,0xC45E); a=c.iram[0x29]; call(c,0xC465); b=c.iram[0x29]
    c2=base(img); matrix(c2,0,15,0); print(nm,'Fn pin giu 29=%02X su 29=%02X | LCtrl emette'%(a,b),hx(c2.out))
print('rilascio Fn prima del tasto, Fn+F2:')
c=base(PATCH); call(c,0xC45E); c.out.clear(); matrix(c,0,2,0); m=c.out[:]; call(c,0xC465); c.out.clear(); matrix(c,0,2,1); print(hx(m),'/',hx(c.out))
