from keys import *
PIN=0x1608
def poll(c,low):
    c.x[PIN]=(c.x[PIN]&0x7F)|(0 if low else 0x80)
    c.rset(7,4)
    call(c,0xC4C8)
def press_pin(c,low,n):
    c.out.clear(); got=[]
    for i in range(n):
        poll(c,low)
        if c.out and not got: got=[i+1]+c.out[:]
    return got
print('### Fn tramite il debounce reale, entry 4')
for name,img in (('orig',ORIG),('patch',PATCH)):
    c=base(img); calls=[]
    c.hooks[0xC45E]=lambda s:calls.append('down')
    c.hooks[0xC465]=lambda s:calls.append('up')
    for i in range(10): poll(c,0)   # settle: pin released? see below
    print(name,'dopo 10 poll pin basso',calls,hx(c.out),'0xBC=%02X'%c.iram[0xBC]); calls.clear(); c.out.clear()
    for i in range(10): poll(c,1)
    print(name,'dopo 10 poll pin alto ',calls,hx(c.out),'0xBC=%02X'%c.iram[0xBC]); calls.clear(); c.out.clear()
    # short glitch must not trigger
    for i in range(3): poll(c,0)
    for i in range(10): poll(c,1)
    print(name,'glitch 3 poll',calls,hx(c.out))
print('\n### Stato iniziale del pin al boot')
for low in (1,0):
    c=base(ORIG); calls=[]; c.hooks[0xC45E]=lambda s:calls.append('down'); c.hooks[0xC465]=lambda s:calls.append('up')
    for i in range(10): poll(c,low)
    print('pin','basso' if low else 'alto',calls)
print('\n### Fn rilasciato PRIMA del tasto')
cells=[(s,d) for s in range(8) for d in range(16)]
def trial(img,cl,fndown,fnup):
    c=base(img); fndown(c); c.out.clear(); matrix(c,*cl,0); m=c.out[:]; fnup(c); c.out.clear(); matrix(c,*cl,1); b=c.out[:]; return m,b
def sym(m,b):
    # break must be the make with F0 before the final byte
    if not m: return b==[]
    return b==m[:-1]+[0xF0,m[-1]] 
for name,img,dn,up in (('orig con Fn fisico',ORIG,lambda c:call(c,0xC45E),lambda c:call(c,0xC465)),
                       ('patch con LCtrl fisico',PATCH,lambda c:matrix(c,0,15,0),lambda c:matrix(c,0,15,1))):
    bad=[];diff=[]
    for cl in cells:
        if cl==(0,15):continue
        m,b=trial(img,cl,dn,up)
        c0=base(img); nm=[]; matrix(c0,*cl,0); nm=c0.out[:]
        if m!=nm: diff.append((cl,hx(m),hx(nm)))
        if not sym(m,b): bad.append((cl,hx(m),hx(b)))
    print(f'{name}: {len(diff)} combinazioni Fn attive, rilascio incoerente: {len(bad)}')
    for x in bad[:12]: print('  ',x)
    print('   es.',diff[:6])
