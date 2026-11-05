import re
a=open('dumps/EC-V0.4.0-20250723-lettura1.bin','rb').read()
x220='''01 02 11 10 1f 6e 2e 83
70 03 12 1e 20 2d 2f 00
71 04 13 72 21 73 30 00
06 05 14 15 22 23 31 32
07 08 17 16 25 24 34 33
0d 09 18 1c 26 75 35 38
77 0a 19 76 27 84 36 85
0c 0b 1a 1b 28 29 2a 37
78 79 0e 0f 1d 74 2b 3d
4b 7b 00 9b 00 00 00 59
4c 7a 9a 99 98 97 a0 54
55 56 00 00 9c 00 89 8a
50 51 00 00 00 53 7e 4f
00 7c 7d 00 00 3c 00 3e
00 00 00 2c 00 00 39 00
3a 00 00 00 00 00 40 00'''.split('\n')
M=[[int(v,16) for v in l.split()] for l in x220]
both=mine_only=their_only=0;to=[];mo=[]
for d in range(16):
    for s in range(8):
        o=a[0x2EB9+(s<<4)+d]; t=M[d][s]
        if o and t: both+=1
        elif o: mine_only+=1; mo.append((s,d,hex(o)))
        elif t: their_only+=1; to.append((s,d,hex(t)))
print('both',both,'only V0.4.0',mine_only,mo,'only x220',their_only,to)
# semantic check: IBM key number -> set2 for pure typing keys
ibm={1:0x0e,2:0x16,3:0x1e,4:0x26,5:0x25,6:0x2e,7:0x36,8:0x3d,9:0x3e,10:0x46,11:0x45,12:0x4e,13:0x55,15:0x66,16:0x0d,17:0x15,18:0x1d,19:0x24,20:0x2d,21:0x2c,22:0x35,23:0x3c,24:0x43,25:0x44,26:0x4d,27:0x54,28:0x5b,29:0x5d,30:0x58,31:0x1c,32:0x1b,33:0x23,34:0x2b,35:0x34,36:0x33,37:0x3b,38:0x42,39:0x4b,40:0x4c,41:0x52,43:0x5a,46:0x1a,47:0x22,48:0x21,49:0x2a,50:0x32,51:0x31,52:0x3a,53:0x41,54:0x49,55:0x4a,110:0x76}
ok=bad=0;B=[]
for d in range(16):
    for s in range(8):
        t=M[d][s]
        if t in ibm:
            o=a[0x2EB9+(s<<4)+d]
            if o==ibm[t]: ok+=1
            else: bad+=1;B.append((s,d,hex(t),hex(o)))
print('typing keys match',ok,'mismatch',bad,B)
# patched diffs
import hashlib
for n in ('iso-jis','fn-ctrl-swap','iso-jis-fn-ctrl-swap'):
    p=open('dumps/EC-V0.4.0-%s.bin'%n,'rb').read()
    d=[(hex(i),hex(a[i]),hex(p[i])) for i in range(len(a)) if a[i]!=p[i]]
    print(n,len(p),d, 'sig',p[0x40:0x50]==a[0x40:0x50],'reset',p[:0x40]==a[:0x40],'banner',p[0x7F80:0x7FC0]==a[0x7F80:0x7FC0])
for c,s1 in ((0x61,0x56),(0x5d,0x2b),(0x6a,0x7d),(0x51,0x73),(0x67,0x7b),(0x64,0x79),(0x13,0x70)):
    assert a[0xD03+c]==s1,hex(c)
print('set1 ok')
print('ptrs',[ (hex(x.start())) for x in re.finditer(rb'\x90\x00\xca',a) if x.start()<0x15600][:10],'xram00D5',[hex(x.start()) for x in re.finditer(rb'\x90\x00\xd5',a) if x.start()<0x15600])
