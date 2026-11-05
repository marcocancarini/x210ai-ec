# TODO — X210AI EC (IT5571)

Stato al 2026-11-05: sulla scheda c'è `EC-V0.4.0-all-keys.bin`, con tasti ISO e JIS, scambio Fn↔L-Ctrl, Back, Forward, ThinkVantage, rilascio di Fn e combinazioni con Fn confermati. Versioni e procedure in [`firmware/README.md`](firmware/README.md), analisi in [`README.md`](README.md).

## Da fare

### Firmware

- [ ] Registrare l'hash del dump di `all-keys`: deve iniziare con `d96e1b3e6a4f`, poi salvarlo in `dumps/ec/`
- [ ] Decodificare cosa cambia tra `EC0416` e `V0.4.0` (driver SMBus, logica banchi 1 e 2)
- [ ] Capire se il CRC viene controllato dalla boot ROM

### Recovery e hardware

- [ ] Cicalino 15 segnali KSO/KSI dal connettore tastiera ai pin EC (README §7; KSO1 foto = contatto 16, schema = 18). Chiude la mappa EPP per RP2040
- [ ] ISP via RP2040 in SOLA lettura: `isp hello / lines / enter --mode powerup / id / read -o x210ai-ec.bin -s 128 --no-exit`. Mai `write` prima di verificare il dump
- [ ] Misurare `EC_SPI1` contatti 1, 3, 7, 8, 9, 10 (massa, EC 119 = GPG6, EC 100 = GPG2, SMBus 87/88, 115/116, 117/118). FSPI già mappata sui contatti 2, 4, 5, 6
- [ ] Misurare se la scheda ha un pull-up esterno sulla linea HOTKEY

### BIOS

- [ ] Decidere se `dumps/bios/` deve restare nella repo: i dump possono contenere dati della macchina, e toglierli richiede di riscrivere la cronologia
- [ ] Analizzare `dumps/bios/BIOS-X210AI-20261104-lettura1.bin` (32 MiB, due letture identiche) prima di considerarlo immagine di recovery
- [ ] Trovare `MTLH-NB06_B0.2.bin` e fare un `acpidump` della macchina, per chiudere l'analisi del brick in `ifu`: byte residuo su porta 0x62 → `EC ACK Fail` → cancellazione del blocco 0 → `Verify Fail`

## Fatto

- [x] Dump BIOS: 33554432 byte, sha256 `dd6e3116…4669`, due letture identiche, flash descriptor valido a `0x10`
- [x] Analisi di `usb-tools/ifu.efi` (ITE Flash Utility 2.3.1a, sha256 `16c08273…8176`): `ifu.efi /S 128` da solo dà 0 byte perché il reset `0xFE` precede `fclose`
- [x] Dump EC con `ifu.efi /S 128 /k /j`: firmware originale `V0.4.0` del 2025-07-23
- [x] CRC `0x4A-0x4B`: CRC-16/CMS sull'immagine esclusa la firma, confermato su tre build (README §3)
- [x] Patch `V0.4.0` con `tools/patch_keyboard.py` e verifica con `tools/emulator/`
- [x] Quattro flash riusciti con `ifu`: `EC0416`, `iso-jis`, `iso-jis-fn-ctrl-swap`, `all-keys`
- [x] Tasti ISO e JIS, Back, Forward e ThinkVantage confermati con `evtest`
- [x] Rilascio di Fn prima del tasto e combinazioni con Fn confermati sulla scheda
- [x] HOTKEY arriva a GPH7 e il contatto 36 è a massa: dedotto dallo scambio funzionante, senza misure

## Regole di sicurezza (README §5, §6, §9)

- Mai scrivere prima di una lettura verificata. Prima scrittura via ISP: un solo settore riscritto con il proprio contenuto (`-R`)
- Patch: 16B-signature a `0x40` intatta tranne il CRC `0x4A-0x4B` da ricalcolare, tabelle non spostate, non toccare gestore `0xDC` e ciclo di flash
- `ifu`: controllare la porta `0x66`, usare sempre il parametro `128`, fotografare lo schermo, mai sola USB-C
- `EC_SPI1`: non alimentare la scheda dal connettore, non forzare gli strap test mode (FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2) all'accensione, livelli massimi 3,3 V
- Connettore tastiera: scambiarlo solo a macchina spenta, senza alimentatore e batteria
