from keys import *
def boot(img,N):
    c=CPU(img); w=[]
    c.xw=lambda a,v:w.append((a,v))
    for i in range(N): c.step()
    return w,c.pc
N=3000000
a,pa=boot(ORIG,N); b,pb=boot(PATCH,N)
print('scritture XRAM',len(a),len(b),'pc',hex(pa),hex(pb))
d=[(i,x,y) for i,(x,y) in enumerate(zip(a,b)) if x!=y]
print('differenze',[(i,'%04X=%02X'%x,'%04X=%02X'%y) for i,x,y in d][:6],'totale',len(d))
