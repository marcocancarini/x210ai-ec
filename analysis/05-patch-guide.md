# 05 — Guida concreta di patch: rimappatura tasti (es. Fn ↔ Ctrl) e supporto ISO/JIS

Riferimento esterno usato per la decodifica della matrice:
`thedalles77/USB_Laptop_Keyboard_Controller` → `Example_Keyboards/Lenovo_ThinkPad_T61/Teensy 4p0/`
(`keylist.txt`, `Matrix_Decoder_T61.ino`).

## 1. Cosa ci insegna il progetto di riferimento (T61)

`keylist.txt` elenca ogni tasto come `nome <tab> riga <tab> colonna` della matrice del
connettore tastiera (es. `cntrl-l  7  32`, `shift-l  19  28`, `caps-lck  19  31`, `space  23  33`).
Punto chiave:

> **Fn non è nella matrice**: `fn (known to be I/O 18 and ground)` — tasto su pin dedicato
> verso massa, letto separatamente dal controller.

Quindi **Fn non produce uno scancode PS/2**: il controller/EC lo legge a parte e lo usa
internamente (livello Fn per F1–F12, ecc.). Ne consegue che lo "swap Fn↔Ctrl" **non si
può fare nella tabella di conversione scancode** (Fn non c'è): va fatto a livello di
mappatura matrice (scambiare la posizione di Fn con quella di L-Ctrl) oppure a livello di
gestione interna del tasto Fn.

## 2. Punti di patch verificati nel firmware EC0416.BIN

| Livello | Dove | Effetto |
|---|---|---|
| Matrice (riga,colonna)→tasto | driver scan banco 1 `0x9300-0x9F00`: scrive KSO (`KSOL 0x1D00`, `KSOH1 0x1D01`, `KSOH2 0x1D03`), legge `KSI 0x1D04`; indice `0x4D = (col<<4)\|row\|0x08`; regione candidata tabella ~`0x2126` (coppie col→codice set-1) | swap fisico tasti, incl. Fn se in matrice |
| **Scancode set-2 → set-1** | **tabella `0x0D03` (128 byte), `table[set2]=set1`**, usata da `0x0C09` | rimappa globale dei tasti verso l'host |
| Tasti estesi `0xE0` | tabella `0x305E` | flag E0 per frecce/Ins/Del/PgUp/PgDn/keypad |
| Sequenze multi-byte | `0x25B2` (`E0 F0 xx`, `E1 14 77` Pausa…) | make/break tasti speciali |
| Comandi PS/2 | `0x2636` (`F5 F4 F3 ED`…) | comportamento comandi host |

### Demo executabile: swap L-Ctrl ↔ CapsLock (tabella `0x0D03`)

- L-Ctrl = set-2 `0x14` → offset `0x0D03+0x14 = 0x0D17` (valore `0x1D` = set-1 LCtrl)
- CapsLock = set-2 `0x58` → offset `0x0D03+0x58 = 0x0D5B` (valore `0x3A` = set-1 Caps)

Patch: scambiare i due byte → `0x0D17 = 0x3A`, `0x0D5B = 0x1D`.
Binario demo generato: `dumps/EC0416_ctrl-caps-swap.BIN`
- sha256 originale: `acaf8fed…994cb6dca`
- sha256 patchato:  `21f63a733dd5ee8b338ffefcda093ffec8d38c38138bc97c1e82a65a20acd406`
- verifica: diff di **esattamente 2 byte** (`0x0D17`, `0x0D5B`)

Per **Fn↔Ctrl** vero: Fn va intercettato a livello matrice/GPIO (non in `0x0D03`); una volta
trovata la sua posizione (riga,col) nello scan (`0x4D`), si scambia la voce di tabella
corrispondente con quella di L-Ctrl (set-2 `0x14`).

## 3. Procedura operativa di patch e flash

1. **Backup**: dump della flash EC (`fpt.efi -d` / `flashrom -p internal -r` / ISP via KBS)
   e verifica hash (`sha256sum` vs `acaf8fed…`).
2. **Patch**: modificare i byte negli offset indicati; **non cambiare dimensione** (128 KiB,
   pad `0xFF`), **non spostare** tabelle (indirizzi assoluti), **preservare la 16B-signature
   a `0x40`** (vedi doc 02). Nessun checksum interno da aggiornare (nessuno presente).
3. **Verifica statica**: ricontrollare i byte (`xxd -s 0xD17 -l 2`), diff col originale,
   disassembly delle routine toccate (`tools/i8051.py`).
4. **Flash**: UEFI Shell → `ifu.efi EC_patch.BIN 128` (tool ITE, vedi doc 04), oppure
   `flashrom -p internal -w` se la regione è sbloccata, oppure ISP via KBS / programmatore
   esterno. Controllare prima i write-protect (`flashrom --wp-list`).
5. **Verifica dinamica**: ri-dump e confronto hash; test tasti rimappati; test boot.
6. **Rollback**: riflashare il backup originale (da ISP se l'EC non parte).

## 4. Supporto tastiere ISO e Japan (JIS)

Verificato sul firmware + datasheet + riferimento T61:

- **Matrice hardware**: KBS 18×8 = **144 posizioni** (datasheet IT5570 §7.4) — superiore a
  ISO-105 e JIS-109; il layout effettivo dipende dal cablaggio fisico della tastiera
  (come si vede in `keylist.txt` del T61, ~96 tasti usadosu matrice + Fn separato).
- **Copertura scancode**: la tabella set2→set1 `0x0D03` copre **tutti i codici set-2
  `0x00–0x7F`**, incluso il tasto extra ISO `<>|` (set-2 `0x61` → set-1 `0x56`, verificato);
  tabella estesi `0xE0` in `0x305E` (frecce, Ins/Del, PgUp/PgDn, keypad, keypad Enter `/`…);
  sequenze multi-byte in `0x25B2`.
- **Conclusione**: lato EC **ISO e JIS sono supportati** (entro il limite di 144 tasti della
  matrice): la tabella traduce l'intera gamma set-2 più i tasti E0, quindi qualsiasi layout
  ISO/JIS cablato sulla matrice funziona; la scelta ISO/JIS è una proprietà della tastiera
  fisica, non del firmware EC. Il tasto Fn resta gestito fuori matrice (pin dedicato), come
  nel reference T61.
