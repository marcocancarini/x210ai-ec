import sys
p='README.md'; s=open(p,encoding='utf-8').read()
def R(a,b):
    global s
    if s.count(a)!=1: sys.exit('NOMATCH %d: %s'%(s.count(a),a[:70]))
    s=s.replace(a,b)
H={}
for l in open(sys.argv[1]):
    h,n=l.split(); H[n]=h
R("| Firmware EC | `EC0416` analizzato, patch verificate staticamente (§2-§5). **Sulla scheda c'è la `V0.4.0`**, più recente: confrontata con `EC0416` (§9) |",
  "| Firmware EC | **Sulla scheda c'è `EC0416` (`V0.3.2`)**, flashata sopra la `V0.4.0` originale. Confronto in §9, patch `V0.4.0` con CRC corretto in §5 |")
R("| Scrittura EC | Rischi documentati (§9). Con RP2040 è possibile, ma con punti aperti (§7) |",
  "| Scrittura EC | **`ifu` ha flashato `EC0416` con successo**, immagini modificate mai provate (§9). Con RP2040 è possibile, ma con punti aperti (§7) |")
R("**Eseguito sulla X210AI:** solo `ifu.efi` in lettura (§6). **Nessuna scrittura è stata provata.** `Fpt.efi` e il percorso di scrittura di `ifu` sono stati solo disassemblati.",
  "**Eseguito sulla X210AI:** `ifu.efi` in lettura (§6) e un flash di `EC0416` originale (§9). `Fpt.efi` è stato solo disassemblato.")
R("5. Provare le patch `V0.4.0` solo dopo aver verificato la recovery (§5, §9).\n","5. Flashare la patch `V0.4.0` con CRC corretto, meglio dopo aver verificato la recovery (§5, §9).\n")
for n,txt in (('EC-V0.4.0-iso-jis.bin','`V0.4.0` con tasti ISO e JIS (7 byte + CRC), mai provata'),('EC-V0.4.0-fn-ctrl-swap.bin','`V0.4.0` con scambio Fn↔LCtrl (3 byte + CRC), mai provata'),('EC-V0.4.0-iso-jis-fn-ctrl-swap.bin','Entrambe (10 byte + CRC), mai provata')):
    import re
    s,c=re.subn(r'\| `dumps/%s` \| `[0-9a-f]{64}` \| [^\n]*\|'%re.escape(n),'| `dumps/%s` | `%s` | %s |'%(n,H[n],txt),s); assert c==1,n
R("| `dumps/EC0416_ctrl-caps-swap.BIN` | `21f63a733dd5ee8b338ffefcda093ffec8d38c38138bc97c1e82a65a20acd406` | Patch demo L-Ctrl↔CapsLock (2 byte) |",
  "| `dumps/EC0416_ctrl-caps-swap.BIN` | `21f63a733dd5ee8b338ffefcda093ffec8d38c38138bc97c1e82a65a20acd406` | Patch demo L-Ctrl↔CapsLock (2 byte). **CRC non aggiornato, non flashare** |")
