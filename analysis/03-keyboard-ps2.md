# 03 — Tastiera PS/2: funzionamento (ITE IT5571 + firmware EC0416)

## 1. Blocchi hardware (datasheet IT5570/IT5571)

- **KB Matrix Scan Controller (KBS)**: matrice 18×8 (KSO out 18 bit, KSI in 8 bit),
  base registri EC **0x1D00h** (datasheet §7.4, Table 7-8): `KSOL@1D00h`, `KSOH1@1D01h`,
  `KSOCTRL@1D02h`, `KSOH2@1D03h`, `KSIR`, `KSICTRLR`, `KSIGCTRLR/KSIGOENR/KSIGDATR`,
  `KSOxLSDR` (scan data per riga KSO0–KSO17). KSI/KSO sono muxabili come GPIO (Table 7-7).
- **PS/2 interface**: 2 porte PS/2 (Table 7-17), hardware/software mode.
- **KBC 8042-style**: legacy porte host **0x60 (data) / 0x64 (status+command)**, IRQ1/IRQ12,
  Fast A20G e KB reset. EC view (Table 6-34): `KBHICR@+00h`, `KBIRQR@+02h`, `KBHISR@+04h`,
  `KBHIKDOR@+06h`, `KBHIMDOR@+08h`, `KBHIDIR@+0Ah`; KBDIR/KBDOR/KBCMDR/KBSTR = legacy 0x60.
- Altri base utili: SMFI `0x1000h` (ECINDAR `0x103B-0x103F`, FLHCTRL `0x1031/0x1032`),
  INTC `0x1100h`, EC2I `0x1200h`, **Bank `0x1300h`**, Common `0x1400h`, PMC `0x1500h`, GPIO `0x1600h`.

## 2. Mappa firmware (banco 0)

| Indirizzo | Funzione |
|---|---|
| xdata `0x004B` / `0x004C` | KBC status / data (specchio porte host `0x64`/`0x60`) |
| `0x1300–0x1308` | modulo Bank (selettore banco / kontrol) |
| `0x0A5C`, `0x0B12` | config KBC (bit su `0x1300/0x1304/0x1306/0x1308`) |
| `0x0A76` | init KBC: Timer0 `TH0=0xB2 TL0=0x19` (timeout clock PS/2), `SETB 0x8E` (IE serial), poll `0x1304` |
| `0x0AA3`, `0x0ABE` | scrittura/lettura porta dati host con poll OBF/IBF (bit `0xE0/0xE1` di ACC su `0x1304`) |
| `0x0AF1`, `0x0B0E` | write byte verso dispositivo + poll stato |
| `0x0D9C` | **dispatcher eventi**: flag bit RAM `0x30–0x3D` → handler `0x0FC7, 0x0EB9, 0x0B33, 0x2BA7…0x2BCF, 0x0E80, 0x0820` (comandi PS/2: 0xED LED, 0xF0 scancode set, 0xF3 typematic, 0xF4/F5 enable, 0xFF reset…) |
| `0x2B6B–0x2BE0` | trampoline "software interrupt": `MOV DPTR,#handler_bank1; AJMP 0x2800` |
| `0x2800` | dispatcher comune (impila falso frame, salta all'handler nel banco commutabile) |

## 3. Catena di conversione scancode (il "convertitore PS/2")

Flusso: **KBS matrix scan → (row,col) → scancode set 2 → conversione set 1 → buffer KBC → porta 0x60 + IRQ1**.

| Elemento | Indirizzo | Note |
|---|---|---|
| Tabella **set-2 → set-1** (128 byte) | `0x0D03–0x0D82` | verificata: `5A→1C` (Enter), `29→39` (Spazio), `12→2A` (LShift), `0D→0F` (Tab), `0E→29` (`) |
| Routine conversione | `0x0C09` | `0xF0` (break) → marker `0xFF`; casi speciali `0x83→0x41` (F7), `0x84→0x54`; bit `0xE7` → lookup tabella; break → `\|0x80` |
| Tabella tasti estesi `0xE0` | `0x305E` | coppie `(flag, scancode)`: frecce `6B/72/74/75`, Ins `70`, Del `71`, PgUp/PgDn `7D/7A`, keypad… |
| Sequenze multi-byte | `0x25B2` | `E0 F0 xx` (break E0), `E0 xx` (make E0), `E1 14 77` / `E1 F0 14 F0 77` (Pausa), `E0 7E` (Bloc Scorr) |
| Tabella comandi PS/2 | `0x2636` | `F5 F4 F3 ED …` (letta dal banco 1 a `0xA8B0` con `MOVC`) |
| Tabelle byte di risposta | `0x2643` / `0x2645` | loop di invio a `0xB293–0xB2BE` |
| Tabella matrice | `0x2119` | coppie `1C xx`, usata da `0x1235A` (`LCALL 0x21A5`) |
| Buffer stato scan | xdata `0x0771/0x0772` | letti in banco 1 (`0xA8A9–0xA8E9`) |

## 4. Note per il patching della tastiera

- La tabella set2→set1 a `0x0D03` è il punto per rimappare i tasti (es. Fn → altro tasto):
  basta patchare la entry corrispondente; la routine `0x0C09` applica poi break (`|0x80`).
- I tasti `0xE0` sono decisi dalla tabella a `0x305E`; le sequenze speciali (Pausa) a `0x25B2`.
- Non spostare queste tabelle: sono referenziate con `DPTR` assoluti (`MOV DPTR,#0x0D03` ecc.).
