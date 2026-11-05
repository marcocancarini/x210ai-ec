import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
def refs(pat):
    return [hex(x.start()) for x in re.finditer(pat,a)]
print('DPTR 0029',refs(rb'\x90\x00\x29'));print('DPTR 002A',refs(rb'\x90\x00\x2a'))
for x in re.finditer(rb'\x90\x00\x29',a):
    s=x.start();o=[]
    if s<0x10000:
        m.disasm(a,0,max(s-16,0),s+22,o);print('---',hex(s));print('\n'.join(o))
