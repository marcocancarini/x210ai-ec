# 13 — Livello Fn / ThinkLight (Fn+PgUp) e estrazione del dump EC

## 1. La patch Fn→Ctrl tocca la rilevazione del "livello Fn"?

**No.** La patch (`0x0C35`: `0x84 → 0x1D`) agisce solo sul byte di *output scancode*
nella routine di conversione `0x0C09`. Il "livello Fn" (il flag interno che fa sì che
Fn+tasto produca la funzione speciale, es. Fn+PgUp = ThinkLight) è impostato dal gestore
del pin Fn dedicato (fuori matrice), **a monte e indipendentemente** dalla conversione
scancode → la patch non lo tocca.

Attenzione però a un punto di onestà: nei sorgenti analizzati `0x84` nel caso speciale
della conversione mappa a set-1 `0x54` (tasto vendor), e gli altri hit di `0x83/0x84`
(PMC `0x1500/0x1501`, es. NEW `0xDB27/0xDB36`, OLD `0xDD8A/0xDD99`) sono codici evento ACPI,
non Fn. Quindi **non è certo che `0x84` sia Fn**: la patch rende "il codice interno
`0x84`" pari a LCtrl; se su questa board Fn non passa da `0x84`, l'effetto Fn→Ctrl non
si manifesta. La verifica del livello Fn va fatta sul pin dedicato (schema board).

Sul perché nella **versione vecchia** Fn+PgUp (ThinkLight) non andava: le tabelle tastiera
sono identiche (doc 06), ma il codice banco 0/1 differisce (build MTLH-NB06 vs X210AI);
il livello Fn è gestito nel codice (pin Fn + flag), non nelle tabelle → la causa è in
quel codice, non nelle tabelle scancode.

## 2. Estrarre un dump dell'EC

Verificato: `bios_backup.rom` (12 MiB) **non contiene l'EC** (nessuna 16B-signature, nessuna
stringa `ITE EC-V`/`V0.3.2`) → la eFlash del IT5571 è solo embedded, non nel dump BIOS.

Modi per estrarre il dump EC (128 KiB):

1. **ISP via KBS** (consigliato, a macchina spenta): adattatore DB25 sul connettore
   tastiera (pinout datasheet §7.24.3.1) → boot ROM in modo programmazione → tool ITE
   fa read della flash → `EC_dump.BIN` (128 KiB). Poi `sha256sum` vs `acaf8fed…`.
2. **Tool ITE da UEFI**: `ifu.efi` (nel pacchetto `inputs/bios/extracted/`? no — in
   `MTLH-NB06-ec-250322/ifu.efi` e nel pacchetto BIOS) — oltre a scrivere, le build IFU
   supportano il dump; oppure `fpt.efi -d full.bin` (dump della SPI host: include solo BIOS,
   non l'EC embedded — verificato sopra).
3. **Da Linux sul sistema avviato**: `flashrom -p internal -r full.bin` legge la flash
   sull'SPI host (BIOS); l'EC embedded non è lì. Per l'EC via host: `fpt.efi`/tool ITE
   through LPC (HLPC, datasheet §6.4.3.8/9).
4. **Debug I2EC** (datasheet §7.23.3.5): se abilitato lato EC, si legge/scrive la memoria
   EC via LPC I/O `2Eh/2Fh` — utile per dump parciali/debug, non per flash intera.

Verifica dump: size 131072, 16B-signature a `0x40`, sha256 vs `acaf8fed…` (EC0416).
