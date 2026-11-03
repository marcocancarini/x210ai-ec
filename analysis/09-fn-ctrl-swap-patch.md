# 09 — Patch Fn ↔ L-Ctrl sulla nuova EC (EC0416.BIN)

## Contesto (dai doc 05/08)

- Fn è **fuori matrice** (pin dedicato, tipo T61 I/O18→GND), letto dall'EC e gestito
  internamente: non ha uno scancode nella tabella `0x0D03` → **non si scambia via tabella**.
- L-Ctrl è in matrice → set-2 `0x14` → tabella `0x0D03` → set-1 `0x1D` → host.
- Nella routine di conversione `0x0C09` ci sono due casi speciali "fuori range tabella":
  `0x83 → 0x41` (F7) e **`0x84 → 0x54`** — `0x84` è il codice interno del tasto Fn/custom.

## Patch applicata (binario prodotto)

File: `dumps/EC0416_fn-ctrl-swap.BIN`

| Campo | Valore |
|---|---|
| Patch | 1 byte a `0x0C35`: `0x54 → 0x1D` |
| Effetto | `MOV R7,#0x1D` nel caso `0x84` → il codice interno Fn (`0x84`) viene emesso come **set-1 `0x1D` = Left Ctrl** verso l'host |
| sha256 | `970431688f10aa160973d3f276c453e5cc86427a28a01ee34ef43ea17dfabee8` |
| diff vs originale | solo `0x0C35` (verificato) |

Disassembly del punto patchato:

```
0C30: EF        MOV A, R7
0C31: B4 84 04  CJNE A, #0x84, 0x0C38
0C34: 7F 1D     MOV R7, #0x1D     ; patchato (era 7F 54)
0C36: 7E 01     MOV R6, #0x01
```

## Limiti e direzione inversa

- Questa patch rende **Fn → LCtrl** (il tasto Fn invia Left-Ctrl all'OS).
- La direzione inversa (**tasto fisico L-Ctrl che fa da Fn**) richiede di patchare la
  posizione di matrice di L-Ctrl perché emetta il codice interno Fn al posto di `0x14`:
  punto driver scan banco 1 `0x9300-0x9F00`, indice `0x4D=(col<<4)|row|0x08`; serve lo schema
  della scheda per sapere riga/colonna di Ctrl. Senza quello non è un patch byte-safe.
- Verifica pre-flash: `xxd -s 0xC30 -l 8` deve dare `ef b4 84 04 7f 1d 7e 01`.
- Flash: vedi doc 04 (`ifu.efi EC0416_fn-ctrl-swap.BIN 128` da UEFI Shell).

## Variante "solo tasti host" (sempre valida)

Swap di soli tasti visibili all'OS via tabella `0x0D03` (nessun codice toccato):
`dumps/EC0416_ctrl-caps-swap.BIN` (demo Ctrl↔Caps, 2 byte a `0x0D17`/`0x0D5B`).
