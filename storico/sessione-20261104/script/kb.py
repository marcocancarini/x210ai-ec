import importlib.util
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
def D(s,e):
    o=[];m.disasm(a,0,s,e,o);print('\n'.join(o))
print('set2->set1 0D03:');
t=a[0xD03:0xD83]
for i in range(0,128,16): print('%02X:'%i,t[i:i+16].hex(' '))
print('## 0C09');D(0xC09,0xC60)
