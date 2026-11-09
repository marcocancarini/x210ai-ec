# Parte 4: Controllo della ventola da ACPI

**In breve:** l'ACPI di fabbrica non controlla la ventola: i suoi oggetti sono residui di un modello Intel e non arrivano all'EC. Ma il comando di scrittura dell'EC accetta qualsiasi offset, compresi quelli della curva, quindi dall'OS si può cambiare la curva o comandare la ventola a mano.

**Stato:** dedotto dal codice e provato nell'emulatore ([3.3](3-curve-ventola.md#33-comportamento-verificato)). **Nessuna scrittura è stata fatta sulla scheda.** I difetti del firmware e le correzioni sono nella [parte 8](8-ventole-firmware.md).

## 4.1 Cosa offre l'ACPI di fabbrica

Tabelle da `storico/diagnostica-20261017/acpi.dat`, stato letto dal vivo il 2026-11-07 sulla scheda, con kernel 7.3.1.

| Oggetto | Dove | Cosa fa davvero | Sulla scheda |
|---|---|---|---|
| `\_TZ.FAN0-FAN4` (`PNP0C0B`) | SSDT `Ther_Rvp` | `_ON` e `_OFF` salvano un flag e chiamano `UPFS`, che agisce solo se esiste `H_EC.DUMY`. **`DUMY` non esiste in nessuna tabella**: nulla arriva all'EC | Linux vede 5 ventole (`cooling_device0-4`), tutte con stato 0 |
| `\_TZ.TZ00._TMP` | SSDT `Ther_Rvp` | Chiama `MXTP`, che senza `DUMY` restituisce la costante `0x0BC2`, cioè **27,85 °C** | `acpitz` segna 27,8 °C con la CPU a 58 °C |
| `_AC0-_AC4`, `_CRT` | SSDT `Ther_Rvp` | Soglie di 40, 45, 50, 55, 110 °C, critica a 115 °C | Mai raggiunte: la temperatura è fissa |
| `\_SB.IETM.TFN1` (DPTF) | SSDT `DptfTabl` | `_STA` dipende da `FND1`. `_FSL` chiama `FNSL`, `_FST` chiama `GFNS`: **nessuno dei due esiste** | `INTC1063:00`, `status=0`: il dispositivo è spento |
| `\_SB.IETM.TMP1-8` | SSDT `DptfTabl` | Sensori DPTF | Le zone segnano 50, cioè 0,05 °C |
| `ECF2` | DSDT | Regione `EmbeddedControl` da `0xFF` byte. I campi si fermano a `BTP1` (`0x93`) e non nominano `0x40-0x73`. `FANM` esiste solo come nome di variabile | La regione copre gli offset della ventola, ma nessuno li usa |
| Codice del BIOS (DXE/SMM) | Non analizzato | Non si può escludere che scriva qualcosa nello spazio EC durante l'avvio | I valori in RAM sono identici alle costanti del firmware |
| Coreboot | `ec.asl` | Non nomina questi offset, quindi la curva resta quella dell'EC | Non provato |

Il nome `Ther_Rvp` indica una tabella della piattaforma di riferimento Intel, lasciata nel BIOS.

**Conseguenza da ricordare:** `acpitz` non vede la temperatura, quindi `_CRT` non spegnerà mai la macchina. La protezione dal surriscaldamento resta alla CPU, che riduce la frequenza da sola, e ai sensori `coretemp` e `x86_pkg_temp`.

## 4.2 Il comando di scrittura dell'EC

Il comando ACPI `0x81` su `0x66` ha questo percorso:

| Passo | Dove | Cosa fa |
|---|---|---|
| Comando | Tabella `0x0A0F` → `0x08FE` | Riconosce `0x81` e passa allo stato "indirizzo" |
| Indirizzo e dato | `0x094C` | Il primo byte va in iRAM `0x38`, il secondo arriva come dato |
| Scrittura | `0x2B66` → `0xD90E` | Scrive il dato in `0x0400 + offset`, **senza controlli** |

`0xD90E` non ha filtri né liste: tutti i 256 byte sono scrivibili. Dopo la scrittura guarda solo due offset:

