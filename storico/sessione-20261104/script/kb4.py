import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
def hexd(s,n,w=16):
    for i in range(0,n,w): print('%04X:'%(s+i),a[s+i:s+i+w].hex(' '))
print('2E00..');hexd(0x2EB0,0x220)
print('refs 0027',[hex(x.start()) for x in re.finditer(rb'\x90\x00\x27',a)],'0028',[hex(x.start()) for x in re.finditer(rb'\x90\x00\x28',a)])
for x in re.finditer(rb'\x90\x00\x27',a):
    s=x.start()
    if s<0x10000:
        o=[];m.disasm(a,0,s-22,s+30,o);print('---',hex(s));print('\n'.join(o))
print('b106/b0f1');o=[];m.disasm(a,0,0xB0F1,0xB112,o);print('\n'.join(o))
print('9E51');o=[];m.disasm(a,0,0x9E51,0x9E60,o);print('\n'.join(o))
