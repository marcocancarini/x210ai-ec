# X210AI — ITE IT5571 EC

Reverse engineering del firmware EC della scheda **X210AI**: patch della tastiera, ventola, lettura, scrittura e recovery di EC e BIOS, port coreboot.

Il chip è un **ITE IT5571 rev. 2**: core **8051**, eFlash embedded da 128 KiB, package **LQFP-128** con piedini (14×14 mm, passo 0,4 mm).

**Per flashare parti da [`firmware/README.md`](firmware/README.md):** contiene tutte le versioni, le istruzioni e la conferma.

## Parti del progetto

| Parte | Contenuto | Stato |
|---|---|---|
| 1. [Studio del dump e del firmware](docs/1-dump-firmware.md) | File e hash, architettura, CRC, tastiera, confronto tra le build | EC decodificato per tastiera e ventola. Dump BIOS confrontati col port coreboot, non analizzati a fondo |
| 2. [Modifiche via software](docs/2-modifiche-software.md) | Patch, lettura e scrittura con `ifu` e `Fpt`, rischi | **Sulla scheda c'è `EC-V0.4.0-all-keys.bin`**, tasti e combinazioni confermati. Quattro flash riusciti, hash del dump non registrato. Causa dei brick segnalati trovata nel codice di `ifu`, non riprodotta |
| 3. [Curve della ventola](docs/3-curve-ventola.md) | Curva dell'EC, modi, rampa, valutazione | Decodificata e provata in emulatore. **Nessuna misura sulla ventola.** Isteresi inattiva e duty alto già con poco carico |
| 4. [Controllo ventola da ACPI](docs/4-ventola-acpi.md) | Cosa fa l'ACPI, scrittura dello spazio EC, vie possibili | L'ACPI di fabbrica non comanda nulla. **La curva è scrivibile dall'OS**, dal codice: mai provato sulla scheda |
| 5. [Studio dell'hardware](docs/5-hardware.md) | EC, `EC_SPI1`, connettore tastiera, chip BIOS, ventola | Da foto, datasheet e firmware. `EC_SPI1`: 4 contatti su 10 sono FSPI |
| 6. [Modifiche via hardware e misure mancanti](docs/6-modifiche-hardware.md) | Misure da fare, ISP con RP2040, programmatore, recovery | Niente provato sulla scheda. La recovery è descritta, mai eseguita |
| 7. [Coreboot](docs/7-coreboot.md) | Port di terze parti, riscontro con la scheda, ordine delle operazioni | Non accettato upstream. Manufacturing mode confermato, Boot Guard attivo. Immagine compilata, mai scritta: tutto in [x210ai-coreboot](https://github.com/marcocancarini/x210ai-coreboot) |
| 8. [Ventole: analisi del firmware](docs/8-ventole-firmware.md) | Catena di lettura, problemi di letture e impostazioni, correzioni proposte | Errori di temperatura ignorati, giri mai letti, isteresi inattiva. Correzione provata solo in emulatore, nessuna immagine generata |

**Eseguito sulla X210AI:** `ifu.efi` in lettura e quattro flash, l'ultimo con `all-keys`. `Fpt.efi` è stato solo disassemblato.

## Prossimi passi

1. Registrare l'hash del dump di `all-keys` ([conferma](firmware/README.md#conferma)).
2. Leggere lo spazio EC con `ec_sys`, a riposo e sotto carico: non scrive nulla e chiude il caso dei 100 °C ([4.4](docs/4-ventola-acpi.md#44-prova-in-sola-lettura)).
3. Provare la scrittura di un punto della curva ([4.5](docs/4-ventola-acpi.md#45-prova-in-scrittura)).
4. Misure sulla scheda, in ordine di utilità ([6.1](docs/6-modifiche-hardware.md#61-misure-mancanti)): prima i 15 segnali verso il connettore tastiera, poi il cablaggio RP2040 con `isp id` e `isp read`. Niente scritture prima ([6.3](docs/6-modifiche-hardware.md#63-guida-rp2040-isp-dal-connettore-tastiera)).
5. Per coreboot: seguire la guida di [x210ai-coreboot](https://github.com/marcocancarini/x210ai-coreboot), non ancora pubblica ([parte 7](docs/7-coreboot.md)).

Elenco completo in [`TODO.md`](TODO.md).

## Struttura della repo

| Percorso | Contenuto |
|---|---|
| [`docs/`](docs/) | Le otto parti |
| [`firmware/`](firmware/README.md) | Versione del produttore, immagini patchate, versioni da non usare, hash |
| [`dumps/`](dumps/README.md) | Letture di EC e BIOS dalla scheda, con hash |
| `tools/` | `patch_keyboard.py`, disassembler `i8051.py`, [emulatore](tools/emulator/README.md) |
| [`usb-tools/`](usb-tools/README.md) | UEFI Shell e `fe.nsh`. `ifu.efi` e `Fpt.efi` sono proprietari e non inclusi: il README dice dove trovarli |
| `refs/` | Immagini, foto e note sul datasheet |
| [`storico/`](storico/README.md) | Tutti i dati usati nel progetto, da sfoltire |

## Strumenti e convenzioni

- `python3 tools/patch_keyboard.py <dump V0.4.0> <cartella>`: genera le immagini. Con `--check <file>` controlla dimensione, reset, firma e CRC, non la correttezza del codice.
- `python3 tools/emulator/run_tests.py`: esegue il codice reale del firmware su tutte le immagini patchate. `tools/emulator/selftest.py` prova le istruzioni dell'emulatore. Niente dipendenze esterne.
- `python3 tools/emulator/fan_check.py`: esegue il codice reale della ventola e controlla modi, rampa, isteresi e scrittura dallo spazio EC.
- `python3 tools/emulator/fan_fix.py`: prova in memoria le correzioni della ventola, senza scrivere file. Come funziona l'emulatore: [`tools/emulator/README.md`](tools/emulator/README.md).
- `python3 tools/i8051.py <bin> 0 <start_hex> <end_hex>`: disassembler 8051 minimale, senza dipendenze. `tools/output/strings.txt` e `tools/output/key-regions.asm` sono artefatti generati.
- Commit raggruppati per sessione. `inputs/` resta in locale e non è nella repo. Hash e sezioni del datasheet in `refs/DATASHEETS.md`.

## Licenza

Script, strumenti e documentazione di questa repo sono distribuiti con licenza [GPL-2.0](LICENSE).

Restano dei rispettivi autori, con le loro condizioni:

- i firmware EC del produttore (`firmware/vendor/`, `storico/produttore/`) e i dump letti dalla scheda (`dumps/ec/`); le immagini patchate in `firmware/patched/` sono derivate da questi;
- le pagine del datasheet ITE in `refs/datasheet/` e `refs/img/it5571-pinout-lqfp128.png`, riprodotte solo come riferimento;
- i file in `storico/riferimenti/`, con link al progetto di origine in [`storico/README.md`](storico/README.md);
- la UEFI Shell in `usb-tools/EFI/` (EDK2, licenza BSD).
