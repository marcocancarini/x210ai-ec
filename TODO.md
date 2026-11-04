# TODO — X210AI EC (IT5571) — prossimi passi

Stato: analisi statica completa (vedi README.md). Eseguito su hardware solo `ifu` in lettura; nessuna scrittura provata.
Verifiche indipendenti rifatte il 2026-11-04: hash, patch (2 byte @0x0D17/0x0D5B, 1 byte @0x0C35),
signature @0x40, firma @0x7F80, mappa banchi, tabella set2→set1 @0x0D03 — tutte confermate.

## Priorità

- [x] Dump EC software: `ifu.efi /S 128 /k /j` (sola lettura, `/S 128` da solo dà 0 byte). Risultato: firmware installato `V0.4.0` 2025-07-23, più recente di `EC0416` (`dumps/EC-V0.4.0-20250723-lettura*.bin`)
- [ ] Verificare e analizzare `Bios dumps/full.bin` (32 MiB, 2 letture identiche) prima di considerarlo immagine di recovery
- [ ] Annotare come si comporta la macchina a fine dump con `/j`: ritorno al prompt, tastiera, `reset -s`
- [x] Patch tastiera `V0.4.0` (ISO/JIS, Fn↔LCtrl): `tools/patch_keyboard.py`, solo verifica statica
- [ ] Provare le patch `V0.4.0` solo dopo la recovery ISP; non flashare `EC0416` né `EC0416_*.BIN` senza decidere il downgrade (README §9)
- [ ] Decodificare cosa cambia tra `EC0416` e `V0.4.0` (driver SMBus, logica banchi 1 e 2)
- [ ] Cicalino 15 segnali KSO/KSI dal connettore tastiera ai pin EC (tabella §7 README; KSO1 foto=contatto 16 vs schema 18 — ricontrollare) → chiude mappa EPP per RP2040
- [ ] Misurare EC_SPI1 contatti 1, 3, 7, 8, 9, 10 (massa, EC 119 = GPG6, EC 100 = GPG2, SMBus 87/88, 115/116, 117/118); FSPI già mappata sui contatti 2,4,5,6
- [ ] Confermare con il cicalino che HOTKEY (contatto 1) arrivi al pin EC di `0x1608` bit 7. Il caso `0x84` a `0x0C31` non è Fn: è Alt+SysRq
- [ ] Chiarire byte `0x4A-0x4B` (`26 E6` in EC0416, `F9 0C` nella build vecchia): checksum? Finché non si sa, le patch restano non provate su hardware
- [ ] ISP via RP2040 in SOLA lettura: `isp hello / lines / enter --mode powerup / id / read -o x210ai-ec.bin -s 128 --no-exit` — mai `write` prima di verifica dump
- [ ] Acquisire immagine BIOS mancante (`MTLH-NB06_B0.2.bin`) e `acpidump` dalla macchina → chiudere analisi causa brick in `ifu` (byte residuo su porta 0x62 → "EC ACK Fail" → cancellazione blocco 0 → "Verify Fail" → brick)

## Regole di sicurezza (da README §5, §6, §9)

- Mai писать prima di una lettura verificata; prima scrittura = singolo settore riscritto con il proprio contenuto (`-R`)
- Patch: 16B-signature @0x40 intatta, tabelle non spostate, non toccare gestore `0xDC`/ciclo flash
- ifu: svuotare buffer porta 0x62 prima (bit0 di 0x66), usa sempre parametro `128`, fotografa lo schermo, mai sola USB-C
- EC_SPI1: non alimentare la scheda dal connettore, non forzare gli strap test mode (FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2) durante l'accensione, livelli max 3,3 V
