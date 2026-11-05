import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
def D(s,e,t=''):
    o=[];m.disasm(a,0,s,e,o);print('##',t);print('\n'.join(o))
D(0x8CD2,0x8D10,'after matrix lookup')
print('callers 0C09',[hex(x.start()) for x in re.finditer(rb'\x12\x0c\x09',a)])
print('ref tables: 2F51',[hex(x.start()) for x in re.finditer(rb'\x74\x51|\x90\x2f\x51',a)][:10])
for pat in (b'\x90\x30\x43',b'\x90\x2f\x81',b'\x90\x2f\x51',b'\x90\x2f\xc1',b'\x90\x2f\xe3',b'\x90\x30\x60',b'\x90\x30\x62',b'\x90\x30\x88'):
    print(pat.hex(),[hex(x.start()) for x in re.finditer(re.escape(pat),a)])
print('E0/mod compares: CJNE A,#0x8x / SUBB');
for pat,n in ((b'\xb4\x8c',''),(b'\xb4\x88',''),(b'\xb4\x8a',''),(b'\xb4\x8d',''),(b'\x24\x78',''),(b'\x24\x70',''),(b'\x94\x80',''),(b'\x94\x90',''),(b'\x94\xe0',''),(b'\x94\xc0',''),(b'\x94\xa0','')):
    r=[hex(x.start()) for x in re.finditer(re.escape(pat),a) if x.start()<0x15600]
    print(pat.hex(),r[:14])
