# 11 — Si può scrivere il chip EC (IT5571) direttamente?

## Risposta breve

**No con una clip SOIC: l'IT5571E/VG-128 è VFBGA-128 (BGA 7×7 mm, datasheet Table 4-2 /
§12 package) e la sua flash è embedded nel die** (128 KiB e-flash, datasheet §6.4.3.11 /
features). I pin FSPI (FSCK/FSCE#/FMOSI/FMISO, Table 5-5) sono l'interfaccia per flash
**esterna** ("External Serial Flash Interface") — non espongono la eFlash interna.
Quindi un programmatore SPI (CH341A/T48) non può leggere/scrivere la eFlash del chip
attraverso i pin del package.

## Modi che funzionano davvero per scrivere la eFlash dell'EC

1. **ISP via connettore KBS (in-circuit, senza dissaldare)** — datasheet §7.23.3.3
   ("In-system Programming Operation: flash read and program") e §7.24.3.1: adattatore
   porta parallela DB25 femmina sul connettore tastiera (KSO0-7=PD0-7, KSO8=ACK#,
   KSO9=BUSY, KSO10=PE, KSO12=SLCT, KSI0=STB#). La boot ROM entra in modo programmazione
   e il tool ITE fa read/write della flash. Macchina spenta, standby presente.
2. **Programmatore universale + zoccolo BGA (dopo dissaldatura)** — T48/T56 ecc. con
   adattatore BGA: funziona **solo se il database include l'algoritmo e-flash del IT5571**.
   **Verificato: NO** — nella lista ufficiale T48 (V13.16, 37103 IC, `SupportLists/T48_List.txt`)
   la sezione `[ ITE [Testing] ]` riporta "IC Support: 0 PCS" e non esistono entry
   IT55xx/IT85xx/IT8xxx: il T48 **non** programma gli EC ITE. Quindi questa via è chiusa
   sul T48; resterebbe solo un programmatore con algoritmo ITE in database (non il T48).
3. **Via host LPC/eSPI (HLPC, §6.4.3.8/6.4.3.9)** — flash programming through host LPC
   interface (scratch SRAM / serial-flash follow mode): è quello che fanno
   `fpt.efi` / `flashrom -p internal` / `ifu.efi` (doc 04). Macchina accesa.
4. **Debug I2EC/D2EC (§7.23.3.5)** — snoop/scrittura della memoria EC via LPC I/O
   (porte 2Eh/2Fh o porta dedicata) se abilitata lato EC; utile per dump/debug, non per
   flash routine.

## Nota sul board

Su questa scheda l'EC è la variante con eFlash embedded (EC0416.BIN = 128 KiB): **non
esiste un chip flash EC esterno da clip**are. La flash clip-abile (SOIC-8) è solo quella
del BIOS (vedi doc 10). Se lo schemaünstlera i pin FSPI dell'EC verso un connettore/test
point, allora sì si può clip-pare lì; altrimenti no.

## In pratica

- Dump/flash EC "diretto" senza accendere la macchina: **adattatore parallelo su KBS + tool
  ITE (ISP)** — metodo standard di recovery.
- Dump/flash EC con macchina accesa: `fpt.efi -d/-f`, `flashrom -p internal`, `ifu.efi`.
- Solo se supportato dal database del programmatore: desaldare il VFBGA e scrivere la
  eFlash su zoccolo BGA (T48/T56) — ultima ratio.
