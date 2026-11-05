import struct,re,sys,subprocess
d=open(sys.argv[1],'rb').read()
pe=struct.unpack_from('<I',d,0x3c)[0]
n=struct.unpack_from('<H',d,pe+6)[0];o=struct.unpack_from('<H',d,pe+20)[0]
base=struct.unpack_from('<Q',d,pe+24+24)[0]
secs=[]
for i in range(n):
    p=pe+24+o+40*i
    nm=d[p:p+8].rstrip(b'\0').decode();vs,va,rs,rp=struct.unpack_from('<IIII',d,p+8)
    secs.append((nm,va,vs,rp,rs))
print(hex(base),secs)
def f2r(x):
    for nm,va,vs,rp,rs in secs:
        if rp<=x<rp+rs:return x-rp+va
txt=[s for s in secs if s[0]=='.text'][0]
code=d[txt[3]:txt[3]+txt[4]]
for pat in [b'Paramter NOT Match',b'File Size Paramter Lost',b'EC file %s checksum',b'File Size: %dK',b'File Open Fail',b'Wrong Parameter',b'-- Verify Fail. \n',b'-- Programing OK']:
    for m in re.finditer(pat,d):
        r=f2r(m.start())
        hits=[]
        for i in range(len(code)-7):
            if code[i+1]==0x8d and code[i] in(0x48,0x4c) and (code[i+2]&0xc7)==5:
                t=txt[1]+i+7+struct.unpack_from('<i',code,i+3)[0]
                if t==r:hits.append(hex(txt[1]+i))
        print(pat,hex(r),hits)
print('text',hex(txt[1]),hex(txt[3]),hex(txt[4]))
