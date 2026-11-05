import pickle,re,sys
res=pickle.load(open(sys.argv[1],'rb'))
def strip(l):
    p=l.split(); return ' '.join(x for x in p[1:] if not re.fullmatch(r'[0-9A-F]{2}',x))
def n2(l):
    t=strip(l); t=re.sub(r'MOV DPTR, ?#0x[0-9A-F]+','MOV DPTR,#@',t); return t
cnt=0;kept=[]
for n,o,lo,ln in res:
    a=[n2(x) for x in lo]; b=[n2(x) for x in ln]
    if a==b: continue
    kept.append((n,o,lo,ln))
print('ops total',len(res),'semantic after DPTR mask',len(kept))
for n,o,lo,ln in kept:
    print('---',n,lo[0].split(':')[0] if lo else '?', '->',ln[0].split(':')[0] if ln else '?',o[0])
    for x in lo[:14]: print('  -',x)
    for x in ln[:14]: print('  +',x)
