# Parte 7: Coreboot

Esiste un port di coreboot per la X210AI: [WheeledCord/coreboot-x210ai](https://github.com/WheeledCord/coreboot-x210ai), branch `x210ai`, di Fionn Cassidy. È un fork di coreboot con la scheda in `src/mainboard/51nb/x210ai/`. **Nulla è stato ancora scritto o avviato sulla nostra scheda.** Patch, configurazione, strumenti e guida sono nella repo [x210ai-coreboot](https://github.com/marcocancarini/x210ai-coreboot), non ancora pubblica, che è il riferimento aggiornato: questa sezione tiene il confronto con la scheda.

| Voce | Stato al 2026-11-06 |
|---|---|
| Fork | 25 commit sopra coreboot, ultimo push 2026-09-01. Nessuna issue aperta |
| Upstream | [CL 94886](https://review.coreboot.org/c/coreboot/+/94886) `mb/51nb/x210ai: Add new mainboard`: stato `NEW`, patch set 4, Verified+1, nessun Code-Review, ultimo commento 2026-09-08. In coreboot `main` c'è solo `51nb/x210` |
| Piattaforma | Meteor Lake U/H (`SOC_INTEL_METEORLAKE_U_H`, `FSP_TYPE_IOT`), payload a scelta |
| Provato dall'autore | Core Ultra 7 165H con pannello 3000×2000: Linux, NVMe, SATA, WiFi, Bluetooth, Ethernet, audio ALC1220, eDP, HDMI/DP, USB, S3 |
| Non provato | TPM, Thunderbolt/USB4, WWAN, variante 185H. Il port dice che PTT non è abilitato, ma sulla nostra scheda è attivo: `tpm_crb_acpi`, CRB a `0xFED40040`, `PttSupported=Yes` nella config del ME |

## 7.1 Riscontro con la nostra scheda

| Punto | Port coreboot | Nostra scheda | Esito |
|---|---|---|---|
| Layout della flash | `board.fmd`: 32 MiB, descriptor 16K, ME 8260K, DevExp2 10156K, BIOS 14 MiB a 18 MiB | Descriptor dei due dump in `dumps/bios/` e di `storico/diagnostica-20261017/full_dump.bin`: DESC `0x0-0x3FFF`, ME `0x4000-0x814FFF`, DevExp2 `0x815000-0x11FFFFF`, BIOS `0x1200000-0x1FFFFFF` | **Identico** |
| Chip BIOS | WSON-8, SPI, saldato | W25Q256JW, 1,8 V, letto dal kernel. Package non verificato a vista | Corregge [5.4](5-hardware.md#54-chip-del-bios), che diceva SOIC-8 |
| Boot Guard | Attivo di fabbrica: coreboot non parte finché non si disattiva | `MSR 0x13A = 0x30000006f`: verified boot e measured boot attivi (`storico/diagnostica-20261017/riepilogo.txt`) | **Concorde.** Va disattivato prima |
| Manufacturing mode | `setpci -s 00:16.0 0x40.l` deve dare `90000255` | `90000255`, letto con root il 2026-11-06 | **Concorde.** Coreboot è possibile |
| EC | IT5571E su eSPI, porte `0x62/0x66`, SCI su GPE `0x6E` | Stesso chip ([5.1](5-hardware.md#51-ec)) | Concorde |
| RAM dell'EC | `ec.asl`: lid `0x7F` bit 0, AC `0x80` bit 0, batteria `0x81-0x93` | `storico/diagnostica-20261017/ec_ram.bin`: `0x7F=01` (coperchio aperto), `0x81=09` (batteria presente, bit 3), capacità di progetto 8658, tensione di progetto 11100 mV, 238 cicli, 2554/5254 = 49 %, e `0x92=0x31` = 49 | **Valori coerenti** con la mappa del port |
| Eventi dell'EC | `_Q0A` AC, `_Q0B` batteria, `_Q0C` coperchio, `_Q54` tasto di accensione | Il DSDT originale (`acpi.dat`) ha anche `_Q06`, `_Q07`, `_Q3B-_Q3F`, `_Q53`, `_Q69`, `_Q70`. Solo `_Q06` e `_Q07` fanno qualcosa: chiamano `DHCF(3)` e `DHCF(2)`, il metodo della luminosità (`HBRT`, `BRTN`, `BRTL`). Gli altri 8 sono metodi vuoti | **Mancano i tasti della luminosità**, il resto non serve |
| Flash interno | `flashrom -p internal --ifd -i bios -N -w build/coreboot.rom` | Nella diagnostica flashrom ha usato `/dev/mtd0` ("Opaque flash chip"): il driver del kernel tiene il controller e regioni e protezioni non sono visibili | Prima va scollegato il driver SPI del kernel |

## 7.2 Flashare coreboot tocca l'EC?

**No, il firmware dell'EC non viene toccato.** Sono due memorie diverse:

| | Firmware EC | BIOS / coreboot |
|---|---|---|
| Dove sta | eFlash da 128 KiB **dentro** l'IT5571 ([1.2](1-dump-firmware.md#12-architettura-e-mappa-memoria)) | Chip SPI esterno WSON-8 da 32 MiB ([5.4](5-hardware.md#54-chip-del-bios)) |
| Chi lo scrive | `ifu.efi` tramite il firmware EC in esecuzione ([2.4](2-modifiche-software.md#24-scrittura-dellec-con-ifu-rischi)), oppure ISP dal connettore tastiera ([6.3](6-modifiche-hardware.md#63-guida-rp2040-isp-dal-connettore-tastiera)) | `flashrom -p internal`, `Fpt.efi`, programmatore sul chip |
| Nel flash descriptor | **Nessuna regione EC**: la regione 8 è vuota nei due dump di `dumps/bios/` | DESC, ME, DevExp2, BIOS |

Quindi `flashrom ... -i bios` non può raggiungere l'eFlash, e nemmeno la scrittura dell'intero chip per disattivare Boot Guard. `EC-V0.4.0-all-keys.bin` resta com'è. Il port non contiene codice che manda comandi all'EC: usa solo il bus eSPI, l'ACPI di `ec.asl`, che legge la RAM dell'EC su `0x62/0x66`, e il controller PS/2.

Cambia invece **come il sistema usa l'EC**, senza modificarlo:

- **Tastiera:** arriva all'OS dal KBC dell'EC su `0x60/0x64` ([1.4](1-dump-firmware.md#14-tastiera-iso-e-jis)), e il port dichiara il controller PS/2 (`ps2_controller.asl`). Le combinazioni con Fn che l'EC traduce in scancode ([1.4](1-dump-firmware.md#14-tastiera-iso-e-jis)) non dipendono dal BIOS.
- **Luminosità:** passa per gli eventi `_Q06` e `_Q07`, che il port non ha. Con coreboot i tasti della luminosità non dovrebbero funzionare finché non vengono aggiunti a `ec.asl` (dedotto dal DSDT, non provato).
- **Ventola:** non cambia, perché la curva è nel firmware EC ([parte 3](3-curve-ventola.md)).
- **eSPI:** se il BIOS configura male il bus, tastiera, batteria e coperchio smettono di arrivare all'OS. Il firmware EC resta comunque intatto, e rimettere il BIOS originale ripristina tutto.

## 7.3 Ordine delle operazioni

1. **Backup:** due letture nuove del 2026-11-06, identiche tra loro, sono fuori dalla repo. Prima di scrivere ne serve una aggiornata.
2. **Manufacturing mode:** confermato, `90000255`.
3. **Disattivare Boot Guard** con Intel MFIT, sul proprio dump: `mfit.exe --decompose dump.bin --saveconfig config.xml`, poi `BtGuardProfileConfig` da `Debug Profile` a `Boot Guard Disabled`, poi `mfit.exe --loadconfig config.xml --build dump_bgdisabled.bin`. L'autore usa MFIT 18.0.10.2285. Noi abbiamo costruito l'immagine con MFIT 18.1.18.2749, non ancora provata sulla scheda. MFIT è software Intel e non è nella repo.
4. **Scrivere l'immagine con Boot Guard disattivato** e controllare che il BIOS originale parta ancora. Questa scrittura tocca anche le regioni fuori dal BIOS, non solo i 14 MiB di coreboot.
5. **Scrivere coreboot** nella sola regione BIOS: descriptor, ME e DevExp2 restano quelli di fabbrica.

## 7.4 Rischi e punti deboli

- **Immagine precompilata:** il fork distribuiva un'immagine con Boot Guard disattivato, tolta il 2026-08-29 (`ae8c1be92e`) dopo la review: a due utenti, uno con 185H e uno con 165H, non funzionava, mentre il proprio dump modificato sì. Il `README.md` principale del fork cita ancora `x210ai-bootguard-disabled.bin`: è un residuo, quel file non c'è più. Usare solo il proprio dump.
- **Thunderbolt** (review di Maya Matuszczyk): `tbt_pcie_rp0` dovrebbe essere `tbt_pcie_rp1`, manca il collegamento a `pmc_mux`, e il GPIO di accensione del retimer non è noto. Con le correzioni Thunderbolt funziona solo a volte.
- **USB-C:** secondo l'autore funziona solo a volte, sia con coreboot sia con il BIOS originale. Potrebbe dipendere dalla scheda o dall'EC. Il PD è gestito dall'EC ([1.2](1-dump-firmware.md#12-architettura-e-mappa-memoria)): interessa anche questo progetto.
- **PCIe:** un revisore segnala che su una sua scheda una root port del `devicetree.cb` non viene trovata e viene disattivata.
- **S3:** funziona solo con `INTEL_TME` disattivato, perché la chiave della RAM non sopravvive alla sospensione.
- **Recovery:** se la macchina non parte più, serve il T48 sul chip WSON-8 ([6.5](6-modifiche-hardware.md#65-programmatore-sul-chip-del-bios)) con il dump di fabbrica, da un altro PC Windows. Non c'è un'altra via. Si può flashare dall'interno, ma solo con questo recupero già pronto.
