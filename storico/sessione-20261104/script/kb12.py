import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
M=a[0x2EB9:0x2F39]
print('matrix code use',{hex(c):M.count(c) for c in range(0x80,0x9C)})
ov=set()
for i in range(14): ov.update(a[0x3046+2*i:0x3046+2*i+2])
print('E0 overlay refs',sorted(hex(x) for x in ov if 0x80<=x<0x9c))
# indirect 9C..DF entries
vals=set()
for i in range(0xE0-0x9C):
    f,h,l=a[0x2FE3+3*i:0x2FE3+3*i+3];p=(h<<8)|l
    n=4 if f&0x10 else 2
    for j in range(n): vals.add(a[p+j])
print('indirect refs',sorted(hex(x) for x in vals if 0x80<=x<0x9c))
print('direct R7 imm',{hex(c):[hex(x.start()) for x in re.finditer(bytes([0x7f,c,0x12,0x8d,0x77]),a)]+[hex(x.start()) for x in re.finditer(bytes([0x7f,c,0x02,0x8d,0x77]),a)] for c in range(0x80,0x9c)})
for c in range(0x80,0x9c):
    h=[hex(x.start()) for x in re.finditer(bytes([0x7f,c]),a) if 0x70<x.start()<0x15600]
    if h: print(hex(c),'MOV R7',h[:8])
o=[];m.disasm(a,0,0x9010,0x9060,o);print('\n'.join(o))
