import importlib.util,re,collections,hashlib
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
R='dumps/'
a=open(R+'ITEFW-lettura1.bin','rb').read();r=open(R+'EC0416.BIN','rb').read()
def L(d,s,e):
    o=[];m.disasm(d,0,s,e,o);return o
def show(d,s,e,t):
    print('##',t); print('\n'.join(L(d,s,e)))
# flash entry
show(r,0x8000,0x8030,'8000 same in both')
for nm,d in (('new',a),('old',r)):
    show(d,0x0A0F,0x0A16,nm+' 0A0F');show(d,0x0A40,0x0A50,nm+' 0A40');show(d,0x0928,0x0938,nm+' 0928');show(d,0x8A62,0x8A7A,nm+' 8A62')
# xrefs by DPTR
def refs(d):
    c=collections.Counter()
    for s,e in ((0x70,0x5500),(0x8000,0xF8B0),(0x10000,0x15520)):
        for l in L(d,s,e):
            mm=re.search(r' MOV #0x([0-9A-F]{4})',l)
            if mm: c[int(mm.group(1),16)]+=1
    return c
ca,cr=refs(a),refs(r)
def rng(c,s,e): return {k:v for k,v in c.items() if s<=k<e}
for nm,s,e in (('flash ctrl 0x1000-0x10FF',0x1000,0x1100),('GPIO 0x1600-0x16FF',0x1600,0x1700),('SMBus 0x1C00-0x1CFF',0x1C00,0x1D00),('KBS 0x1D00',0x1D00,0x1E00),('ECPM/ETWD 0x1E00-0x1FFF',0x1E00,0x2000),('GCTRL 0x2000-0x20FF',0x2000,0x2100),('PWM/ADC/DAC 0x1800-0x19FF',0x1800,0x1A00),('0x2200-0x2FFF',0x2200,0x3000),('EC space 0x0400-0x05FF',0x0400,0x0600)):
    A,B=rng(ca,s,e),rng(cr,s,e)
    print(nm,'new',len(A),'old',len(B),'only new',sorted(hex(k) for k in set(A)-set(B))[:25],'only old',sorted(hex(k) for k in set(B)-set(A))[:25],'count changed',[(hex(k),B[k],A[k]) for k in sorted(set(A)&set(B)) if A[k]!=B[k]][:25])
