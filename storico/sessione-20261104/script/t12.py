from keys import *
exec(open('t2.py').read().split("# locate LShift cell")[0])
M=0x2EB9
SH=[(s,d) for s,d in cells if ORIG[M+(s<<4)+d]==0x88][0]
EXTRA={(6,11),(7,11),(5,10)}
NEW.difference_update(EXTRA)
f=suite(ORIG,PATCH,'iso-jis + swap')
print('difformi',len(f)); print(f[:4])
c=base(PATCH); c.out.clear(); call(c,0xC45E); d=c.out[:]; c.out.clear(); call(c,0xC465); print('Fn fisico:',hx(d),'/',hx(c.out))
c=base(PATCH); c.out.clear(); matrix(c,0,15,0); d=c.out[:]; a=c.iram[0x29]; c.out.clear(); matrix(c,0,15,1); print('LCtrl fisico:',repr(hx(d)),'29=%02X ->%02X'%(a,c.iram[0x29]))
g={}; exec(open('t7.py').read().split('bad={}')[0],g)
b=sum(g['seq'](PATCH,g['dn_p'],g['up_p'],cl,'fn_up_first')!=g['seq'](PATCH,g['dn_p'],g['up_p'],cl,'fn_held') for cl in g['cells'] if cl!=(0,15))
print('rilascio errato se lasci il nuovo Fn prima del tasto:',b,'/127')
