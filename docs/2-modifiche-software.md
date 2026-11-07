# Parte 2: Modifiche via software

Tutto quello che si fa dalla macchina accesa, senza toccare la scheda: patch, lettura e scrittura di EC e BIOS. **Per flashare parti da [`firmware/README.md`](../firmware/README.md).** Qui ci sono analisi e rischi. Le modifiche alla ventola sono nella [parte 4](4-ventola-acpi.md).

## 2.1 Patch della tastiera

**Patch `V0.4.0`.** `tools/patch_keyboard.py` parte dal dump `V0.4.0`, ne controlla l'hash e i byte attesi, ricalcola il CRC ([1.3](1-dump-firmware.md#13-firme-e-checksum)) e genera i quattro file `firmware/patched/EC-V0.4.0-*.bin` ([1.1](1-dump-firmware.md#11-file-e-hash)). Ogni file è verificato per dimensione, vettore di reset, firma e CRC: questi controlli non dicono nulla sulla correttezza del codice. Sono state flashate `iso-jis`, `iso-jis-fn-ctrl-swap` e `all-keys`, che funzionano. Solo `fn-ctrl-swap` non è provata sull'hardware.

| Byte | Da → a | Effetto |
|---|---|---|
| `0x2F0A` (`KSI5/KSO1`) | `00 → 61` | ISO `<>` |
| `0x2F20` (`KSI6/KSO7`) | `00 → 5D` | ISO `#`, `ù` su layout italiano |
| `0x2EE1` (`KSI2/KSO8`) | `00 → 6A` | JIS Yen |
| `0x2F2E` (`KSI7/KSO5`) | `00 → 51` | JIS Ro |
| `0x2F29` (`KSI7/KSO0`) | `00 → 67` | JIS Muhenkan |
| `0x2F0F` (`KSI5/KSO6`) | `00 → 64` | JIS Henkan |
| `0x2F2F` (`KSI7/KSO6`) | `00 → 13` | JIS Katakana/Hiragana |
| `0x2EC8` (`KSI0/KSO15`) | `8C → 8E` | Il tasto LCtrl fa da Fn |
| `0xC461`, `0xC468` | `8E → 8C` | Il tasto Fn fa da LCtrl |
| `0x2F24` (`KSI6/KSO11`) | `00 → 87` | Back, solo in `all-keys` |
| `0x2F34` (`KSI7/KSO11`) | `00 → 8F` | Forward, solo in `all-keys` |
| `0x306E` | `5E → 38` | Codice `0x87`: da `E0 5E` a `E0 38`, Linux `KEY_BACK` |
| `0x307E-0x307F` | `20 05 → 30 01` | Codice `0x8F`: da modificatore inutilizzato a `E0 30`, Linux `KEY_FORWARD` |
| `0x2F13` (`KSI5/KSO10`) | `00 → 08` | ThinkVantage come F13 set 2, Linux `KEY_F13` |
| `0x2764` | `80 → 84` | `GPCRH7`: pull-up interno da 75 kΩ sul pin di Fn, solo in `all-keys` |
| `0x8CFA-0x8CFC` | `90 08 0E → 02 56 00` | Salto alla nuova routine di Fn, solo in `all-keys` |
| `0x5600-0x564D` | `FF → codice` | Salva Fn alla pressione nella mappa `0x00E0` e lo riusa al rilascio, solo in `all-keys` |
| `0x4A-0x4B` | `AF 5B → 79 1C` | CRC di `all-keys`. Negli altri file vale `F1 49` (ISO/JIS + scambio), `44 C4` (ISO/JIS), `1A D6` (scambio) |

I codici interni `0x87` e `0x8F` non sono usati da matrice, overlay o codice. Mappatura Linux verificata su `drivers/input/keyboard/atkbd.c`, compresi i tasti JIS: Yen 124, Ro 89, Muhenkan 94, Henkan 92, Katakana/Hiragana 93. Con `evtest` sulla scheda arrivano Back, Forward, F13 e tutti i tasti JIS.

**Verifica con emulatore 8051.** Esegue il codice reale del firmware con le periferiche simulate. Risultati su `all-keys`:

