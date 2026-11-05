import sys
p='README.md'; s=open(p,encoding='utf-8').read()
def R(a,b):
    global s
    if s.count(a)!=1: sys.exit('NOMATCH %d: %s'%(s.count(a),a[:70]))
    s=s.replace(a,b)
R("5. Ricreare le patch tastiera sulla `V0.4.0` (§5).\n","5. Provare le patch `V0.4.0` solo dopo aver verificato la recovery (§5, §9).\n")
R("""| `dumps/EC0416.BIN` | `acaf8fed""","""| `dumps/EC-V0.4.0-iso-jis.bin` | `133564d2a2fdda1bf0f90fa39e1ed4f3b79eeba7821ecafc0d2e7107d9affeaf` | `V0.4.0` con tasti ISO e JIS (7 byte), mai provata |
| `dumps/EC-V0.4.0-fn-ctrl-swap.bin` | `a0b07b248ef3e4713a98bc0f69402bcbe850de430981f7c08a28b77ebb6fac22` | `V0.4.0` con scambio Fn↔LCtrl (3 byte), mai provata |
| `dumps/EC-V0.4.0-iso-jis-fn-ctrl-swap.bin` | `3dfe2965ba0221c617ed04be8497b4834375cc84cdb844b09fe7fefaf27b2bba` | Entrambe (10 byte), mai provata |
| `dumps/EC0416.BIN` | `acaf8fed""")
R("""| `dumps/EC0416_fn-ctrl-swap.BIN` | `970431688f10aa160973d3f276c453e5cc86427a28a01ee34ef43ea17dfabee8` | Patch Fn→LCtrl (1 byte) |""",
  """| `dumps/EC0416_fn-ctrl-swap.BIN` | `970431688f10aa160973d3f276c453e5cc86427a28a01ee34ef43ea17dfabee8` | **Errata, non usare:** cambia Alt+SysRq, non Fn (§5) |""")
