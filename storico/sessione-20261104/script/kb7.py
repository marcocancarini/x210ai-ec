import importlib.util,re
sp=importlib.util.spec_from_file_location('i8051','tools/i8051.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
def D(s,e,t=''):
    o=[];m.disasm(a,0,s,e,o);print('##',t);print('\n'.join(o))
D(0x8CFA,0x8D77,'8CFA fn check')
D(0x98FA,0x9910,'98FA');D(0x9300,0x932F,'9300');D(0xB7B0,0xB7C8,'B7B0')
print('jump 25C8:',a[0x25C8:0x25C8+0x24].hex(' '))
for i in range(0,12):
    b=a[0x25C8+i*3:0x25C8+i*3+3];print(i,b.hex(' '))
# bit refs to iram 0x29 (bits 48-4F), and A<->0x29
pats={}
for s,e in ((0x70,0x5500),(0x8000,0xF8B0),(0x10000,0x15520)):
    o=[];m.disasm(a,0,s,e,o)
    for l in o:
        if re.search(r'\b(SETB|CLR|JB|JNB|JBC|CPL|MOV C,|MOV) ?.*0x4[89A-F]\b',l) and re.search(r'^\w+: (D2|C2|20|30|10|B2|A2|92)',l): print(l)
        if re.search(r'^\w+: (E5 29|F5 29|85 29|85 .. 29|45 29|55 29|43 29|53 29|65 29|63 29)',l): print(l)
