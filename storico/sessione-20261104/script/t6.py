from keys import *
def poll(c,low,tr):
    c.x[0x1608]=(c.x[0x1608]&0x7F)|(0 if low else 0x80)
    c.rset(7,4); ev.clear(); call(c,0xC4C8)
    print(tr,'pin','L' if low else 'H','07FD=%d 07FE=%d CA=%02X D5=%d'%(c.x[0x7FD],c.x[0x7FE],c.x[0xCA],c.x[0xD5]),ev,'BC=%02X 29=%02X'%(c.iram[0xBC],c.iram[0x29]),hx(c.out))
ev=[]
c=base(ORIG)
c.hooks[0xC45E]=lambda s:ev.append('C45E(make)')
c.hooks[0xC465]=lambda s:ev.append('C465(break)')
c.hooks[0xC447]=lambda s:ev.append('poll')
for i in range(8): poll(c,1,i)
print()
for i in range(8): poll(c,0,i)
print()
for i in range(8): poll(c,1,i)
