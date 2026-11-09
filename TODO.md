# TODO — X210AI EC (IT5571)

Stato al 2026-11-07: sulla scheda c'è `EC-V0.4.0-all-keys.bin`, con tasti ISO e JIS, scambio Fn↔L-Ctrl, Back, Forward, ThinkVantage, rilascio di Fn e combinazioni con Fn confermati. Versioni e procedure in [`firmware/README.md`](firmware/README.md), analisi nelle parti di [`docs/`](README.md#parti-del-progetto).

## Da fare

### Repo

- [ ] Tagliare da `storico/` le parti inutili (`storico/README.md`)

### Parte 1: dump e firmware

- [ ] Registrare l'hash del dump di `all-keys`: deve iniziare con `d96e1b3e6a4f`, poi salvarlo in `dumps/ec/`
- [ ] Decodificare cosa cambia tra `EC0416` e `V0.4.0` (driver SMBus, logica banchi 1 e 2)
- [ ] Capire se il CRC viene controllato dalla boot ROM
- [ ] Analizzare `dumps/bios/BIOS-X210AI-20261104-lettura1.bin` (32 MiB, due letture identiche) prima di considerarlo immagine di recovery

### Parte 2: modifiche via software

- [ ] Trovare `MTLH-NB06_B0.2.bin` e usare `storico/diagnostica-20261017/acpi.dat`, per chiudere l'analisi del brick in `ifu`: byte residuo su porta 0x62 → `EC ACK Fail` → cancellazione del blocco 0 → `Verify Fail`

### Parte 3: curve della ventola

- [ ] Capire perché nella prima prova la temperatura EC è rimasta a 54 °C: 2 minuti di letture rapide (52 byte al secondo) contro 2 minuti di letture lente, a riposo (docs 8.2, `storico/test-ventola-20261107/`)
- [ ] Misurare giri, rumore e duty minimo di avvio (docs 3.5)
- [ ] Scegliere una nuova curva
- [ ] Decodificare `0x04FB` e `0x00C2`, che tengono ferma la ventola tramite `0xCE71`

### Parte 4: controllo ACPI

- [ ] Prova di scrittura di un punto della tabella (docs 4.5), per confermare sulla scheda che il comando `0x81` raggiunge la curva
- [ ] Verificare che i valori scritti sopravvivano a riavvio e sospensione
- [ ] Decidere la via definitiva: patch EC, SSDT o coreboot (docs 4.3)

### Parte 8: analisi del firmware delle ventole

- [ ] Dopo le misure, trasformare `tools/emulator/fan_fix.py` in una patch vera: curva, isteresi, errori di temperatura, tachimetro (docs 8.5)
- [ ] Valutare il fail-safe all'avvio: le prime letture PECI possono fallire
- [ ] Coprire anche il caso con il canale OOB fermo, oggi escluso dal controllo errori
- [ ] Decidere se aggiungere una soglia termica nell'EC (L5 in docs 8.2)

### Parte 5 e 6: hardware

Elenco completo delle misure in docs 6.1.

- [ ] Cicalino 15 segnali KSO/KSI dal connettore tastiera ai pin EC (docs 6.3; KSO1 foto = contatto 16, schema = 18). Chiude la mappa EPP per RP2040
- [ ] ISP via RP2040 in SOLA lettura: `isp hello / lines / enter --mode powerup / id / read -o x210ai-ec.bin -s 128 --no-exit`. Mai `write` prima di verificare il dump
- [ ] Misurare `EC_SPI1` contatti 1, 3, 7, 8, 9, 10 (massa, EC 119 = GPG6, EC 100 = GPG2, SMBus 87/88, 115/116, 117/118). FSPI già mappata sui contatti 2, 4, 5, 6
- [ ] Misurare se la scheda ha un pull-up esterno sulla linea HOTKEY
- [ ] Contare le ventole collegate e guardare connettore e fili: due canali PWM nel firmware, una ventola nello chassis
- [ ] Misurare PWM ed eventuale tachimetro sui piedini EC 24, 25, 47, 48
- [ ] Guardare il chip BIOS: marking e misura del package. Modello e tensione già letti: W25Q256JW, 1,8 V
- [ ] Procurarsi l'adattatore WSON-8 per il T48 e preparare il secondo PC con Xgpro

### Parte 7: coreboot

