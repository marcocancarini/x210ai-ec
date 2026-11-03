# 08 — Swap Fn ↔ Ctrl: l'EC lo permette? O è il BIOS?

## Risposta breve

**In questo firmware EC no: non esiste logica di swap Fn↔Ctrl, e non viene letto alcun
flag dal BIOS.** Lo swap va fatto patchando l'EC stesso (livello pin Fn / matrice),
non la tabella scancode.

## Evidenze nel firmware (EC0416.BIN e E03-250322)

1. **Fn non è uno scancode**: è un pin dedicato fuori matrice (reference T61:
   `fn = I/O 18 and ground`). Non compare nella tabella set2→set1 (`0x0D03`/`0x0D2C`)
   né nelle tabelle E0/sequenze → **non si può scambiare via tabella scancode**.
2. **Nessuna logica di swap su Ctrl**: nel path tastiera non c'è alcun confronto su
   `0x14` (LCtrl set-2) o `0x1D` (LCtrl set-1) — searched `CJNE/XRL/ANL A,#0x14|#0x1D`:
   zero hit rilevanti (l'unico `CJNE #0x1D` a `0xDBC3` è un contatore di loop).
3. **BRAM non usata per setting**: la BRAM EC-view (base `0x2200h`, SBT0-191,
   datasheet Table 7-33) — dove il BIOS metterebbe l'opzione "Fn/Ctrl swap" — è
   referenziata solo 2 volte (`0x80F5`, `0xDAC9`), ed è la sequenza di unlock flash
   (`0x22BF=0x55`), non una lettura di setting.

## Come funziona sullo stock ThinkPad

L'opzione "Fn and Ctrl key swap" nel BIOS Setup dei ThinkPad è una feature **BIOS**: il
BIOS scrive un flag nella NVRAM/BRAM dell'EC (via LPC, BRAM host-view legacy `0x70h`+,
Table 7-30) e l'EC stock la legge e scambia. In **questa** build custom (X210AI /
MTLH-NB06) quel codice non c'è: la BRAM non viene letta come setting.

## Come fare lo swap qui (patch EC)

- **Livello scancode (solo tasti host-visibili)**: tabella `0x0D03` — es. demo
  Ctrl↔CapsLock già fatta (`dumps/EC0416_ctrl-caps-swap.BIN`). Fn non è lì dentro.
- **Livello Fn (vero swap Fn↔Ctrl)**: bisogna intervenire dove l'EC legge il pin Fn
  (GPIO/WUI dedicato) e dove la posizione di matrice di L-Ctrl mappa a set-2 `0x14`:
  scambiare i due mapping nel codice/matrice (driver scan banco 1 `0x9300-0x9F00`,
  indice `0x4D=(col<<4)|row`).
