import re,sys
O=sys.argv[1]
j=open(O+'/keyboard.json').read()
cols=re.findall(r'"GP(\d+)"',re.search(r'"cols"\s*:\s*\[(.*?)\]',j,re.S).group(1))
rows=re.findall(r'"GP(\d+)"',re.search(r'"rows"\s*:\s*\[(.*?)\]',j,re.S).group(1))
p=open(O+'/pinout.txt').read()
S={m[0]:int(m[1]) for m in re.findall(r'GPIO(\d+) \| SENSE(\d)',p)}
D={m[0]:int(m[1]) for m in re.findall(r'GPIO(\d+) \| DRV(\d+)',p)}
print('rows',rows,'cols',cols)
Rm=[S[g] for g in rows]; Cm=[D[g] for g in cols]
print('sense',Rm,'drv',Cm)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
p2=open('dumps/EC-V0.4.0-iso-jis-fn-ctrl-swap.bin','rb').read()
def cell(s,d): return 0x2EB9+(s<<4)+d
txt=open(O+'/table-main.txt').read()
seen={}
for r,c,n in re.findall(r'row=(\d) col=(\d+)\s+(.+)',txt):
    seen[(int(r),int(c))]=n.strip()
ex={'q':0x15,'w':0x1d,'e':0x24,'r':0x2d,'t':0x2c,'y':0x35,'u':0x3c,'i':0x43,'o':0x44,'p':0x4d,'a':0x1c,'s':0x1b,'d':0x23,'f':0x2b,'g':0x34,'h':0x33,'j':0x3b,'k':0x42,'l':0x4b,'z':0x1a,'x':0x22,'c':0x21,'v':0x2a,'b':0x32,'n':0x31,'m':0x3a,'1':0x16,'2':0x1e,'3':0x26,'4':0x25,'5':0x2e,'6':0x36,'7':0x3d,'8':0x3e,'9':0x46,'0':0x45,'Tab':0x0d,'Enter':0x5a,'Backspace':0x66,'ESC':0x76,'CapsLock':0x58,'L_Ctrl':0x8c,'R_Ctrl':0x8d,'L_Alt':0x8a,'R_Alt':0x8b,'Windows/Super':0x82,'Program (Menu)':0x84,'F1':0x05,'F6':0x0b,'F8':None}
ok=bad=0;B=[]
for (r,c),n in seen.items():
    s,d=Rm[r],Cm[c]
    v=a[cell(s,d)]
    if n in ex and ex[n] is not None:
        if v==ex[n]: ok+=1
        else: bad+=1;B.append((n,s,d,hex(v)))
print('checked',ok,'bad',bad,B)
print('--- JIS/ISO cells via X20x JP table')
for n in ('Yen','Muhenkan','Henkan','Katakana/Hiragana/Romaji','\\','¥',']','@','[','Hankaku/Zenkaku','ThinkVantage','Browser Back','Browser Forward','Mute','VolDn','VolUp','L_Shift','R_Shift','Space'):
    for (r,c),m in seen.items():
        if m==n:
            s,d=Rm[r],Cm[c]; print(f'{n:28s} SENSE{s} DRV{d:<2d} stock={a[cell(s,d)]:02x} patched={p2[cell(s,d)]:02x} off=0x{cell(s,d):04X}')
print('ISO <> cell sense5 drv1 listed?', [k for k,m in seen.items() if (Rm[k[0]],Cm[k[1]])==(5,1)])
keys=set((Rm[r],Cm[c]) for r,c in seen)
empty=[(s,d) for s in range(8) for d in range(16) if a[cell(s,d)]==0]
print('fw-empty cells that exist on X20x JP:',[(s,d,seen[(Rm.index(s),Cm.index(d))]) for s,d in empty if (s,d) in keys])
print('fw-used cells absent from X20x JP table:',[(s,d,hex(a[cell(s,d)])) for s in range(8) for d in range(16) if a[cell(s,d)] and (s,d) not in keys])
