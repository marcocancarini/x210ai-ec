import sys,re,difflib
sys.path.insert(0,'tools')
import importlib.util
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/ITEFW-lettura1.bin','rb').read();r=open('dumps/EC0416.BIN','rb').read()
BANKS=((0x0400,0x5500,0x0,'b0'),(0x8000,0xF8B0,0x0,'b1'),(0x10000,0x15520,0x10000-0x8000,'b2'))
def dis(d,s,e,base):
    out=[]; m.disasm(d,base,s-0,e-0,out) if False else None
    return out
def lines(d,s,e):
    out=[]; m.disasm(d,0,s,e,out); return out
def norm(l):
    t=l.split(':',1)[1].strip()
    t=re.sub(r'^([0-9A-F]{2} ?)+\s+','',t) if False else t
    p=t.split()
    # strip raw hex bytes if present
    q=[x for x in p if not re.fullmatch(r'[0-9A-F]{2}',x)]
    t=' '.join(q)
    t=re.sub(r'\b(LCALL|LJMP|ACALL|AJMP|SJMP) 0x[0-9A-F]+',r'\1 @',t)
    t=re.sub(r'\b(JZ|JNZ|JC|JNC) 0x[0-9A-F]+',r'\1 @',t)
    t=re.sub(r'(JB|JNB|JBC) (0x[0-9A-F]+), 0x[0-9A-F]+',r'\1 \2, @',t)
    t=re.sub(r'(CJNE .*), 0x[0-9A-F]+$',r'\1, @',t)
    t=re.sub(r'(DJNZ .*), 0x[0-9A-F]+$',r'\1, @',t)
    return t
res=[]
for s,e,off,n in ((0x400,0x5500,0,'b0'),(0x8000,0xF8B0,0,'b1'),(0x10000,0x15520,0,'b2')):
    la=lines(a,s,e); lr=lines(r,s,e)
    na=[norm(x) for x in la]; nr=[norm(x) for x in lr]
    sm=difflib.SequenceMatcher(None,nr,na,autojunk=False)
    ops=[o for o in sm.get_opcodes() if o[0]!='equal']
    print(n,'instr',len(nr),len(na),'ratio %.4f'%sm.ratio(),'diff ops',len(ops),'old lines',sum(o[2]-o[1] for o in ops),'new lines',sum(o[4]-o[3] for o in ops))
    for o in ops:
        res.append((n,o,lr[o[1]:o[2]],la[o[3]:o[4]]))
import pickle; pickle.dump(res,open(sys.argv[1],'wb'))