Riferimento: [x210ai-coreboot](https://github.com/marcocancarini/x210ai-coreboot) (non ancora pubblica), `docs/STATO.md`.

- [ ] Seguire la [CL 94886](https://review.coreboot.org/c/coreboot/+/94886): al 2026-11-06 è `NEW`, senza Code-Review

## Fatto

- [x] Dump BIOS: 33554432 byte, sha256 `dd6e3116…4669`, due letture identiche, flash descriptor valido a `0x10`
- [x] Analisi di `usb-tools/ifu.efi` (ITE Flash Utility 2.3.1a, sha256 `16c08273…8176`): `ifu.efi /S 128` da solo dà 0 byte perché il reset `0xFE` precede `fclose`
- [x] Dump EC con `ifu.efi /S 128 /k /j`: firmware originale `V0.4.0` del 2025-07-23
- [x] CRC `0x4A-0x4B`: CRC-16/CMS sull'immagine esclusa la firma, confermato su tre build (docs 1.3)
- [x] Patch `V0.4.0` con `tools/patch_keyboard.py` e verifica con `tools/emulator/`
- [x] Quattro flash riusciti con `ifu`: `EC0416`, `iso-jis`, `iso-jis-fn-ctrl-swap`, `all-keys`
- [x] Tasti ISO e JIS, Back, Forward e ThinkVantage confermati con `evtest`
- [x] Rilascio di Fn prima del tasto e combinazioni con Fn confermati sulla scheda
- [x] HOTKEY arriva a GPH7 e il contatto 36 è a massa: dedotto dallo scambio funzionante, senza misure
- [x] Capire perché `storico/diagnostica-20261017/full_dump.bin` differisce da `dumps/bios/`: descriptor e DevExp2 identici, cambiano solo zone di ME (partizioni dati) e BIOS (inizio regione), anche tra 04/11 e 06/11. Coerente con dati a runtime
- [x] Dump BIOS tolti dalla repo e dalla cronologia, GPS tolto dalle foto: i dump restano solo in locale
- [x] Curva della ventola trovata nel firmware EC (`0xB841`, `0xB9E9`): 8 punti da 40 a 80 °C
- [x] Comando di scrittura dell'EC: nessun filtro sugli offset (`0xD90E`), curva scrivibile dall'OS. Dal codice e dall'emulatore, non ancora provato sulla scheda
- [x] Modi della ventola, modo manuale `0x90`, divisori della rampa `0x4C/0x4D` e `0xCE90` decodificati, isteresi senza effetto (`tools/emulator/fan_check.py`)
- [x] Prove in sola lettura con `ec_sys` a riposo e sotto carico: la temperatura EC segue `coretemp`, duty 92 % con carico stabile, pendolamento confermato (docs 8.2)
- [x] Catena della temperatura: PECI GetTemp su eSPI OOB, errori ignorati (`0x9508`), codici PECI letti come 110 °C
- [x] Correzione della ventola provata in emulatore (`tools/emulator/fan_fix.py`), nessuna immagine generata
- [x] Oggetti ACPI della ventola: `FAN0-4`, `TZ00` e `TFN1` non arrivano all'EC, `acpitz` è fisso a 27,85 °C
- [x] Port coreboot confrontato con i dump: layout della flash identico, Boot Guard attivo, mappa della RAM EC coerente
- [x] Leggere `setpci -s 00:16.0 0x40.l` sulla scheda: `90000255`, manufacturing mode confermato
- [x] Aggiungere a `ec.asl` gli eventi `_Q06`/`_Q07` (luminosità, `DHCF`): patch in x210ai-coreboot, da provare sulla scheda
- [x] MFIT sul proprio dump per disattivare Boot Guard: immagine costruita, non ancora scritta. Mai l'immagine di qualcun altro

## Regole di sicurezza (docs 2.1, 2.2, 2.4, 4.6, 5.2)

- Mai scrivere prima di una lettura verificata. Prima scrittura via ISP: un solo settore riscritto con il proprio contenuto (`-R`)
- Patch: 16B-signature a `0x40` intatta tranne il CRC `0x4A-0x4B` da ricalcolare, tabelle non spostate, non toccare gestore `0xDC` e ciclo di flash
- `ifu`: controllare la porta `0x66`, usare sempre il parametro `128`, fotografare lo schermo, mai sola USB-C
- Spazio EC: scrivere solo gli offset di docs 4.5. Mai sospendere in modo manuale `0x90`: al rientro la ventola resta ferma
- `EC_SPI1`: non alimentare la scheda dal connettore, non forzare gli strap test mode (FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2) all'accensione, livelli massimi 3,3 V
- Connettore tastiera: scambiarlo solo a macchina spenta, senza alimentatore e batteria
