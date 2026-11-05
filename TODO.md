# TODO — X210AI EC (IT5571) — prossimi passi

Stato: analisi statica completa (vedi README.md). Eseguito su hardware `ifu` in lettura e un flash di `EC0416` originale; immagini modificate mai provate.
Verifiche indipendenti rifatte il 2026-11-04: hash, patch (2 byte @0x0D17/0x0D5B, 1 byte @0x0C35),
signature @0x40, firma @0x7F80, mappa banchi, tabella set2→set1 @0x0D03 — tutte confermate.

## Sessione 2026-11-04 (hardware reale)

- [x] Dump BIOS: `Bios dumps/full.bin` + `full2.bin`, 33554432 B (32 MiB), sha256 `dd6e3116…4669`
  identici, flash descriptor `0x5AA5F00F` a 0x10 valido → **dump BIOS OK**, recovery BIOS coperta
- [x] Analisi `chiavetta usb/ifu.efi` (ITE Flash Utility 2.3.1a, PE32+ DEBUG, sha256 `16c08273…8176`):
  opzioni `/S`(nascosta) `/V /VB /VBF /BK /Mn /Bp /PB /T /k /j /O`; ramo /S a RVA 0x5174 → routine
  lettura RVA 0x422c (fast read 0x0B, blocchi 32 KiB, fwrite su ITEFW.bin); **se size=0 salta tutto
  e crea file vuoto** (jle a 0x43a2)
- [x] Tentativi con `ifu.efi /S 128`: `ITEFW.bin` 0 byte (`EC versions/EC0400_dump1/2.bin`), `SPIDeviceID= FF FF FF FF`, ACK ok,
  spegnimento brusco. Stato 0x66=0x00, alimentazione DC+batteria. Causa: reset `0xFE` prima di `fclose`, non `size=0`. La via software funziona con `/k /j`
- [x] Dump EC software: `ifu.efi /S 128 /k /j` (sola lettura, `/S 128` da solo dà 0 byte). Risultato: firmware installato `V0.4.0` 2025-07-23, più recente di `EC0416` (`dumps/EC-V0.4.0-20250723-lettura*.bin`)
- [ ] Verificare e analizzare `Bios dumps/full.bin` (32 MiB, 2 letture identiche) prima di considerarlo immagine di recovery
- [ ] Annotare come si comporta la macchina a fine dump con `/j`: ritorno al prompt, tastiera, `reset -s`
- [x] Patch tastiera `V0.4.0` (ISO/JIS, Fn↔LCtrl, Back, Forward, ThinkVantage, pull-up e rilascio di Fn): `tools/patch_keyboard.py`, verifica statica ed emulata, mai sull'hardware
- [x] Flash `EC0416` con `ifu`: riuscito sulla scheda; registrare l'hash del dump successivo
- [x] Flash `EC-V0.4.0-iso-jis.bin` e poi `EC-V0.4.0-iso-jis-fn-ctrl-swap.bin` con `ifu`: riusciti, ISO e scambio Fn↔LCtrl funzionanti; registrare l'hash del dump
- [ ] Provare i tasti JIS su una tastiera giapponese
- [ ] Flashare `dumps/EC-V0.4.0-all-keys.bin` (README §9), meglio dopo la recovery ISP; mai `EC0416_*.BIN` (CRC vecchio)
- [ ] Dopo il flash di `all-keys`: registrare l'hash del dump e provare Back, Forward, ThinkVantage e il rilascio di Fn
- [ ] Decidere se i dump BIOS devono restare nella repo: possono contenere dati della macchina
- [ ] Decodificare cosa cambia tra `EC0416` e `V0.4.0` (driver SMBus, logica banchi 1 e 2)
- [ ] Cicalino 15 segnali KSO/KSI dal connettore tastiera ai pin EC (tabella §7 README; KSO1 foto=contatto 16 vs schema 18 — ricontrollare) → chiude mappa EPP per RP2040
- [ ] Misurare EC_SPI1 contatti 1, 3, 7, 8, 9, 10 (massa, EC 119 = GPG6, EC 100 = GPG2, SMBus 87/88, 115/116, 117/118); FSPI già mappata sui contatti 2,4,5,6
- [x] HOTKEY arriva a GPH7 e il contatto 36 è a massa: confermato dallo scambio funzionante, senza misure. Il caso `0x84` a `0x0C31` non è Fn: è Alt+SysRq
- [ ] Misurare se la scheda ha un pull-up esterno sulla linea HOTKEY
- [x] Byte `0x4A-0x4B`: CRC-16/CMS su tutta l'immagine esclusa la firma, confermato su tre build (README §3)
- [ ] Capire se il CRC viene controllato dalla boot ROM
- [ ] ISP via RP2040 in SOLA lettura: `isp hello / lines / enter --mode powerup / id / read -o x210ai-ec.bin -s 128 --no-exit` — mai `write` prima di verifica dump
- [ ] Acquisire immagine BIOS mancante (`MTLH-NB06_B0.2.bin`) e `acpidump` dalla macchina → chiudere analisi causa brick in `ifu` (byte residuo su porta 0x62 → "EC ACK Fail" → cancellazione blocco 0 → "Verify Fail" → brick)

## Regole di sicurezza (da README §5, §6, §9)

- Mai scrivere prima di una lettura verificata; prima scrittura = singolo settore riscritto con il proprio contenuto (`-R`)
- Patch: 16B-signature @0x40 intatta tranne il CRC @0x4A-0x4B da ricalcolare, tabelle non spostate, non toccare gestore `0xDC`/ciclo flash
- ifu: svuotare buffer porta 0x62 prima (bit0 di 0x66), usa sempre parametro `128`, fotografa lo schermo, mai sola USB-C
- EC_SPI1: non alimentare la scheda dal connettore, non forzare gli strap test mode (FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2) durante l'accensione, livelli max 3,3 V
