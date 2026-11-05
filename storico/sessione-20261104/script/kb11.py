import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
def D(s,e,t=''):
    o=[];m.disasm(a,0,s,e,o);print('##',t);print('\n'.join(o))
print('2D90',a[0x2D80:0x2DC0].hex(' '))
D(0x2D90,0x2DAC,'jump thunks')
print('2800 ref to thunks: LCALL/LJMP 2D9B etc')
for t in (0x2D9B,0x2DA0,0x2DA5,0x2D9A,0x2D9F,0x2DA4):
    p=bytes([0x12,t>>8,t&255]);q=bytes([0x02,t>>8,t&255])
    print(hex(t),[hex(x.start()) for x in re.finditer(re.escape(p),a)],[hex(x.start()) for x in re.finditer(re.escape(q),a)])
for s in (0xbd5b,0xc42a,0xc6ec,0xc748,0xc7a2,0xc7dd,0xd94e):
    D(s-2,s+12,hex(s))
D(0xBE05,0xBE20,'bit4E')