R("| **Errata, non usare:** cambia Alt+SysRq, non Fn (§5) |","| **Errata, non usare:** cambia Alt+SysRq, non Fn, e ha il CRC vecchio (§3, §5) |")
R("""- **Nessuna firma crittografica trovata**: niente costanti SHA/RSA/MD5/CRC, somme non nulle, blocco `0x7F80` solo testo e non referenziato, reset `0x0070` non verifica la flash, e il firmware non legge da codice la zona `0x40-0x4F`.
""","""- **Nessuna firma crittografica trovata**: niente costanti SHA/RSA/MD5, blocco `0x7F80` solo testo e non referenziato, reset `0x0070` non verifica la flash, e il firmware non legge da codice la zona `0x40-0x4F`.
""")
R("""- **Punto aperto, byte `0x4A-0x4B`:** valgono `26 E6` in `EC0416` e `F9 0C` nella build vecchia, mentre datasheet e System76 hanno `5A 5A` fissi. Non corrispondono a somme a 8/16 bit, XOR o CRC-16 con polinomi noti sugli intervalli provati. Il firmware System76 con `5A 5A` avvia su IT5570, quindi un controllo della boot ROM è improbabile, ma **non escluso** per valori diversi. Nessuna patch risulta provata sull'hardware.
""","""- **CRC a `0x4A-0x4B`:** è un **CRC-16/CMS** big endian (polinomio `0x8005`, init `0xFFFF`, senza riflessione, senza XOR finale) su tutti i 128 KiB esclusi i 16 byte della firma `0x40-0x4F`. Trovato provando tutti i 65536 polinomi su 12 intervalli: è l'unico risultato e torna esattamente sulle tre build ufficiali (`F9 0C` del 22 marzo, `26 E6` di `EC0416`, `AF 5B` della `V0.4.0`). Va **ricalcolato dopo ogni modifica**: `tools/patch_keyboard.py` lo fa, e `--check` verifica un'immagine.
- **Chi controlla il CRC:** non è noto. Il firmware non lo legge, quindi può essere la boot ROM o nessuno. Datasheet e System76 hanno `5A 5A` fissi, e System76 avvia su IT5570: forse è un valore che salta il controllo, ma non è verificato. Un CRC corretto è comunque la scelta prudente.
""")
R("""**Patch per il firmware installato.** `tools/patch_keyboard.py` parte dal dump `V0.4.0`, ne controlla l'hash e i byte attesi, e genera i tre file `dumps/EC-V0.4.0-*.bin` (§1). **Verificate solo staticamente, mai flashate.** Se i byte `0x4A-0x4B` (§3) fossero un controllo, l'immagine modificata potrebbe non partire: prima serve la recovery (§9).
""","""**Patch `V0.4.0`.** `tools/patch_keyboard.py` parte dal dump `V0.4.0`, ne controlla l'hash e i byte attesi, ricalcola il CRC (§3) e genera i tre file `dumps/EC-V0.4.0-*.bin` (§1). Ogni file è verificato per dimensione, vettore di reset, firma e CRC. **Mai flashate:** un'immagine modificata non è ancora stata provata sull'hardware.
""")
R("""| `0xC461`, `0xC468` | `8E → 8C` | Il tasto Fn fa da LCtrl |
""","""| `0xC461`, `0xC468` | `8E → 8C` | Il tasto Fn fa da LCtrl |
| `0x4A-0x4B` | `AF 5B → F1 49` | CRC del file combinato. Vale `44 C4` per ISO/JIS e `1A D6` per lo scambio |
""")
R("""**Regole:** dimensione fissa 128 KiB (pad `0xFF`), 16B-signature intatta, tabelle non spostate (indirizzi assoluti), nessun checksum noto da aggiornare (ma vedi il punto aperto in §3). Una patch""",
  """**Regole:** dimensione fissa 128 KiB (pad `0xFF`), 16B-signature intatta, tabelle non spostate (indirizzi assoluti), CRC `0x4A-0x4B` ricalcolato (§3). Una patch""")
R("""- **`dumps/EC0416_fn-ctrl-swap.BIN` è errata, non usarla.**""","""- **Le patch `EC0416_*.BIN` hanno il CRC vecchio:** non flasharle.
- **`dumps/EC0416_fn-ctrl-swap.BIN` è errata, non usarla.**""")
R("""**Conclusione.** Il confronto non mostra incompatibilità di pin o interfaccia e il percorso di `ifu` non cambia, ma non rende sicuro il flash. Restano valide tutte le debolezze sopra, la scrittura non è mai stata provata su questa scheda e la recovery nemmeno. La lettura `/S` conferma solo ingresso `0xDC`, lettura e uscita `0xFC`.
""","""**Conclusione.** Il confronto non mostra incompatibilità di pin o interfaccia e il percorso di `ifu` non cambia. Restano valide tutte le debolezze sopra e la recovery non è provata.

**Flash reale, 2026-11-05.** `ifu.efi EC0416.BIN 128` da UEFI Shell, sopra la `V0.4.0`: riferito riuscito, macchina funzionante. Con `EC0416` `ù` continua a non funzionare, come atteso: la matrice è la stessa (§4). L'hash del dump successivo al flash non è stato registrato e `evtest` non è stato fatto.
""")
R("""| **EC** (eFlash nel chip) | ISP dal connettore tastiera (§7) + `dumps/EC-V0.4.0-20250723-lettura1.bin` |""","""| **EC** (eFlash nel chip) | `ifu` se l'EC parte, altrimenti ISP dal connettore tastiera (§7), con `dumps/EC-V0.4.0-20250723-lettura1.bin` |""")
open(p,'w',encoding='utf-8').write(s)
p='TODO.md'; s=open(p,encoding='utf-8').read()
R("- [ ] Chiarire byte `0x4A-0x4B` (`AF 5B` in V0.4.0, `26 E6` in EC0416, `F9 0C` nella build vecchia): checksum? Finché non si sa, le patch restano non provate su hardware\n",
  "- [x] Byte `0x4A-0x4B`: CRC-16/CMS su tutta l'immagine esclusa la firma, confermato su tre build (README §3)\n- [ ] Capire se il CRC viene controllato dalla boot ROM\n")
R("- [ ] Provare le patch `V0.4.0` solo dopo la recovery ISP; non flashare `EC0416` né `EC0416_*.BIN` senza decidere il downgrade (README §9)\n",
  "- [x] Flash `EC0416` con `ifu`: riuscito sulla scheda; registrare l'hash del dump successivo\n- [ ] Flashare `dumps/EC-V0.4.0-iso-jis-fn-ctrl-swap.bin`, meglio dopo la recovery ISP; mai `EC0416_*.BIN` (CRC vecchio)\n")
open(p,'w',encoding='utf-8').write(s)
