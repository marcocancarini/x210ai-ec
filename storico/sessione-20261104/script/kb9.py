import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
def D(s,e,t=''):
    o=[];m.disasm(a,0,s,e,o);print('##',t);print('\n'.join(o))
D(0xC430,0xC4A8,'Fn C4xx')
D(0x923C,0x9300,'mods')
