import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
o=[];m.disasm(a,0,0x9300,0x9F20,o)
open('/tmp/kbs.asm','w').write('\n'.join(o))
# candidates for matrix table: find 144-byte windows with key set2 codes: containing 0x1C(A),0x32(B),0x21(C),0x23(D),0x24(E),0x5A(enter),0x29(space),0x76(esc)
need=[0x1c,0x32,0x21,0x23,0x24,0x5a,0x29,0x76,0x66,0x0d,0x12,0x59,0x14,0x11]
best=[]
for i in range(0,len(a)-144):
    w=a[i:i+144]
    n=sum(1 for k in need if k in w)
    if n>=13: best.append((n,i))
print('cand',[(n,hex(i)) for n,i in best][:12],len(best))
for pat in (rb'\xe5\x4d',rb'\x85\x4d',rb'\xf5\x4d'):
    print(pat,[hex(x.start()) for x in re.finditer(pat,a)][:30])
print('refs to E0/84 in bank?')
