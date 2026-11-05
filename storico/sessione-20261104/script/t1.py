from keys import *
for sense,drive,name in [(5,1,'ISO <>'),(6,7,'ISO #/u'),(2,8,'Yen'),(7,5,'Ro'),(7,0,'Muhenkan'),(5,6,'Henkan'),(7,6,'Kana'),(6,11,'Back'),(7,11,'Forward'),(5,10,'ThinkVantage'),(0,15,'LCtrl fisico'),(3,1,'cella di controllo')]:
    r=[]
    for img in (ORIG,PATCH):
        c=base(img); matrix(c,sense,drive,0); m=c.out[:]; c.out.clear(); matrix(c,sense,drive,1); b=c.out[:]
        r.append((hx(m),hx(b),hx(set1(c,m)),hx(set1(c,b))))
    print(f'{name:18} orig {r[0]}  patch {r[1]}')
