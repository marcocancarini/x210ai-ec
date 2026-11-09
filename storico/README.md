# Storico

Tutti i dati usati nel progetto, raccolti il 2026-11-05 prima di tagliare le parti inutili. **Non serve per flashare:** per quello c'è [`firmware/`](../firmware/README.md). I file qui sono copie: gli originali sono rimasti al loro posto.

| Cartella | Contenuto | Provenienza |
|---|---|---|
| `produttore/` | Pacchetto EC (cartella e zip), pacchetto BIOS (cartella e `.rar`), tutorial `.docx` | `~/Desktop/EC mod marco/`, `~/Downloads/` |
| `datasheet/` | `IT5570_A_V0.3.1_U.pdf`, solo in locale: le pagine usate sono in [`refs/datasheet/`](../refs/datasheet/README.md) | archivio personale |
| `report/` | `report.md`, `report_programmazione_T48.md`, analisi precedenti | archivio personale |
| `diagnostica-20261017/` | Script `x210ai-diag.sh` e risultati del 17 ottobre: ACPI, DMI, RAM EC, dump BIOS con `flashrom`, `evtest`, dispositivi | `~/Desktop/EC mod marco/` |
| `sessione-20261104/script/` | 40 script di analisi e prova, recuperati dagli appunti della sessione | Appunti del 2026-11-04 |
| `sessione-20261104/evtest/` | Output di `evtest` con tastiera ISO e JIS sul firmware `all-keys` | Salvati durante la sessione |
| `test-ventola-20261107/` | Prove sulla scheda del 7 novembre: script, log CSV e copie dello spazio EC. Vedi [8.2](../docs/8-ventole-firmware.md#82-problemi-delle-letture) | Sessione del 2026-11-07 |
| `riferimenti/adattatore-x201/` | Schema, pinout, tabelle matrice, keymap e hwdb dell'adattatore X6x/X20x | [bulat-chu](https://github.com/bulat-chu/Thinkpad-X6x-X20x-keyboard-USB-Adapter) |
| `riferimenti/thinkpad-ec/` | `table_matrix.txt` della X220 | [thinkpad-ec](https://github.com/hamishcoleman/thinkpad-ec) |
| `riferimenti/linux/` | `atkbd.c`, `input-event-codes.h` | [Linux](https://github.com/torvalds/linux) |
| `riferimenti/t61/` | Sketch Teensy 4.0 della T61 e `keylist.txt` | [USB_Laptop_Keyboard_Controller](https://github.com/thedalles77/USB_Laptop_Keyboard_Controller) |

## Note sui dati

- **Boot Guard:** `diagnostica-20261017/riepilogo.txt` riporta `MSR 0x13A = 0x30000006f`, con verified boot attivo: la regione BIOS non va modificata. Lo script dice che l'interpretazione è indicativa, da verificare sull'immagine. Il port coreboot conferma Boot Guard attivo di fabbrica e spiega come disattivarlo ([parte 7](../docs/7-coreboot.md)).
- **Dump BIOS del 17 ottobre:** `full_dump.bin` è 32 MiB e differisce da `dumps/bios/` per 192721 byte, in cinque zone tra `0x3A9004` e `0x125FC7F`. Il motivo non è stato analizzato. `bios_region.bin` non è una copia completa: differisce molto di più e contiene circa 20 MB di zeri.
- **Dati della macchina:** in `dmi.txt` seriali e UUID sono valori generici del produttore. `full_dump.bin` e `bios_region.bin` contengono NVRAM, voci di avvio e regione ME: restano solo in locale e non sono nella repo.
- **Script:** sono prove di lavoro, alcuni usano percorsi temporanei e la vecchia disposizione delle cartelle. Quelli validi sono in `tools/`.

## Cosa non c'è

| Dato | Motivo |
|---|---|
| `x210ai-diag-20261017-160631.tar.gz` | Stessi file della cartella: cambia solo `riepilogo.txt`, salvato come `riepilogo-archivio.txt` |
| Copie di `EC0416.BIN` sul Desktop | Identiche a `firmware/vendor/EC0416.BIN` |
| `ifu.efi`, `fe.nsh` e `MTLH-NB06_E03-250322.BIN` nell'archivio personale | Identici a quelli in `produttore/MTLH-NB06-ec-250322/` |
| `IT5571E-128.pdf` | Non trovato su questo PC, resta solo il suo hash in `refs/DATASHEETS.md` |
| Progetto RP2040 `ite_pp_isp` | Mai scaricato qui: è solo citato in [6.3](../docs/6-modifiche-hardware.md#63-guida-rp2040-isp-dal-connettore-tastiera) |
| Screenshot della UEFI Shell | Foto dello schermo, non recuperate |
| Appunti completi della sessione | Note personali: conservati solo in locale |
