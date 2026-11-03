# 14 — Flash EC fallito (brick) e acquisto del chip IT5571 da terze parti

## 1. Cosa succede se il flash dell'EC fallisce

- La **boot ROM è ROM mascherata dentro il chip**: un flash corrotto non la damages.
  Se la 16B-signature a `0x40` sparisce/corrompe, il power-on detection non trova la code
  base e l'EC resta in modo ISP/bootloader.
- **Sintomi tipici di EC brickato**: la macchina non si accende (l'EC gestisce il power
  sequencing), oppure si accende ma niente tastiera, no ventole controllate, no ricarica
  batteria, no risposta ai tasti; a volte ventola al massimo. Il BIOS (flash separata)
  resta intatto.
- **Recovery**: la boot ROM è viva → **ISP via connettore KBS** (adattatore DB25, pinout
  datasheet §7.24.3.1) con il tool ITE → riscrivi il dump originale (`EC0416.BIN`,
  sha256 `acaf8fed…`) → l'EC riparte. Funziona anche con flash completamente garbage,
  purché il chip sia elettricamente vivo e VSTBY presente. È il motivo per cui il backup
  dump va tenuto.
- **Verifica sempre post-write** (`-v` / ri-dump + hash): un write interrotto a metà può
  lasciare la signature a metà → brick evitabile.
- Se il **chip è morto elettricamente** (es. 5V da CH341A non moddata, sovratensione,
  ESD): ISP non serve → va sostituito il chip (rework BGA) oppure l'intera scheda.

## 2. Comprare il chip IT5571 da terze parti

Sì, si trova (verificato oggi):

- **JLCPCB/LCSC**: `IT5571E-128/CX` (LQFP-128, C24833823) e `IT5571VG-128/CX`
  (VFBGA-128 7×7, C7429720) — "New Arrivals", ROHS, pochi USD.
- **AliExpress/eBay/PolarTech**: IT5571VG-128/256, IT5571E-128, IT5570E-128 (QFP/BGA),
  nuovi/OEM, pochi € a pezzo.
- **Fornitori repair con chip pre-programmati per modello** (es. icchipforlaptop.com):
  EC chip già flashati per la scheda specifica.

**Attenzione però**:

- Un chip **nuovo ha la eFlash vuota** → va programmato. Il **T48 non supporta ITE**
  (verificato, doc 12) → dopo il rework BGA si programma via **ISP su KBS** o via LPC,
  oppure si compra un programmatore ITE dedicato (es. "ITE Download Board 4", vedi
  Badcaps per IT8390/IT5570/IT5571).
- **Package e flash size devono combaciare con la scheda**: `E-128/CX` = LQFP-128,
  `VG-128` = VFBGA-128 7×7, `-128` = 128 KiB. La famiglia IT5570/IT5571/IT8571 è
  compatibile hardware, ma il **firmware è board-specific** (EC0416 = X210AI): un chip
  generico va flashato con il tuo dump.
- In pratica: se è fallito solo il **flash** → non comprare nulla, riflash via ISP (KBS).
  Compri il chip solo se il chip è **fisicamente morto**; in quel caso preferisci un chip
  **pre-programmato per il modello esatto**, altrimenti blank + ISP dopo il rework.