| Prova | Risultato |
|---|---|
| 127 celle, pressione e rilascio, da sole e con Shift, Fn o Ctrl tenuti | 508 casi, cambiano solo i tasti previsti |
| I 10 tasti nuovi, byte per byte | 40 casi su 40 |
| Fn rilasciato prima del tasto o premuto dopo | Originale 18 tasti errati su 127, patch 0 |
| Sequenze casuali da 600 eventi | Tasti bloccati: patch 0 su 100, originale 300 su 300 nella prova iniziale |
| Boot differenziale, 3 milioni di istruzioni | Unica scrittura diversa: `0x164F=84` |
| Errori inseriti apposta | Tutti rilevati, 15 su 15 |

Nelle sequenze casuali non contano Pausa, che contiene già il suo rilascio, e i falsi shift `E0 12` ed `E0 59`, ignorati da Linux. L'emulazione parte dopo il debounce per i tasti di matrice, simula i registri e non può provare la boot ROM né il cablaggio. Per rilanciare tutto: `python3 tools/emulator/run_tests.py`, circa un minuto. Le altre tre immagini passano la stessa suite e mantengono il bug del rilascio, come atteso.

Il pull-up segue il T61 di [USB_Laptop_Keyboard_Controller](https://github.com/thedalles77/USB_Laptop_Keyboard_Controller/tree/master/Example_Keyboards/Lenovo_ThinkPad_T61/Teensy%204p0) (`go_pu(HOTKEY)`) e l'adattatore X20x (il suo commento dice "active HIGH", ma il codice legge attivo basso con pull-up). Se la scheda ha già una resistenza, il datasheet consiglia di lasciarlo spento: i due pull-up in parallelo aumentano solo la corrente.

Le celle ISO/JIS erano vuote: se su una tastiera non c'è il tasto, non cambia nulla. Le posizioni JIS sono confermate sulla scheda con una tastiera giapponese, `<>` con una ISO ([2.4](#24-scrittura-dellec-con-ifu-rischi)). RCtrl non cambia.

**Patch `EC0416` (basate sulla `V0.3.2`):** restano solo come storia, non vanno flashate (vedi sotto).

**Regole:** dimensione fissa 128 KiB (pad `0xFF`), 16B-signature intatta tranne il CRC `0x4A-0x4B`, che sta al suo interno e va ricalcolato ([1.3](1-dump-firmware.md#13-firme-e-checksum)), tabelle non spostate (indirizzi assoluti). Una patch non deve toccare il gestore `0xDC` né il ciclo di flash, da cui dipende `ifu`. Prima di flashare leggere [2.4](#24-scrittura-dellec-con-ifu-rischi).

- **Tasti visibili all'host:** tabella `0x0D03`. Demo `firmware/obsolete/EC0416_ctrl-caps-swap.BIN`: swap L-Ctrl `0x14`↔Caps `0x58`, byte `0x0D17`↔`0x0D5B`.
- **Le patch `EC0416_*.BIN` hanno il CRC vecchio:** non flasharle.
- **`firmware/obsolete/EC0416_fn-ctrl-swap.BIN` è errata, non usarla.** Cambia il caso `0x84` in `0x0C09` (`0x54→0x1D`), che è il byte set 2 di Alt+SysRq. Fn è fuori matrice ([1.4](1-dump-firmware.md#14-tastiera-iso-e-jis)), quindi la patch non lo tocca: trasforma Alt+SysRq in LCtrl. La verifica qui sotto conferma solo quel byte, non il suo significato.
- **Fn e BIOS:** non c'è logica di swap né flag BIOS (BRAM `0x2200h` non usata come setting).

Verifica di `EC0416.BIN` contro `EC0416_fn-ctrl-swap.BIN`:

| Check | Esito |
|---|---|
| Dimensione | 131072 B in entrambi |
| Byte modificati | **1 solo**: `0x0C35`: `0x54 → 0x1D` |
| Hash patch | md5 `26ea0534446468c3e863e9f372d2de0a`, sha256 `97043168…fabee8` |
| 16B-signature, vettori `0x0000-0x003F`, tabella `0x0D03`, firma `0x7F80`, banchi 1-3 | Identici |
| Flusso istruzioni | Cambia solo l'operando di `MOV R7,#imm` a `0x0C34`, lunghezza invariata |

```
0C30: EF        MOV A, R7
0C31: B4 84 04  CJNE A, #0x84, 0x0C38
0C34: 7F 1D     MOV R7, #0x1D     ; patchato (originale: 7F 54)
0C36: 7E 01     MOV R6, #0x01
```

Emulazione di `0x0C09`: `0x84` → `0x1D`/`0x9D` make/break, stesso output di L-Ctrl (`0x14`); gli altri tasti provati (0x83, 0x14, 0x58, 0x76, 0x5A, 0x29, 0x61) restano invariati.

Riferimento della matrice: [thinkpad-ec, `docs/table_matrix.txt`](https://github.com/hamishcoleman/thinkpad-ec/blob/master/docs/table_matrix.txt).

## 2.2 Lettura dell'EC

L'eFlash è dentro il chip, quindi una clip SOIC o un programmatore SPI non la raggiungono: i pin FSPI servono solo per una flash esterna (datasheet Table 5-5). `flashrom -p internal` e `Fpt` leggono il BIOS, non l'EC.

La via software è stata provata sulla scheda il 2026-11-04. Le altre no. Partire sempre dalla sola lettura.

| Via | Strumento | Serve EC funzionante? | Stato |
|---|---|---|---|
| **Software** | `ifu.efi /S 128 /k /j` | Sì | **Provata**: due letture identiche. Vedi sotto |
| **EPP dal connettore tastiera** | RP2040 + [ITE-EC-Pico-USB-Parallel-ISP](https://github.com/bernTP/ITE-EC-Pico-USB-Parallel-ISP) | No | **Via consigliata per la recovery.** Provato solo su IT5261 ([6.3](6-modifiche-hardware.md#63-guida-rp2040-isp-dal-connettore-tastiera)) |
| **EPP dal connettore tastiera** | Arduino Mega 2560 + [system76/ec](https://github.com/system76/ec/blob/master/docs/flashing.md) | No | Documentato per IT5570. Mappa pin da adattare |
| **EPP con porta parallela reale** | Cavo DB25 (datasheet, sezione 7.24.3.1) + tool ITE | No | Cavo documentato, tool ITE non disponibile |
| **DBGR/SMB** | FT232H + [`iteflash`](https://chromium.googlesource.com/chromiumos/platform/ec/+/6555d8eefedd62af8f0b0e890cb3e696690a76cc/docs/ite-ec-reflashing.md) | No | Serve accesso alle linee SMBus. Tool da modificare, vedi [6.4](6-modifiche-hardware.md#64-lettura-con-dbgrsmb) |
| **Fuori scheda** | Dissaldatura + zoccolo LQFP-128 + programmatore con algoritmo ITE ("ITE Download Board 4") | No | Ultima risorsa. Il T48 non serve: `T48_List.txt` V13.16 ha 0 IC ITE |

Il debug I2EC sulle porte `2Eh/2Fh` accede alla memoria dell'EC dal lato host: non è una via documentata per il dump della eFlash.

La procedura di alimentazione cambia con lo strumento: il progetto Pico tiene l'alimentatore collegato senza batteria, la guida System76 vuole la macchina senza alimentazione. Seguire quella dello strumento, confrontandola con il requisito VSTBY del datasheet.

### Lettura con ifu

`ifu.efi` ha un'opzione **non documentata** nell'help, trovata nel codice (`0x4DCA`, `0x5174`):

```
ifu.efi /S 128 /k /j
```

Maiuscole e minuscole contano. Salva 128 KiB in `ITEFW.bin` nella cartella corrente. La routine `0x422C` usa solo la lettura veloce `0x0B`, senza cancellazioni né scritture, quindi **non può causare il brick descritto in [2.4](#24-scrittura-dellec-con-ifu-rischi)**.

**`/k /j` sono obbligatori.** Con il solo `/S 128` si ottiene un file da 0 byte, anche su volumi diversi (provato su chiavetta e partizione EFI). `ifu` crea il file (`0x519B`), legge (`0x526F`), invia `0xFE` (`0x5294`) e solo alla fine chiude il file (`0x5AFE` → `0x9F4C`): se il reset spegne la macchina, i dati non arrivano mai al disco.

- `/j` invia `0xFC` invece di `0xFE`: l'EC salta a `0x0400` senza reset (`0x80C4`).
- `/k` salta l'`0xAE` finale (`0x52A9`), inutile perché `/S` non invia `0xAD`, e la sua attesa senza timeout.
- Con il solo `/S 128` è stato osservato uno spegnimento brusco. Con `/k /j` il comportamento a fine dump non è stato annotato: l'EC riparte senza un vero reset, quindi spegnere subito con `reset -s`.
- Usa lo stesso ingresso `0xDC`: l'EC si ferma durante la lettura.
- Se il tool si blocca non c'è timeout: serve togliere l'alimentazione, compresa la batteria.
- Con un byte residuo sulla porta `0x62` ([2.4](#24-scrittura-dellec-con-ifu-rischi)) il dump esce spostato di una posizione. Controllare dimensione e firma.
- Non funziona su un EC brickato.
- La partizione EFI è leggibile solo da root: da Linux copiare il dump con `sudo install -o $USER -g $USER -m 644`.

### Verifica del dump

Ogni dump va controllato così, qualunque sia lo strumento:

1. Dimensione 131072 byte.
2. 16B-signature a `0x40` ([1.3](1-dump-firmware.md#13-firme-e-checksum)).
3. Due letture identiche.
4. Confronto con il file flashato per ultimo ([1.1](1-dump-firmware.md#11-file-e-hash)): oggi `EC-V0.4.0-all-keys.bin`.

## 2.3 Lettura del BIOS

Il BIOS sta su un chip SPI esterno, quindi qui un programmatore funziona. Fare il dump **prima di qualsiasi flash**: le due letture in `dumps/bios/` ([1.1](1-dump-firmware.md#11-file-e-hash)) vanno verificate prima di considerarle un'immagine di recovery.

**Dalla macchina funzionante:**

- UEFI Shell: `fpt.efi -d full.bin`
- Linux: `flashrom -p internal -r full.bin`

Dal chip, a macchina spenta: [6.5](6-modifiche-hardware.md#65-programmatore-sul-chip-del-bios).

## 2.4 Scrittura dell'EC con ifu: rischi

Comando: `ifu.efi <file>.bin 128`, dalla UEFI Shell.

Ci sono segnalazioni di brick occasionali, non riprodotte qui. L'analisi non prova la causa di un caso specifico, ma indica un meccanismo probabile e mostra che `ifu` non ha margine d'errore.

### Come funziona

`ifu` richiede la collaborazione del **firmware in esecuzione**.

1. Invia `0xAD` al KBC e `0xDC` sulla porta `0x66`.
2. Il firmware disabilita gli interrupt, porta il ciclo di flash in Scratch ROM (`0xDC94`) e ci salta (`0x800C`; variante PMC2 `0xD9D3`, caso `0xDC` nella tabella `0xF61E`). Risponde `0x33` sulla porta `0x62`. Percorso PMC1: `0x0A0F` → `0x0A40` → `0x0928` → `0x8A62`, **senza condizioni**.
3. L'host pilota il follow mode. Per ogni blocco: cancella, verifica la cancellazione, programma, verifica.
4. Alla fine invia `0xFE`, reset tramite watchdog. Con `/j` invia `0xFC`, salto a `0x0400`.

Finché il ciclo gira, l'EC fa solo questo: ricarica, ventola e tastiera restano ferme nello stato corrente (deduzione dal codice).

### Meccanismo di brick più probabile

Ipotesi ricavata dal codice, non riprodotta: **un byte rimasto nel buffer della porta `0x62`**. Una volta presente il byte, la catena è deterministica, e questo spiegherebbe perché il problema è occasionale.

1. `ifu` svuota il buffer del KBC (`0x2758`), ma non quello del PMC1 prima di `0xDC` (`0x4475-0x449A`).
2. Dopo l'invio attende `IBF=0`, che si azzera appena il firmware legge il comando. Il `0x33` arriva solo dopo l'ingresso in Scratch ROM (`0x8018`), quindi `ifu` legge prima il byte vecchio.
3. Stampa `EC ACK Fail.` e prosegue (`0x44A9`). Il `0x33` resta nel buffer: da qui ogni lettura restituisce il byte precedente.
4. L'ID flash risulta sbagliato, ma nessun controllo ferma il tool. Il vendor `0xFF` seleziona la cancellazione da 1 KiB (`0xD7`, `0x3173`); con un altro vendor il tool usa `0x20` da 4 KiB e la scrittura a pagine (`0x3B00`).
5. Il primo blocco viene cancellato comunque (`0x46E0`).
6. La verifica `0x34D4` si ferma al primo byte diverso da `0xFF` (`0x35AD`): legge quello in ritardo e fallisce.
7. `ifu` invia `0xFE` (`0x479C-0x47D3`): l'EC riparte con il settore di avvio cancellato. **Brick.**

**Firma da cercare:** `EC ACK Fail.`, poi ` -- Verify Fail. counterN=0` subito dopo la prima cancellazione. Il tool termina in pochi secondi.

La provenienza del byte non è determinabile senza il BIOS: serve un accesso precedente alla porta EC, con risposta non letta.

### Altre cause possibili

- **Accessi del BIOS durante il flash:** nel percorso `0x2700-0x5200` non ci sono `cli` né `RaiseTPL`, quindi i timer del BIOS possono inserirsi. Dopo i comandi `0x02/0x03` il byte seguente sulla `0x66` diventa dato SPI: un comando estraneo finirebbe alla flash.
- **Alimentazione:** l'EC è fermo mentre gestisce ricarica e USB-C PD. La sola USB-C è il caso più sospetto.
- **Blocco dell'EC seguito da spegnimento forzato.**
- **Errore isolato di cancellazione o programmazione,** che il tool trasforma in riavvio su flash danneggiata.

### Debolezze verificate nel codice

| Punto | Comportamento | Conseguenza |
|---|---|---|
| ACK `0x44A9` | Se non è `0x33`, stampa `EC ACK Fail` e **prosegue** | Non sa se l'EC è entrato nel ciclo |
| Attese su `0x62/0x66` | **Nessun timeout**, compresa l'attesa WIP `0x27DC` | L'unica uscita da un blocco è spegnere |
| Errore in `0x46F4`, `0x4758` | **Nessun nuovo tentativo**: invia `0xFE` | L'EC riparte da flash danneggiata invece di restare in Scratch ROM |
| Esito `0x5150` | `main` ignora il risultato | L'unico segnale è la riga ` -- Verify Fail.` a schermo |
| File in ingresso | Controllata solo la dimensione | Un file sbagliato da 128 KiB viene scritto |
| Ordine | Si parte dal blocco con il codice di avvio | Un errore precoce elimina subito ciò che serve per ripartire |
| Ciclo firmware | `0xDC` senza autenticazione né uscita a tempo | Ogni accesso a `0x62/0x66` è un comando di flash; un `0xDC` accidentale congela l'EC fino al reset |

### Verificato, senza problemi

- File letto in memoria **prima** di iniziare: la chiavetta non è il rischio principale.
- `128` dimenticato o sbagliato: il tool si ferma prima di scrivere (`File Size Paramter Lost`, `Paramter NOT Match`).
- Porte non decodificate: il tool si ferma se `0x62/0x66` leggono `0xFF`.
- **Watchdog EC:** CPU ed esterno sono attivati solo per il reset volontario (`0xD832`, `0x8100`), quindi non scattano a metà flash.
- **Selezione della eFlash:** `XRAM[0x9F]=0x4F` viene impostata all'avvio (`0x24B0` → `0x8C74`). `ifu` invia `0xDD/0xDE` solo per gli ID `0x8631`, `0x8632`, `0x8638`.
- Build vecchia e `EC0416`: stessa tabella GPIO di 103 voci, stesso ciclo a `0x8000-0x8100`, stesso switch di comandi. Non è una regressione.

**Flash reali.** Quattro flash riusciti con `ifu`, dalla ESP: elenco, conferme e procedura in [`firmware/README.md`](../firmware/README.md). L'ultimo, `all-keys`, mostra che un'immagine con CRC ricalcolato e codice aggiunto a `0x5600` parte sulla scheda. Non dimostra che il CRC venga controllato ([1.3](1-dump-firmware.md#13-firme-e-checksum)). Il confronto di [1.5](1-dump-firmware.md#15-confronto-tra-v040-e-ec0416) vale per il percorso di `ifu`, identico nelle build usate.

### Come ridurre il rischio

1. **Prima la recovery:** prova la via ISP in sola lettura ([6.3](6-modifiche-hardware.md#63-guida-rp2040-isp-dal-connettore-tastiera)). Senza, un brick significa rework.
2. Salva il firmware attuale con `ifu.efi /S 128 /k /j` ([2.2](#22-lettura-dellec)) e verifica il dump. Poi spegni: il flash va fatto da un avvio pulito.
3. Controlla lo sha256 del file sulla chiavetta ([1.1](1-dump-firmware.md#11-file-e-hash)) e usa sempre il parametro `128`.
4. Dalla UEFI Shell, subito prima del flash, leggi lo stato con `mm 66 -w 1 -IO -n` (eseguita sulla scheda: `0x00`). Il bit 0 è il byte residuo, il bit 1 è un comando non ancora letto: si procede solo se l'ultima cifra è `0`, `4`, `8` o `C`. Se è dispari, leggi una volta `0x62` con `mm 62 -w 1 -IO -n` e ricontrolla. Non aggiungere mai un valore dopo l'indirizzo: `mm` scriverebbe sulla porta.
5. Usa l'alimentatore DC sul connettore dedicato e la batteria carica. Evita la sola USB-C.
6. Avvia la UEFI Shell direttamente da USB o dalla ESP e non fare altro sulla macchina.
7. Fotografa lo schermo. `EC ACK Fail` o `Verify Fail` indicano un flash non riuscito, anche se il tool termina normalmente.
8. Non spegnere finché c'è avanzamento. Il riavvio finale è brusco ed è normale.

### Cosa manca per chiudere l'analisi

- Analisi delle immagini in `dumps/bios/` ([1.1](1-dump-firmware.md#11-file-e-hash), [2.3](#23-lettura-del-bios)).
- Tabelle ACPI, con `acpidump` sulla X210AI.
- Dettagli di un brick reale: alimentazione, messaggi a schermo, stato prima del flash.

## 2.5 Scrittura del BIOS con Fpt

**Con i file forniti non è possibile:** manca `MTLH-NB06_B0.2.bin`. Comando di `fb.nsh`: `fpt.efi -f MTLH-NB06_B0.2.bin`.

- **Piattaforma:** `Fpt.efi` contiene `Meteor Lake Platform` e `Lunar Lake Platform`. La versione esatta non si ricava dal file, né la compatibilità con il ME della scheda.
- **Verifica:** prevista di default (`-f <file> [NOVERIFY]`, fasi `Programming Flash` e `Verifying Flash`). `fb.nsh` non la disattiva.
- **Portata:** `fb.nsh` usa `-f` senza `-bios`, quindi scrive **dall'indirizzo zero** tutte le regioni presenti nell'immagine. Con `-bios` si limiterebbe alla regione BIOS. Dati specifici della macchina possono andare persi.
- **Backup:** né `fb.nsh` né il tutorial lo prevedono. Farlo prima ([2.3](#23-lettura-del-bios)).
- **Prompt:** davanti a `Do you want to truncate the data and continue?` **rispondere no**: immagine e flash non coincidono.
- **Flash:** confrontare il marking del chip con `fparts.txt`.
- **Secure Boot:** la UEFI Shell non è firmata, quindi va probabilmente disattivato.

Senza l'immagine non si possono verificare descriptor, regioni, ME, protezioni né come il BIOS usa l'EC.
