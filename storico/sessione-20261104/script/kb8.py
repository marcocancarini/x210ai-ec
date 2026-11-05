import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
def D(s,e,t=''):
    o=[];m.disasm(a,0,s,e,o);print('##',t);print('\n'.join(o))
D(0x2CD8,0x2D00,'handlers ptr')
print('MOV R7,#8E/8F',[hex(x.start()) for x in re.finditer(rb'\x7f[\x8e\x8f]',a) if x.start()<0x15600])
print('MOV A,#8E',[hex(x.start()) for x in re.finditer(rb'\x74\x8e',a) if x.start()<0x15600])
print('calls 8D77',[hex(x.start()) for x in re.finditer(rb'\x12\x8d\x77',a)])
print('calls 8CB2',[hex(x.start()) for x in re.finditer(rb'\x12\x8c\xb2',a)],'9C54 ',[hex(x.start()) for x in re.finditer(rb'\x12\x9c\x54',a)],'8E41',[hex(x.start()) for x in re.finditer(rb'\x12\x8e\x41',a)])
# what sets 0x07FD or 0x00FA? 
for pat,n in ((rb'\x90\x00\xfa','00FA'),(rb'\x90\x00\xfb','00FB'),(rb'\x90\x00\xfc','00FC'),(rb'\x90\x07\xfd','07FD')):
    print(n,[hex(x.start()) for x in re.finditer(pat,a) if x.start()<0x15600])
