from keys import *
exec(open('t2.py').read().split("# locate LShift cell")[0])
cells=[(s,d) for s in range(8) for d in range(16)]
def dn_o(c): call(c,0xC45E)
def up_o(c): call(c,0xC465)
def dn_p(c): matrix(c,0,15,0)
def up_p(c): matrix(c,0,15,1)
FN={'orig':(ORIG,dn_o,up_o),'patch':(PATCH,dn_p,up_p)}
def seq(img,dn,up,cl,order):
    c=base(img); ev=[]
    def key(b):
        c.out.clear(); matrix(c,*cl,b); ev.append(c.out[:])
    def f(fun):
        c.out.clear(); fun(c)
    if order=='fn_up_first':   f(dn);key(0);f(up);key(1)        # Fn, K, Fn up, K up
    if order=='fn_held':       f(dn);key(0);key(1);f(up)        # normal
    if order=='fn_late':       key(0);f(dn);key(1);f(up)        # K, Fn, K up, Fn up
    if order=='none':          key(0);key(1)
    return ev
bad={}
for nm,(img,dn,up) in FN.items():
    a=b=0;ex=[]
    for cl in cells:
        if cl==(0,15):continue
        ref=seq(img,dn,up,cl,'fn_held'); e=seq(img,dn,up,cl,'fn_up_first')
        if e!=ref: a+=1; ex.append((cl,'Fn su prima',hx(e[0]),hx(e[1]),'atteso',hx(ref[1])))
        ref2=seq(img,dn,up,cl,'none'); e2=seq(img,dn,up,cl,'fn_late')
        if e2!=ref2: b+=1; ex.append((cl,'Fn tardivo',hx(e2[0]),hx(e2[1]),'atteso',hx(ref2[1])))
    print(f'{nm}: Fn rilasciato prima del tasto, sbagliati {a}/127; Fn premuto dopo il tasto, sbagliati {b}/127')
    for x in ex[:5]: print('   ',x)
# Fn-state in the fix must follow the pull-up/debounce path too
print('Fn+F2 con rilascio di Fn prima (patch):',seq(PATCH,dn_p,up_p,(0,2),'fn_up_first'))
print('Fn+F2 con rilascio di Fn prima (orig): ',seq(ORIG,dn_o,up_o,(0,2),'fn_up_first'))
