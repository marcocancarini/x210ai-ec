# TODO — X210AI EC (IT5571)

Stato al 2026-11-08: sulla scheda c'è `EC-V0.4.0-all-keys.bin`, con tasti ISO e JIS, scambio Fn↔L-Ctrl, Back, Forward, ThinkVantage, rilascio di Fn e combinazioni con Fn confermati. Versioni e procedure in [`firmware/README.md`](firmware/README.md), analisi nelle parti di [`docs/`](README.md#parti-del-progetto). Per la ventola, patch, SSDT e strumento lato OS sono pronti ma mai usati sulla scheda: il prossimo passo è la sessione sull'hardware qui sotto.

## Sessione sull'hardware: ventola, in ordine

Ogni passo usa i risultati del precedente. Strumento: `tools/host/ec_fan.py` (docs 4.8). Ipotesi da confrontare: docs 5.5 e 8.7.

**1. Letture dall'OS, nessuna modifica**

- [ ] `sudo modprobe ec_sys`, poi `ec_fan.py status`: modo `0x10`, curva di fabbrica, `0xC9-0xCA` a 0 (offset scelti per la patch 8.8, devono restare a 0)
- [ ] `ec_fan.py log --out riposo.csv` 5 minuti a riposo, poi `carico.csv` con 22 thread: temperatura EC contro `coretemp`, duty. Serve anche per il caso dei 54 °C fissi (parte 3)
- [ ] `ec_fan.py i2ec` a riposo e sotto carico. Controlla l'ID del chip prima di continuare. Un conteggio che segue il duty dimostra che il tachimetro arriva a EC 47 e dà già i giri. Fisso o `FF`: nessuna conclusione (L8), si passa al punto 2. Guardare anche `GPCRD6` (deve essere `0x00`) e i bit di dato valido in `TSWCTLR`/`ZINTSCR`

**2. Ventola e connettore, senza scollegare nulla**

