import re,sys
p='TODO.md'; s=open(p,encoding='utf-8').read()
c=list(re.finditer(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>> origin/main\n',s,re.S))
assert len(c)==2
first=c[0].group(1)
mine=c[1].group(1).split('\n'); theirs=c[1].group(2)
t=theirs.split('- [ ] Dump EC software:')[0]
dump="""- [x] Tentativi con `ifu.efi /S 128`: `ITEFW.bin` 0 byte (`EC versions/EC0400_dump1/2.bin`), `SPIDeviceID= FF FF FF FF`, ACK ok,
  spegnimento brusco. Stato 0x66=0x00, alimentazione DC+batteria. Causa: reset `0xFE` prima di `fclose`, non `size=0`. La via software funziona con `/k /j`
"""
blk=t+dump+mine[0]+'\n'+'\n'.join(mine[1:])
s=s[:c[0].start()]+first+s[c[0].end():c[1].start()]+blk+s[c[1].end():]
a="- [ ] Chiarire byte `0x4A-0x4B` (`26 E6` in EC0416, `F9 0C` nella build vecchia)"
assert s.count(a)==1
s=s.replace(a,"- [ ] Chiarire byte `0x4A-0x4B` (`AF 5B` in V0.4.0, `26 E6` in EC0416, `F9 0C` nella build vecchia)")
assert '<<<<' not in s
open(p,'w',encoding='utf-8').write(s)
p='README.md'; s=open(p,encoding='utf-8').read()
for a,b in (("- Il comportamento della macchina a fine dump non è stato annotato. L'EC riparte senza un vero reset: spegnere subito con `reset -s`.\n",
 "- Con il solo `/S 128` è stato osservato uno spegnimento brusco. Con `/k /j` il comportamento a fine dump non è stato annotato: l'EC riparte senza un vero reset, quindi spegnere subito con `reset -s`.\n"),
 ("- **Flash ID:** `write` accetta solo `ff ff fe`. Non è verificato che l'IT5571 lo restituisca.",
  "- **Flash ID:** `write` accetta solo `ff ff fe`. Non è verificato che l'IT5571 lo restituisca: `ifu` sulla scheda ha stampato `SPIDeviceID= FF FF FF FF`, che va confrontato con `isp id`.")):
    assert s.count(a)==1,a
    s=s.replace(a,b)
open(p,'w',encoding='utf-8').write(s)
