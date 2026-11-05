import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
r=open('dumps/EC0416.BIN','rb').read()
def D(s,e,t=''):
    o=[];m.disasm(a,0,s,e,o);print('##',t);print('\n'.join(o))
def F(p): return [hex(x.start()) for x in re.finditer(p,a) if x.start()<0x15600]
for n,p in (('C447',rb'\x12\xc4\x47'),('C447j',rb'\x02\xc4\x47'),('C45E',rb'\x12\xc4\x5e'),('C45Ej',rb'\x02\xc4\x5e'),('C465',rb'\x12\xc4\x65'),('C465j',rb'\x02\xc4\x65'),('C444',rb'\x12\xc4\x44'),('C441',rb'\x12\xc4\x41'),
            ('DPTR1608',rb'\x90\x16\x08'),('R0 BC',rb'\x78\xbc'),('direct BC',rb'\xe5\xbc'),('bit4E',rb'[\x20\x30\xd2\xc2\x10]\x4e')):
    print(n,F(p))
print('C45x addr in tables',[hex(i) for i in range(0,0x15600) if a[i:i+2] in (b'\xc4\x5e',b'\xc4\x65',b'\xc4\x47')][:20])
print('old same',r[0x2EB9:0x2F39]==a[0x2EB9:0x2F39],'0x2F39 bytes',a[0x2F39:0x2F51].hex(' '))