- [ ] Contare le ventole collegate, fotografare connettore e fili: 3 o 4 fili, colori. La foto di [tpart.net](https://www.tpart.net/product/x210ai-custom-fan/) mostra 3 fili, ma è la ventola in vendita
- [ ] A scheda spenta, senza alimentatore né batteria: cicalino dal retro del connettore verso massa, EC 47 (TACH0A, forse con resistenza in serie), EC 24 (PWM0). Con 3 fili nessun pin dovrebbe arrivare a EC 24. Annotare il componente tra EC 24 e il filo +V (MOSFET o regolatore)
- [ ] Con la ventola accesa, sotto il 100 % di duty: multimetro in V e in Hz, o analizzatore, su +V e TACH, a riposo e sotto carico. Confrontare con la tabella di docs 8.7:
  - 20 kHz su +V: alimentazione commutata
  - 0 Hz su +V con tensione che cambia col carico: driver lineare
  - TACH a 2 impulsi per giro: frequenza che segue i giri. Raffiche a 20 kHz: commutata
- [ ] Misurare anche EC 24, 25, 47, 48: PWM a 20 kHz confermato, tachimetro presente
- [ ] Aggiornare `tools/emulator/fan_plant.py` (driver, impulsi per giro, giri massimi) e rilanciare `fan_sim.py`. Con un driver commutato il tachimetro va riprogettato (filtro o lettura solo al 100 %)

**3. Curva reale della ventola** (docs 3.5, 4.5)

- [ ] Con `ec_sys write_support=1`, prova di un punto della tabella (docs 4.5): conferma che il comando `0x81` arriva alla curva
- [ ] Modo manuale `0x90`, duty da 0 a 152 a passi: giri (da `i2ec` o dal TACH in Hz), rumore, duty minimo di avvio da fermo e di arresto. **Tornare a `0x10` prima di qualsiasi sospensione**
- [ ] Verificare che i valori scritti nella tabella sopravvivano a riavvio e sospensione
- [ ] Scegliere la nuova curva. Mettere i giri misurati in `_FPS` di `firmware/acpi/x210ai-fan.asl` e il duty minimo di avvio in `fan_plant.py`

**4. SSDT senza patch EC** (docs 4.7)

- [ ] `iasl firmware/acpi/x210ai-fan.asl`, caricarla con l'hook `acpi_override` di mkinitcpio, riavviare
- [ ] `dmesg`: tabella accettata. `XTZ0` deve dare la temperatura vera, `XFAN` deve comparire come sesta ventola
- [ ] Scrivere `cur_state` del suo `cooling_device`: con `ec_fan.py status`, `0xC9` deve cambiare e `0xCA` valere 255. La ventola non deve cambiare, perché senza patch quei byte non hanno effetto
- [ ] Verificare se il kernel 7.3 espone i giri di `_FST` in hwmon

**5. Patch EC e flash** (docs 8.5, 8.6, 8.8)

- [ ] Decidere il contenuto: tachimetro (8.6), controllo dall'host (8.8), correzioni della curva (8.5), e la soglia `SAFE_C`
- [ ] Unire `host_ctl.py` e `fan_fix.py`, che si agganciano entrambi a `0xB60B` e `0xBB36`: isteresi, poi scelta tra richiesta e curva. Rifare tutte le prove e gli scenari del simulatore
- [ ] Estendere `tools/patch_keyboard.py` per scrivere l'immagine: CRC, firma, regole di docs 2.1
- [ ] Prima del flash, una via di recovery provata: ISP via RP2040 in sola lettura o programmatore (parte 5 e 6)
- [ ] Dopo il flash: `status` con i giri in `0x74`, `request 30 --timer 5` e scadenza, `request --forever` e sospensione (al risveglio deve tornare la curva), `auto`, SSDT con la patch

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

Misure e scelta della curva: sessione sull'hardware, punto 3.


- [ ] Capire perché nella prima prova la temperatura EC è rimasta a 54 °C: 2 minuti di letture rapide (52 byte al secondo) contro 2 minuti di letture lente, a riposo (docs 8.2, `storico/test-ventola-20261107/`)
- [ ] Decodificare `0x04FB` e `0x00C2`, che tengono ferma la ventola tramite `0xCE71`

### Parte 4: controllo ACPI

- [ ] Decidere la via definitiva: patch EC con SSDT (sessione sopra) o coreboot, che può includere gli stessi metodi in `ec.asl` (docs 4.3)

### Parte 8: analisi del firmware delle ventole

Lettura I2EC, patch e flash: sessione sull'hardware, punti 1 e 5.


- [ ] Valutare il fail-safe all'avvio: le prime letture PECI possono fallire
- [ ] Coprire anche il caso con il canale OOB fermo, oggi escluso dal controllo errori
- [ ] Decidere se aggiungere una soglia termica nell'EC (L5 in docs 8.2)

### Parte 5 e 6: hardware

Elenco completo delle misure in docs 6.1. La ventola è nella sessione sull'hardware, punto 2.

- [ ] Cicalino 15 segnali KSO/KSI dal connettore tastiera ai pin EC (docs 6.3; KSO1 foto = contatto 16, schema = 18). Chiude la mappa EPP per RP2040
- [ ] ISP via RP2040 in SOLA lettura: `isp hello / lines / enter --mode powerup / id / read -o x210ai-ec.bin -s 128 --no-exit`. Mai `write` prima di verificare il dump
- [ ] Misurare `EC_SPI1` contatti 1, 3, 7, 8, 9, 10 (massa, EC 119 = GPG6, EC 100 = GPG2, SMBus 87/88, 115/116, 117/118). FSPI già mappata sui contatti 2, 4, 5, 6
- [ ] Misurare se la scheda ha un pull-up esterno sulla linea HOTKEY
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
- [x] Patch del tachimetro (docs 8.6, `tools/emulator/tach_read.py`): stessi registri di system76/ec, doppia lettura, conteggio grezzo in `0x74-0x77`. Provata nell'emulatore
- [x] Simulatore dell'hardware della ventola (docs 8.7, `fan_plant.py`, `fan_sim.py`): task reale ogni 100 ms con driver, ventola, tachimetro e temperatura modellati. Tabella di cosa leggere sul connettore per ogni ipotesi
- [x] Patch per il controllo dall'host (docs 8.8, `tools/emulator/host_ctl.py`): richiesta e timer in `0xC9-0xCA`, curva sopra 85 °C, ritorno alla curva in sospensione o alla scadenza. Provata nell'emulatore e nel simulatore
- [x] Bozza di SSDT con ventola ACPI 4.0 e zona termica vera (docs 4.7, `firmware/acpi/x210ai-fan.asl`): compila senza avvisi, mai caricata
- [x] Strumento lato OS `tools/host/ec_fan.py` (docs 4.8): `status` provato sul dump del 17 ottobre, il resto mai eseguito

## Regole di sicurezza (docs 2.1, 2.2, 2.4, 4.6, 5.2)

- Mai scrivere prima di una lettura verificata. Prima scrittura via ISP: un solo settore riscritto con il proprio contenuto (`-R`)
- Patch: 16B-signature a `0x40` intatta tranne il CRC `0x4A-0x4B` da ricalcolare, tabelle non spostate, non toccare gestore `0xDC` e ciclo di flash
- `ifu`: controllare la porta `0x66`, usare sempre il parametro `128`, fotografare lo schermo, mai sola USB-C
- Spazio EC: scrivere solo gli offset di docs 4.5, più `0xC9-0xCA` dopo la patch 8.8. Mai sospendere in modo manuale `0x90`: al rientro la ventola resta ferma
- I2EC: solo con `ec_fan.py i2ec`, che si ferma se l'ID del Super I/O non è `0x5570` o `0x5571`. Solo letture di memoria EC
- `EC_SPI1`: non alimentare la scheda dal connettore, non forzare gli strap test mode (FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2) all'accensione, livelli massimi 3,3 V
- Connettore tastiera: scambiarlo solo a macchina spenta, senza alimentatore e batteria
