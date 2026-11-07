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
| **SSDT aggiuntiva** | Tabella caricata da initrd (`CONFIG_ACPI_TABLE_UPGRADE=y`) o `configfs` (`=m`), con un `Field` su `ECF2` e una ventola ACPI 4.0: `_FIF`, `_FPS`, `_FSL`, `_FST` | A ogni avvio | Da provare. Darebbe una vera ventola a Linux, con il driver `acpi-fan`. I giri resterebbero ignoti (`0xFFFFFFFF`) |
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