- `0x10`, il campo `APTS` del DSDT: se il nibble alto del dato è 0, azzera il bit 4 di `0x1608` e il bit 6 di `0x0411`.
- `0x11`: salta a `0xB2CF`, non analizzato.

La lettura `0x80` (`0xD8FB`) è altrettanto libera. Nell'emulatore le scritture a `0x40`, `0x4E`, `0x6D` e `0xFB` finiscono tutte in RAM.

**Durata.** La sola routine che scrive la tabella è `0xB841`, e gira solo all'avvio dell'EC ([3.1](3-curve-ventola.md#31-il-percorso-nel-firmware)). Quindi i valori scritti dovrebbero sopravvivere a riavvio, sospensione e spegnimento finché l'EC resta alimentato, e tornare quelli di fabbrica solo togliendo alimentatore e batteria, o dopo un flash. Dedotto dal codice, non provato.

**Build.** Tutto vale per la `V0.4.0` e per le immagini patchate, in cui queste routine sono identiche. Su `EC0416` gli indirizzi cambiano e non è stato controllato.

## 4.3 Le vie possibili

| Via | Come | Durata | Stato |
|---|---|---|---|
| **Scrittura dall'OS** | `ec_sys write_support=1`, da script o servizio | Fino al prossimo reset dell'EC | Possibile: il modulo c'è e il lockdown è spento. Con Secure Boot e lockdown il kernel può bloccarla |
| **SSDT aggiuntiva** | Tabella caricata da initrd (`CONFIG_ACPI_TABLE_UPGRADE=y`) o `configfs` (`=m`), con un `Field` su `ECF2` e una ventola ACPI 4.0: `_FIF`, `_FPS`, `_FSL`, `_FST` | A ogni avvio | Bozza in [4.7](#47-ssdt-ventola-acpi-40), mai caricata. Darebbe una vera ventola a Linux, con il driver `acpi-fan`. Per i giri e per un controllo sicuro serve la patch EC della [8.8](8-ventole-firmware.md#88-patch-per-il-controllo-dallhost) |
| **Coreboot** | Gli stessi metodi in `ec.asl`, più un `_TMP` vero | A ogni avvio | Da fare dopo il primo avvio di coreboot ([parte 7](7-coreboot.md)) |
| **Patch del firmware EC** | Cambiare le costanti in `0xB841-0xB98E` (istruzioni `MOV A,#xx`), correggere l'isteresi, ricalcolare il CRC ([1.3](1-dump-firmware.md#13-firme-e-checksum)) | Permanente, vale da subito e con qualsiasi OS | Stesso percorso delle patch della tastiera, con gli stessi rischi ([2.4](2-modifiche-software.md#24-scrittura-dellec-con-ifu-rischi)) |
| **BIOS originale** | Aggiungere le scritture | — | No: Boot Guard è attivo ([7.1](7-coreboot.md#71-riscontro-con-la-nostra-scheda)) |

`TFN1` non è un'alternativa comoda: aggiungere `FNSL` e `GFNS` con una SSDT non basta, perché `_STA` dipende da `FND1`, che ora spegne il dispositivo.

**Percorso consigliato:** provare e misurare con la scrittura dall'OS, poi portare la curva scelta nel firmware EC. La curva resta così nell'EC, senza servizi nell'OS, e continua a funzionare se l'OS si blocca. Per la ventola a mano, servono la SSDT o un servizio, con i rischi di [4.6](#46-rischi).

## 4.4 Prova in sola lettura

Non scrive nulla: senza `write_support` il file è di sola lettura, e la diagnostica del 17 ottobre ha già fatto lo stesso.

```fish
sudo modprobe ec_sys
sudo xxd -s 0x40 -l 0x34 /sys/kernel/debug/ec/ec0/io
grep . /sys/class/hwmon/hwmon*/name /sys/class/hwmon/hwmon*/temp1_input
sudo modprobe -r ec_sys
```

| Offset | Cosa guardare |
|---|---|
| `0x40-0x41` | Modo: deve essere `10` |
| `0x42` | Temperatura usata dalla curva. Va confrontata con `coretemp` |
| `0x44`, `0x46` | Obiettivo e duty attuale |
| `0x4E-0x6D` | Tabella di fabbrica, se il BIOS non l'ha toccata |
| `0x70` | Temperatura letta dall'EC |

Da ripetere a riposo e con un carico prolungato. Basta anche solo questo per chiudere il caso dei 100 °C ([3.2](3-curve-ventola.md#32-struttura-nello-spazio-ec)) e capire dove lavora la curva.

## 4.5 Prova in scrittura

Solo dopo la prova in lettura, con la macchina davanti e controllando `coretemp`. Il parametro del kernel avverte: `Dangerous, reboot and removal of battery may be needed`.

1. Annotare i valori attuali degli offset che si vogliono cambiare.
2. Caricare il modulo con la scrittura attiva:

   ```fish
   sudo modprobe -r ec_sys
   sudo modprobe ec_sys write_support=1
   ```

3. Cambiare un solo punto della tabella, di poco. Per esempio il duty dei 55 °C su entrambi i canali, offset `0x5C` e `0x5D`, da 80 a 70:

   ```fish
   printf '\x46\x46' | sudo dd of=/sys/kernel/debug/ec/ec0/io bs=1 seek=92 conv=notrunc
   ```

4. Rileggere e controllare che l'obiettivo a `0x44` segua, se la temperatura è in quella fascia.
5. Rimettere il valore originale e rileggere.
6. Solo dopo, se serve, provare il divisore della rampa o il modo manuale.

**Se serve il duty minimo di avvio** ([3.5](3-curve-ventola.md#35-cosa-misurare)), il modo manuale `0x90` è la via più diretta: scrivere prima l'obiettivo, poi il modo. Per uscirne, scrivere `0x10` in `0x40` e `0x41`.

**Limiti della prova:** solo offset `0x4C-0x6D`, più `0x40-0x41` e `0x44-0x45` per il manuale. Niente `0x10`, `0x11` e `0xFB`. In `dd`, `seek` è in decimale.

## 4.6 Rischi

| Rischio | Dettaglio | Come evitarlo |
|---|---|---|
| **Manuale e blocco dell'OS** | In modo `0x90` nessuno ricalcola l'obiettivo: se l'OS si blocca, il duty resta quello | Preferire la modifica della tabella: la curva resta nell'EC |
| **Manuale e sospensione** | Allo spegnimento o in sospensione `0xB98F` azzera l'obiettivo, e al rientro in modo manuale resta 0: **ventola ferma**. Provato nell'emulatore | Tornare a `0x10` prima di sospendere, oppure riscrivere l'obiettivo al risveglio |
| **Bit 4-6 del modo a 0** | La ventola va al massimo. Innocuo ma rumoroso | Scrivere sempre un modo con bit 4 acceso |
| **Tabella sbagliata** | La ricerca parte dall'alto e si ferma alla prima soglia superata: il firmware non controlla l'ordine | Soglie crescenti e duty finale a 152 |
| **Offset sbagliato** | Tutti i 256 byte sono scrivibili. `0xFB` può fermare la ventola, altri campi toccano la batteria | Limiti di [4.5](#45-prova-in-scrittura) |
| **Temperatura dall'host** | Con sorgente `0x72`, se l'OS smette di scrivere la temperatura resta quella | Non usarla senza un motivo preciso |
| **Nessun riscontro** | Senza tachimetro, l'EC non sa se la ventola gira ([3.4](3-curve-ventola.md#34-valutazione)) | Controllare a orecchio e con `coretemp` |

## 4.7 SSDT: ventola ACPI 4.0

`firmware/acpi/x210ai-fan.asl` è una **bozza mai caricata** sulla scheda. Compila con `iasl` 20251212 senza errori né avvisi, controllata contro il DSDT del 17 ottobre.

| Oggetto | Cosa fa |
|---|---|
| `\_SB.PC00.LPCB.H_EC.XFRG` | Seconda regione `EmbeddedControl` sugli offset `0x40-0xCF`, con i soli campi che servono: duty `0x46`, temperatura `0x70`, tachimetro `0x74`, richiesta `0xC9`, timer `0xCA` |
| `\_SB.XFAN` | Ventola ACPI 4.0 (`PNP0C0B`, `_UID` 0x10): `_FIF` a passi dell'1 %, `_FPS` con giri stimati dal modello, `_FSL` scrive la richiesta con timer 255, `_FST` restituisce duty e giri |
| `XAUT` | Metodo non standard: ridà la ventola alla curva |
| `\_TZ.XTZ0` | Zona termica con la temperatura vera da `0x70`, letta ogni 5 s. **Nessuna soglia**: senza la correzione L3 un errore PECI vale 110 °C, e un `_CRT` spegnerebbe la macchina |

**Senza la patch EC** `_FSL` scrive due byte non usati e non cambia nulla, `_FST` dà giri 0, e `XTZ0` funziona già. Si può quindi provare la tabella prima del flash: `_FSL` deve far comparire i valori in `0xC9-0xCA` (4.8, `status`).

**Caricamento.** Il kernel della scheda ha `CONFIG_ACPI_TABLE_UPGRADE=y`, e mkinitcpio ha l'hook `acpi_override`:

```fish
iasl firmware/acpi/x210ai-fan.asl
sudo install -Dm644 firmware/acpi/x210ai-fan.aml /etc/initcpio/acpi_override/x210ai-fan.aml
# aggiungere acpi_override a HOOKS in /etc/mkinitcpio.conf, poi
sudo mkinitcpio -P
```

Per tornare indietro: togliere il file e l'hook, rigenerare l'initramfs. Dopo il riavvio:

```fish
sudo dmesg | grep -i -E 'ACPI.*(override|upgrade|X210AI)'
grep . /sys/bus/acpi/devices/PNP0C0B:*/path
ls /sys/class/thermal/ ; grep . /sys/class/thermal/thermal_zone*/type
```

Linux dovrebbe vedere una sesta ventola, con `cur_state` da 0 a 100 nel suo `cooling_device`. I giri compaiono negli attributi del dispositivo e, nei kernel recenti, anche in hwmon: va verificato sul kernel 7.3.

**Da sapere:**
- `\_TZ.FAN0-FAN4` restano: non si tolgono con una SSDT.
- `_FPS` contiene giri inventati: vanno sostituiti con quelli misurati (3.5).
- Il driver `acpi-fan` non sa ridare la ventola alla curva. Per farlo servono `XAUT` (con `acpi_call`), `ec_fan.py auto` o una sospensione.

## 4.8 Strumento dall'OS

`tools/host/ec_fan.py` legge e, se richiesto, scrive dall'OS. Serve root.

| Comando | Cosa fa | Scrive |
|---|---|---|
| `status` | Modo, temperature, obiettivo, duty, curva, tachimetro, richiesta dell'host. Con `--ec-file` decodifica un dump salvato | No |
| `log --out file.csv` | Le stesse grandezze più `coretemp`, una riga al secondo: è la misura di 4.4 e 3.5 | No |
| `i2ec` | Legge i registri del tachimetro `0x181E-0x1821`, `TSWCTLR`, `ZINTSCR` e `GPCRD6` via I2EC. **Prima di tutto controlla che l'ID del chip sia `0x5570` o `0x5571`**, e altrimenti si ferma | Solo i registri di indice del Super I/O su `0x2E/0x2F` |
| `request 40 --timer 10`, `--forever` | Scrive richiesta e timer. Ha effetto solo con la patch 8.8 | `0xC9`, `0xCA` |
| `auto` | Azzera il timer | `0xCA` |

`status` e `log` vogliono `modprobe ec_sys`, le scritture `ec_sys write_support=1`. `status` è provato sul dump del 17 ottobre. `i2ec`, `request` e `auto` non sono mai stati eseguiti.

**`i2ec` è la prova del tachimetro senza patch.**
- Un conteggio che segue il duty dimostra che il tachimetro arriva a EC 47.
- Un valore fisso o `FF` non dimostra niente: il datasheet dice che la lettura da I2EC non è garantita.
- Il protocollo è quello del datasheet (6.3.2.9, Figure 7-41), con lo stesso controllo dell'ID che fa l'`ectool` di System76.
