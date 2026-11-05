import pickle,re,sys
res=pickle.load(open(sys.argv[1],'rb'))
def ins(l):
    p=l.split(); return ' '.join(x for x in p[1:] if not re.fullmatch(r'[0-9A-F]{2}',x))
def isreloc(t): return re.match(r'MOV #0x',t) or re.match(r'(ADD|ADDC) A, #',t)
kept=[];rel=0
for n,o,lo,ln in res:
    a=[ins(x) for x in lo]; b=[ins(x) for x in ln]
    if len(a)==len(b) and all(x==y or (isreloc(x) and isreloc(y)) for x,y in zip(a,b)): rel+=1; continue
    kept.append((n,o,lo,ln))
print('total',len(res),'reloc only',rel,'structural',len(kept))
for n,o,lo,ln in kept:
    print('---',n,lo[0].split(':')[0] if lo else '?','->',ln[0].split(':')[0] if ln else '?',o[0],len(lo),len(ln))
    for x in lo[:40]: print('  -',x)
    for x in ln[:40]: print('  +',x)
