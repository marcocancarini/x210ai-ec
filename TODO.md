# TODO — X210AI EC (IT5571) — prossimi passi

Stato: analisi statica completa (vedi README.md). Verifiche indipendenti rifatte il 2026-11-04:
hash, patch (2 byte @0x0D17/0x0D5B, 1 byte @0x0C35), signature @0x40, firma @0x7F80, mappa banchi,
tabella set2→set1 @0x0D03 — tutte confermate.

## Sessione 2026-11-04 (hardware reale)

- [x] Dump BIOS: `Bios dumps/full.bin` + `full2.bin`, 33554432 B (32 MiB), sha256 `dd6e3116…4669`
  identici, flash descriptor `0x5AA5F00F` a 0x10 valido → **dump BIOS OK**, recovery BIOS coperta
- [x] Analisi `chiavetta usb/ifu.efi` (ITE Flash Utility 2.3.1a, PE32+ DEBUG, sha256 `16c08273…8176`):
  opzioni `/S`(nascosta) `/V /VB /VBF /BK /Mn /Bp /PB /T /k /j /O`; ramo /S a RVA 0x5174 → routine
  lettura RVA 0x422c (fast read 0x0B, blocchi 32 KiB, fwrite su ITEFW.bin); **se size=0 salta tutto
  e crea file vuoto** (jle a 0x43a2)
- [ ] Dump EC software: `ifu.efi /S 128` → **FALLITO**: `ITEFW.bin` 0 byte, `SPIDeviceID= FF FF FF FF`,
  ACK ok, spegnimento brusco (0xFE, normale). Buffer 0x62 svuotato prima (0x66=0x00), alim. DC+batteria.
  `EC versions/EC0400_dump1/2.bin` vuoti. Conclusione: via software ifu non funzionante su questa scheda
  (mai testata prima, README §6) → **passare a RP2040**
- [ ] Dump BIOS prima di qualsiasi flash: `fpt.efi -d full.bin` o `flashrom -p internal -r full.bin` (oggi nessuna immagine di recovery esiste)
- [ ] Cicalino 15 segnali KSO/KSI dal connettore tastiera ai pin EC (tabella §7 README; KSO1 foto=contatto 16 vs schema 18 — ricontrollare) → chiude mappa EPP per RP2040
- [ ] Misurare EC_SPI1 contatti 1, 3, 7, 8, 9, 10 (massa, EC 119 = GPG6, EC 100 = GPG2, SMBus 87/88, 115/116, 117/118); FSPI già mappata sui contatti 2,4,5,6
- [ ] Identificare pin Fn (HOTKEY contatto 1 → pin EC) e confermare che il caso `0x84` a `0x0C31` sia davvero Fn
- [ ] Chiarire byte `0x4A-0x4B` (`26 E6` in EC0416, `F9 0C` nella build vecchia): checksum? Finché non si sa, le patch restano non provate su hardware
- [ ] ISP via RP2040 in SOLA lettura: `isp hello / lines / enter --mode powerup / id / read -o x210ai-ec.bin -s 128 --no-exit` — mai `write` prima di verifica dump
- [ ] Acquisire immagine BIOS mancante (`MTLH-NB06_B0.2.bin`) e `acpidump` dalla macchina → chiudere analisi causa brick in `ifu` (byte residuo su porta 0x62 → "EC ACK Fail" → cancellazione blocco 0 → "Verify Fail" → brick)

## Regole di sicurezza (da README §5, §6, §9)

- Mai писать prima di una lettura verificata; prima scrittura = singolo settore riscritto con il proprio contenuto (`-R`)
- Patch: 16B-signature @0x40 intatta, tabelle non spostate, non toccare gestore `0xDC`/ciclo flash
- ifu: svuotare buffer porta 0x62 prima (bit0 di 0x66), usa sempre parametro `128`, fotografa lo schermo, mai sola USB-C
- EC_SPI1: non alimentare la scheda dal connettore, non forzare gli strap test mode (FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2) durante l'accensione, livelli max 3,3 V