R("""- **KBS matrix 18×8** (base `0x1D00h`: KSOL/KSOH1/KSOCTRL/KSOH2/KSI@`0x1D04`/KSOxLSDR `0x1D10-0x1D21`). Driver in banco1 `0x9300-0x9F00`: loop 16 righe KSO, legge KSI, indice `0x4D=(col<<4)|row|0x08`.
- **Conversione scancode**: routine `0x0C09` (F0→break marker 0xFF, bit E7→casi speciali `0x83→0x41`/`0x84→0x54`, break `\\|0x80`) e tabella **set2→set1 `0x0D03`** (128 B). Estesi `0xE0`: tabella `0x305E`; sequenze multi-byte (Pausa `E1 14 77`): `0x25B2`; comandi PS/2: `0x2636`.
""","""- **KBS matrix 18×8** (base `0x1D00h`: KSOL/KSOH1/KSOCTRL/KSOH2/KSI@`0x1D04`/KSOxLSDR `0x1D10-0x1D21`). Driver in banco1 `0x9300-0x9F00`: loop 16 righe KSO, legge KSI, indice `0x4D=(col<<4)|row|0x08`.
- **Tabella matrice `0x2EB9`:** 128 byte, indice `(KSI<<4)|KSO` (`0x8CB2`). Identica in `EC0416` e `V0.4.0`. La tabella `0x2F39` (24 byte, 2 KSO extra) è vuota. Le voci sono codici interni, non scancode (vedi sotto).
- **Codici interni** (`0x8D77`): `<0x80` set 2 diretto; `0x80-0x9B` tabella `0x3060` (`0x82` LWin, `0x84` Menu, `0x88` LShift, `0x89` RShift, `0x8A` LAlt, `0x8B` RAlt, `0x8C` LCtrl, `0x8D` RCtrl, `0x8E` Fn); `0x9C-0xDF` varianti a `0x2FE3`; `≥0xE0` coppie normale/Fn a `0x3046`.
- **Fn:** non è in matrice. È il pin `0x1608` bit 7 (attivo basso, `0xC447`), con debounce nella voce 4 della tabella `0x2795`. Pressione e rilascio chiamano `0x8D77` con `0x8E` (`0xC45E`, `0xC465`), che imposta il bit `0x40` dello stato tastiera in iRAM `0xBC`. Quel pin non viene letto altrove.
- **Conversione scancode**: routine `0x0C09` (F0→break marker 0xFF, bit E7→casi speciali `0x83→0x41`/`0x84→0x54`, break `\\|0x80`) e tabella **set2→set1 `0x0D03`** (128 B). Qui `0x83` e `0x84` sono byte set 2 già in uscita: F7 e Alt+SysRq. Sequenze multi-byte (Pausa `E1 14 77`): `0x25B2`; comandi PS/2: `0x2636`.
""")
R("""- **ISO/JIS:** la matrice ha 144 posizioni e la tabella `0x0D03` copre tutti i set-2 `0x00-0x7F`, incluso il tasto extra ISO `0x61→0x56`. Il layout fisico dipende dal cablaggio della tastiera.
- **Build vecchia e `EC0416`:** tabelle set2→set1 (`0x0D2C` vs `0x0D03`), matrice, estesi e sequenze sono identiche, quindi ISO e JIS sono supportati in entrambe. Se nella vecchia ù/<> non passavano all'OS, o Fn+PgUp non funzionava, la causa è nel codice di scansione o di gestione Fn di quella build, non nelle tabelle.
""","""- **ISO/JIS:** la tabella `0x0D03` copre tutti i set-2 necessari, ma **la matrice no**: le celle dei tasti ISO e JIS sono a `0x00`, e `0x8D77` scarta quel codice. Da qui il sintomo di `ù` e `<>` che non arrivano all'OS, in tutte le build viste.
- **Confronto con ThinkPad:** la matrice coincide, trasposta, con la X220 di [thinkpad-ec](https://github.com/hamishcoleman/thinkpad-ec/blob/master/docs/table_matrix.txt): 88 celle occupate in comune e 52 tasti di scrittura su 52 con il codice atteso. Lì i codici sono numeri di tasto IBM, quindi quelli "sconosciuti" sono 14 Yen, 131 Muhenkan, 132 Henkan e 133 Kana. Differenze: LWin sta in `KSI2/KSO11` invece di `KSI3/KSO9`, e qui mancano ThinkVantage, Mic e PgBk/PgFd. Il confronto con una tastiera X201 reale non è stato fatto.
""")
R("""**Vale solo per `EC0416`:** i file `EC0416_*.BIN` sono basati sulla `V0.3.2` e flasharli riporterebbe indietro il firmware installato (§9). Sulla `V0.4.0` i byte `0x0C35`, `0x0D17` e `0x0D5B` stanno agli stessi indirizzi, con gli stessi valori e lo stesso contesto, quindi le patch si possono ricreare sul dump. Non è ancora stato fatto.
""","""**Patch per il firmware installato.** `tools/patch_keyboard.py` parte dal dump `V0.4.0`, ne controlla l'hash e i byte attesi, e genera i tre file `dumps/EC-V0.4.0-*.bin` (§1). **Verificate solo staticamente, mai flashate.** Se i byte `0x4A-0x4B` (§3) fossero un controllo, l'immagine modificata potrebbe non partire: prima serve la recovery (§9).

| Byte | Da → a | Effetto |
|---|---|---|
| `0x2F0A` (`KSI5/KSO1`) | `00 → 61` | ISO `<>` |
| `0x2F20` (`KSI6/KSO7`) | `00 → 5D` | ISO `#`, `ù` su layout italiano |
| `0x2EE1` (`KSI2/KSO8`) | `00 → 6A` | JIS Yen |
| `0x2F2E` (`KSI7/KSO5`) | `00 → 51` | JIS Ro |
| `0x2F29` (`KSI7/KSO0`) | `00 → 67` | JIS Muhenkan |
| `0x2F0F` (`KSI5/KSO6`) | `00 → 64` | JIS Henkan |
| `0x2F2F` (`KSI7/KSO6`) | `00 → 13` | JIS Katakana/Hiragana |
| `0x2EC8` (`KSI0/KSO15`) | `8C → 8E` | Il tasto LCtrl fa da Fn |
| `0xC461`, `0xC468` | `8E → 8C` | Il tasto Fn fa da LCtrl |

Le celle ISO/JIS erano vuote: se su una tastiera non c'è il tasto, non cambia nulla. Le posizioni vengono dalla X220 e vanno confermate sulla tastiera reale. RCtrl non cambia.

**Patch `EC0416` (basate sulla `V0.3.2`):** flasharle riporterebbe indietro il firmware installato (§9).
""")
R("""- **Fn→LCtrl:** Fn è **fuori matrice** (pin dedicato, tipo T61 I/O18→GND, rif. github.com/thedalles77/USB_Laptop_Keyboard_Controller) e non è uno scancode. Non c'è logica di swap né flag BIOS (BRAM `0x2200h` non usata come setting). La patch `dumps/EC0416_fn-ctrl-swap.BIN` cambia 1 byte a `0x0C35` (caso `0x84` in `0x0C09`: `0x54→0x1D`).
- **Limite:** non è confermato al 100% che `0x84` sia Fn. Nello schema della tastiera X201 (§7) Fn è `HOTKEY` sul contatto 1: seguendolo fino all'EC si identifica il pin. La direzione inversa (Ctrl fisico che fa da Fn) richiede la posizione matrice di Ctrl (driver banco1, indice `0x4D`).
- **Livello Fn:** la patch tocca solo l'output scancode, a valle del flag del pin Fn, quindi Fn+PgUp non è influenzato.

Verifica di `EC0416.BIN` contro `EC0416_fn-ctrl-swap.BIN`:
""","""- **`dumps/EC0416_fn-ctrl-swap.BIN` è errata, non usarla.** Cambia il caso `0x84` in `0x0C09` (`0x54→0x1D`), che è il byte set 2 di Alt+SysRq. Fn è fuori matrice (§4), quindi la patch non lo tocca: trasforma Alt+SysRq in LCtrl. La verifica qui sotto conferma solo quel byte, non il suo significato.
- **Fn e BIOS:** non c'è logica di swap né flag BIOS (BRAM `0x2200h` non usata come setting).

Verifica di `EC0416.BIN` contro `EC0416_fn-ctrl-swap.BIN`:
""")
R("""Emulazione di `0x0C09`: `0x84` → `0x1D`/`0x9D` make/break, stesso output di L-Ctrl (`0x14`); gli altri tasti provati (0x83, 0x14, 0x58, 0x76, 0x5A, 0x29, 0x61) restano invariati.
""","""Emulazione di `0x0C09`: `0x84` → `0x1D`/`0x9D` make/break, stesso output di L-Ctrl (`0x14`); gli altri tasti provati (0x83, 0x14, 0x58, 0x76, 0x5A, 0x29, 0x61) restano invariati.

Riferimento della matrice: [thinkpad-ec, `docs/table_matrix.txt`](https://github.com/hamishcoleman/thinkpad-ec/blob/master/docs/table_matrix.txt).
""")
R("""| Tastiera | Tabella `0x0D03` e routine `0x0C09` identiche e agli stessi indirizzi |""","""| Tastiera | Tabelle `0x0D03` e `0x2EB9` e routine `0x0C09` identiche e agli stessi indirizzi |""")
R("""- Confronto con""" if False else """**Chip morto elettricamente**""","""**Dump con EC brickato:** l'ingresso ISP non dipende dal firmware, quindi la lettura dovrebbe funzionare, ma non è provata. Da sola non ripara nulla: mostra solo cosa è rimasto nella flash. La riparazione è `isp write`, ancora bloccata dai punti aperti di §7.

**Chip morto elettricamente**""")
open(p,'w',encoding='utf-8').write(s)
p='TODO.md'; s=open(p,encoding='utf-8').read()
R("""- [ ] Ricreare le patch tastiera sulla `V0.4.0`; non flashare `EC0416` né `EC0416_*.BIN` senza decidere il downgrade (README §9)
""","""- [x] Patch tastiera `V0.4.0` (ISO/JIS, Fn↔LCtrl): `tools/patch_keyboard.py`, solo verifica statica
- [ ] Provare le patch `V0.4.0` solo dopo la recovery ISP; non flashare `EC0416` né `EC0416_*.BIN` senza decidere il downgrade (README §9)
""")
R("""- [ ] Identificare pin Fn (HOTKEY contatto 1 → pin EC) e confermare che il caso `0x84` a `0x0C31` sia davvero Fn
""","""- [ ] Confermare con il cicalino che HOTKEY (contatto 1) arrivi al pin EC di `0x1608` bit 7. Il caso `0x84` a `0x0C31` non è Fn: è Alt+SysRq
""")
open(p,'w',encoding='utf-8').write(s)
