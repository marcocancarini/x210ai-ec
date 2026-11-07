# Parte 6: Modifiche via hardware e misure mancanti

Cosa si può fare sulla scheda e cosa va ancora misurato. Nessuna di queste vie è stata provata su questa scheda.

## 6.1 Misure mancanti

Tutte le misure ancora da fare, in ordine di utilità. Sono a scheda spenta salvo dove indicato.

| Area | Misura | Come | A cosa serve |
|---|---|---|---|
| Connettore tastiera | 15 segnali KSO/KSI verso i piedini EC, a partire da KSO1 (contatto 16 o 18) | Cicalino, [6.3](#63-guida-rp2040-isp-dal-connettore-tastiera) | Mappa per la recovery via RP2040 |
| Connettore tastiera | Tensione su un KSI a riposo, circa 3,3 V | Multimetro, alimentata | Sicurezza del Pico |
| Connettore tastiera | Alimentazioni sui contatti 35 e 38, TrackPoint su 37, 39, 40 | Multimetro, alimentata | Cosa non collegare |
| Connettore tastiera | Contatto di `HOTKEY`, contatto 36 a massa, pull-up esterno sulla linea | Cicalino e ohm | Oggi sono dedotti dal funzionamento |
| `EC_SPI1` | Contatti 1, 3, 7, 8, 9, 10: massa, EC 119, EC 100, SMBus | Cicalino, [6.8](#68-guida-riconoscere-il-pinout) | Capire se la porta porta il test mode o DBGR/SMB |
| `EC_SPI1` | Livello di VFSPI (piedino 106) e del contatto 1 | Multimetro, in standby | Livelli sicuri per l'ascolto |
| `EC_SPI1` | Tipo di blocco del connettore, contatti sopra o sotto | A vista | Scelta del cavetto |
| Chip EC | Marking completo | A vista | Confermare la variante LQFP |
| Chip BIOS | Marking e misura del package WSON-8 | A vista, calibro | Scelta dell'adattatore per il T48 |
| Ventola | Numero di ventole, connettore, fili | A vista | [3.4](3-curve-ventola.md#34-valutazione), [5.5](5-hardware.md#55-ventola) |
| Ventola | PWM su EC 24 e 25, tachimetro su EC 47 e 48 | Analizzatore logico o oscilloscopio, in S0 | Confermare i 20 kHz e la presenza del tachimetro |
| Ventola | Giri e rumore rispetto al duty, duty minimo di avvio | [3.5](3-curve-ventola.md#35-cosa-misurare) | Scegliere la nuova curva |
| Scheda | Foto del lato inferiore | Smontaggio | Vie dei contatti 3, 6, 8 e 10 di `EC_SPI1` |
## 6.2 Modifiche possibili

**Prima di ogni altra cosa:** una via di recovery provata. Oggi un brick dell'EC significa rework.

| Modifica | Cosa serve | Cosa dà | Stato |
|---|---|---|---|
| **Accesso ISP dal connettore tastiera** | Cavo di una tastiera X201 guasta o spina JAE AA01, Pico, 15 resistenze da 1 kΩ | Lettura e recovery dell'EC senza `ifu` | Da costruire ([6.3](#63-guida-rp2040-isp-dal-connettore-tastiera)) |
| **Adattatore WSON-8 per il T48** | Adattatore della misura giusta, PC Windows con Xgpro | Recovery del BIOS, requisito per coreboot | Da procurare ([6.5](#65-programmatore-sul-chip-del-bios)) |
| **Filo verso DBGR/SMB** | Da valutare dopo la mappa di `EC_SPI1`, FT232H | Seconda via ISP e debug | Dipende dalle misure ([6.4](#64-lettura-con-dbgrsmb)) |
| **Ascolto FSPI** | Analizzatore logico, cavetto FFC 10 pin da 0,5 mm | Capire se la porta lavora all'avvio | Solo ascolto ([6.8](#68-guida-riconoscere-il-pinout)) |
| **Tachimetro della ventola** | Da valutare dopo la misura. Se la ventola ha il filo e non arriva a EC 47, un collegamento | Giri leggibili, con una patch EC | Ipotesi ([5.5](5-hardware.md#55-ventola)) |
| **Sostituzione del chip EC** | Rework LQFP, chip nuovo, ISP | Scheda riparata se il chip è morto | Ultima risorsa ([6.7](#67-chip-di-ricambio)) |

Il pull-up di Fn non richiede modifiche: lo abilita già `all-keys`.
## 6.3 Guida RP2040: ISP dal connettore tastiera

**Non provata sull'IT5571.** Il progetto è testato su IT5261 (ThinkPad T14s), dove ha letto e aggiornato il firmware. I segnali coincidono con il datasheet IT5570 (sezione 7.24.3.1, Table 5-19, Table 5-21), ma la numerazione del connettore della T14s non vale qui: i collegamenti vanno ricavati sulla scheda.

| Operazione | Giudizio | Motivo |
|---|---|---|
| **Lettura** | **Probabile** | Il datasheet prevede ISP via EPP, il firmware non disabilita DBGR/EPP ([5.2](5-hardware.md#52-porta-di-debug-ec_spi1)) e il tool gestisce gli ID `0x5xxx`. Con `-s 128` si forza la dimensione |
| **Scrittura** | **Possibile, non ancora sicura** | Il tool sa scrivere, ma restano i punti aperti sotto |

L'ingresso avviene all'accensione con lo strap `KSI[5,4,2,1]=0011b`, con VSTBY presente e l'EC saldato sulla scheda. Non dipende dal firmware: in linea di principio funziona anche con EC brickato.

### Collegamenti

Una resistenza da **1 kΩ in serie su ogni linea** (470 Ω-1 kΩ), 15 in totale.

| Pico GPIO | Pin Pico | Segnale EC | Pin EC (LQFP-128) | Funzione |
|---|---|---|---|---|
| GP0-GP3 | 1, 2, 4, 5 | KSO0-KSO3 | 36-39 | PD0-PD3 |
| GP4-GP7 | 6, 7, 9, 10 | KSO4-KSO7 | 40-43 | PD4-PD7 |
| GP8 | 11 | KSI0 | 58 | STB# |
| GP9 | 12 | KSI1 | 59 | AFD# |
| GP10 | 14 | KSI2 | 60 | INIT# |
| GP11 | 15 | KSI3 | 61 | SLIN# |
| GP12 | 16 | KSI4 | 62 | Strap, tenuto basso |
| GP13 | 17 | KSI5 | 63 | Strap, tenuto basso |
| GP14 | 19 | KSO9 | 45 | BUSY |
| GND | 3, 8, 13, 18 | Massa della scheda | Non dal connettore | Vite o schermo USB |

La mappa dei GPIO sta in `firmware/hwconfig.h` del progetto RP2040: PD0-PD7 devono restare su 8 GPIO consecutivi.

**Mai collegare `3V3` o `VBUS` del Pico alla scheda:** in comune c'è solo la massa.

Connettore e mappa dei contatti: [5.3](5-hardware.md#53-connettore-tastiera).

### Trovare i contatti

1. Scheda spenta, senza batteria e senza tastiera.
2. Multimetro in continuità: un puntale sul piedino dell'EC, l'altro sui contatti del connettore tastiera.
3. Annotare il contatto di ognuno dei 15 segnali. L'orientamento può risultare specchiato.
4. Con la scheda alimentata, misurare un KSI a riposo: circa 3,3 V. **Con 5 V fermarsi.**

Non saldare sui piedini dell'EC (passo 0,4 mm). Le vie sono i candidati da valutare: filo smaltato sottile, ancorato alla scheda, se risultano scoperte. In alternativa serve il connettore corrispondente con una breakout su misura, o i terminali del connettore. Con la tastiera scollegata nessun altro pilota queste linee.

### Sola lettura

1. Con BOOTSEL premuto, copiare `firmware/prebuilt/ite_pp_isp_pico.uf2` del progetto RP2040 sul Pico.
2. Sul PC Linux eseguire `host/setup_venv.sh` e installare le regole udev.
3. Togliere la batteria e lasciare scollegato l'alimentatore. Non premere il tasto di accensione.
4. Eseguire i comandi, con `isp` come abbreviazione di `host/.venv/bin/python host/ite_pp_isp.py`:

```
isp hello
isp lines                 # prima senza alimentatore, poi con
isp enter --mode powerup  # collegare l'alimentatore quando lo chiede
isp id
isp read -o x210ai-ec.bin -s 128 --no-exit
isp safe
```

Verificare il dump ([2.2](2-modifiche-software.md#22-lettura-dellec)). Tra un tentativo e l'altro spegnere e scaricare l'EC: il tool ammette un solo arresto della CPU per ciclo di alimentazione.

### Punti aperti prima di scrivere

Verificati nel codice del tool (`host/itepp/`).

- **Dimensione flash:** è il punto più serio. Il tool la ricava da EC `0x1080`, che sul datasheet IT5570 è `FLHCTRL5R`, non un registro di dimensione documentato. In lettura `-s 128` la forza, ma **`write` non ha quell'opzione**: se il valore rilevato non è 128 KiB, il tool va modificato.
- **Flash ID:** `write` accetta solo `ff ff fe`. Non è verificato che l'IT5571 lo restituisca: `ifu` sulla scheda ha stampato `SPIDeviceID= FF FF FF FF`, che va confrontato con `isp id`. `ifu` ha un ramo per il vendor `0xFF` con cancellazione da 1 KiB (`0xD7`), compatibile con questa ipotesi. In lettura si può aggiungere `--ignore-flash-id`.
- **Programmazione:** il tool usa AAI word, `ifu` usa AAI byte (`0xAF`, `0x3644`). Il primo funziona su IT5261, ma non è provato qui.
- **Protect path:** prima di cancellare, il tool azzera EC `0x20A0-0x20BF`. Quei registri non sono nell'elenco del datasheet IT5570 e il firmware non li referenzia direttamente. Valutare `--keep-protect-path`.
- **Area dati:** `EC_DATA_AREA` ha una voce solo per 256 KiB, quindi a 128 KiB `write` tratta tutta la flash come codice. In `EC0416.BIN` e nella build vecchia gli ultimi 16 KiB sono vuoti, ma va controllato il dump reale.
- **Chip ID e firma:** nessun blocco atteso. `0x5571` entra nel ramo IT5xxxx e `52 61 02` è solo un riferimento stampato. La sequenza `0xA5` richiesta nei primi 4 KiB è presente a `0x40`.

**Non usare `write`** finché lettura, dimensione, ID e area dati non sono verificati su questo chip. Il primo test di scrittura dev'essere un singolo settore riscritto con il proprio contenuto, usando `-R`.

## 6.4 Lettura con DBGR/SMB

`iteflash` è scritto per IT83xx su FT4232 (Servo v2): `check_chipid()` accetta solo `0x83xx` e usa l'interfaccia B, quindi per IT5571 e FT232H va modificato. Protocollo: waveform 50 ms su clock e dati, poi I2C 400 kHz agli indirizzi `0x5A/0x35/0x79`. FT232H: solo 3,3 V, pull-up esterni, DO e DI uniti per SDA. DBGR/SMB si attiva a caldo, ma si esce solo con un reset (datasheet, sezione 7.23.3.2): prevedere un ciclo di alimentazione.

## 6.5 Programmatore sul chip del BIOS

Il BIOS sta su un chip SPI esterno, quindi qui un programmatore funziona. Una clip SOIC non va bene: serve un adattatore a punte per WSON o la dissaldatura ([5.4](5-hardware.md#54-chip-del-bios)). **Niente programmatori a 3,3 V o 5 V su questo chip.**

| Programmatore | Note |
|---|---|
| **XGecu T48** | **Quello da usare.** Xgpro, voce `W25Q256JW @WSON8`, in lista dalla V13.16. `voltages=0x0206` nel database di `minipro` = 1,8 V. Serve l'adattatore WSON-8 della misura giusta |
| **CH341A con mod 3,3 V** | **Non adatto** a questo chip senza adattatore da 1,8 V |
| **CH341A senza mod** | Linee a 5 V: **pericoloso**. Non usare |
| **RP2040** | `pico-serprog` + `flashrom`. Solo 3,3 V: **non adatto** a questo chip senza adattatore da 1,8 V |

Procedura: dump due volte e confronto hash, verifica del chip (RDID), sblocco WP se protetta, scrittura e verifica, nuovo dump. Mai interrompere.

## 6.6 Brick e recovery

Il pacchetto del produttore **non contiene istruzioni di recovery**. Queste sono note di progetto, mai provate su questa scheda.

| Cosa si è rotto | Via | Stato |
|---|---|---|
| **EC** (eFlash nel chip) | `ifu` se l'EC parte, altrimenti ISP dal connettore tastiera ([6.3](#63-guida-rp2040-isp-dal-connettore-tastiera)), con `dumps/ec/EC-V0.4.0-20250723-lettura1.bin` | Metodo da datasheet, collegamenti da ricavare |
| **BIOS** (chip SPI esterno) | Programmatore sul chip ([6.5](#65-programmatore-sul-chip-del-bios)) | Serve un dump verificato: quelli in `dumps/bios/` non sono ancora stati analizzati |
| **EC tramite `EC_SPI1`** | Porta FSPI ([5.2](5-hardware.md#52-porta-di-debug-ec_spi1)) | Non è un piano di recovery finché non si chiarisce il test mode |

**EC corrotto:** la boot ROM è intatta, ma non trova la 16B-signature. Sintomi: niente accensione, tastiera o ricarica, ventola al massimo. `ifu` non serve, perché richiede il firmware in esecuzione. Il chip è vivo, quindi l'ISP dovrebbe funzionare anche con flash illeggibile, se VSTBY è presente. Verificare sempre dopo la scrittura.

**Dump con EC brickato:** l'ingresso ISP non dipende dal firmware, quindi la lettura dovrebbe funzionare, ma non è provata. Da sola non ripara nulla: mostra solo cosa è rimasto nella flash. La riparazione è `isp write`, ancora bloccata dai punti aperti di [6.3](#63-guida-rp2040-isp-dal-connettore-tastiera).

**Chip morto elettricamente** (5 V, ESD): sostituire chip o scheda. Il rework LQFP si fa ad aria calda o drag soldering, senza reballing ([6.7](#67-chip-di-ricambio)).

## 6.7 Chip di ricambio

- **Serve il package LQFP-128:** JLCPCB/LCSC `IT5571E-128/CX` (C24833823), AliExpress/eBay IT5571E-128. Le versioni VFBGA (`IT5571VG-128/CX`, C7429720) **non sono compatibili con la piazzola**. IT5570E-128 ha lo stesso package, ma è un altro chip. Esistono chip pre-programmati per modello (icchipforlaptop.com e simili). Prima di ordinare, leggere il marking.
- Un chip nuovo ha l'eFlash vuota: va programmato via ISP o programmatore ITE, **non con il T48**. Il firmware è specifico della scheda: usare il proprio dump.
- Se è fallito solo il flash, non serve comprare nulla: basta riscrivere via ISP.

## 6.8 Guida: riconoscere il pinout

### Rischi

- `FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2` sono anche strap del **test mode** (Table 5-21): non forzarli durante l'accensione.
- Non alimentare mai la scheda dal connettore.
- Niente CH341A a 5 V: livelli al massimo 3,3 V, e 1,8 V se VFSPI lo è. Il T48 non aiuta.

Obiettivo: sapere cosa porta ogni contatto prima di collegarci qualcosa. Le fasi 1-3 si fanno **senza alimentazione**; la 4 non pilota nessuna linea.

**Servono:** multimetro con cicalino e prova diodi, puntali ad ago, calibro, lente o macro, analizzatore logico adatto alla tensione misurata, adattatore FPC-to-DIP con cavetto.

### Fase 1: passo e numero di contatti

**Confermato: 10 contatti, passo 0,5 mm.** Va bene un adattatore FFC 10 pin da 0,5 mm.

| Misura | Risultato | Come |
|---|---|---|
| Contatti | 10 | Foto macro, stesso conteggio su due scatti |
| Scala | 59,7 px/mm | Foto a 3072×4080: 32 piedini EC da 0,40 mm |
| Passo | 0,497 mm | Distanza media tra i terminali nella stessa foto |
| Larghezza fila terminali | 5,08 mm | Calibro digitale, foto con display capovolto |

Il calibro è coerente: 9 passi da 0,5 mm più la larghezza di un terminale danno circa 4,8 mm, e le ganasce non sono perfettamente a contatto. Un FFC è largo circa (contatti + 1) × passo, quindi 5,5 mm.

Il pin 1 è sul lato del triangolo. Restano da annotare il tipo di blocco (basculante o a slitta) e i contatti sopra o sotto: decidono verso e tipo di cavetto.

### Fase 2: accesso ai contatti

- Batteria e alimentatore scollegati. Se i piedini dell'EC non si raggiungono, smonta la scheda.
- Usa adattatore e cavetto del passo confermato. Non infilare puntali nel connettore.
- Il cavetto può invertire l'ordine: verifica col cicalino il contatto 1 e **annota la corrispondenza**.

### Fase 3: mappa con la continuità

1. **Massa:** ogni contatto contro un foro vite dorato.
2. **Candidati:** ogni contatto contro i piedini della tabella.
3. **Scansione:** per i rimasti, percorri i quattro lati dell'EC finché suona, poi restringi al piedino.
4. **Altrove:** prova il chip BIOS WSON-8 ([5.4](5-hardware.md#54-chip-del-bios)) e le piazzole vicine al connettore.

| Gruppo | Segnale | Piedino EC | Note |
|---|---|---|---|
| Massa | VSS | 1, 27, 49, 91, 104 | |
| Alimentazione | VSTBY / VCC / VFSPI | 121, 114, 92 / 11 / 106 | Se c'è, **non alimentarla da fuori** |
| Reset | WRST# | 14 | |
| FSPI | FSCK / FSCE# / FMOSI / FMISO | 105 / 101 / 102 / 103 | Strap test mode |
| SMBus 0 | SMCLK0 / SMDAT0 | 87 / 88 | |
| SMBus 1 | SMCLK1 / SMDAT1 | 115 / 116 | Attivo nel firmware |
| SMBus 2 | SMCLK2 / SMDAT2 | 117 / 118 | |
| UART | TXD / RXD | 17 / 16 | |
| SSPI | SSCK / SMOSI / SMISO / SSCE0# / SSCE1# / SBUSY | 32 / 56 / 57 / 100 / 125 / 122 | SSCE0# coincide con GPG2, strap test mode |

Il package a piedini aiuta: ogni segnale si raggiunge col puntale sul piedino, con mano ferma (passo 0,4 mm).

**Lettura delle misure:**

- Sotto circa 1 Ω: collegamento diretto.
- Decine di ohm: probabile resistenza in serie, conta come collegato anche se il cicalino non suona.
- Qualche kΩ verso un'alimentazione: probabile pull-up, tipico di SMBus.
- Niente: contatto non collegato o componente non montato. Cerca piazzole vuote lungo la pista.

**Scheda da compilare** (aggiungi righe se servono):

| Contatto | Pin adattatore | Ω verso massa | Prova diodi | Piedino EC / altro | Tensione standby | Segnale |
|---|---|---|---|---|---|---|
| 1 | | | | | | Alimentazione? |
| 2 | | | | 101 (da foto) | | FSCE# |
| 3 | | | | | | GND? |
| 4 | | | | 102 (da foto) | | FMOSI |
| 5 | | | | 103 (da foto) | | FMISO |
| 6 | | | | 105 (da foto) | | FSCK |
| 7 | | | | | | |
| 8 | | | | | | |
| 9 | | | | 108 o 109? | | |
| 10 | | | | | | |

Le due piazzole dorate sotto il connettore si provano col puntale, senza adattatore: sono il modo più semplice per abbinare i contatti 9 e 10.

### Fase 4: conferma in standby

Solo con la scheda già compilata.

1. Collega l'alimentatore, macchina spenta, puntale nero fisso sulla massa.
2. **Misura la tensione** di ogni contatto, senza toccare i vicini: 1,8 V o 3,3 V. Il contatto 1 e il piedino EC 106 indicano il livello di VFSPI.
3. Imposta quella soglia sull'analizzatore e registra l'accensione, solo in ascolto.
4. Decodifica con sigrok/PulseView:

| Cosa si vede | Segnale probabile |
|---|---|
| Clock a raffiche, con una linea che scende durante il traffico | SPI |
| Due linee a riposo alte, con start/stop e indirizzi | SMBus |
| Una linea a riposo alta, con bit di durata costante | UART |
| Tutto fermo | Nessuna attività all'accensione: non prova che la porta sia inutile |

### Fase 5: cosa fare col risultato

- **FSPI (contatti 2, 4, 5, 6):** niente programmatore SPI alla cieca, solo ascolto.
- **GPG6 e GPG2 sui contatti ignoti:** tutti gli strap del test mode sono sul connettore. Cercare il protocollo prima di pilotare qualsiasi linea.
- **SMBus collegato all'EC:** valutare DBGR/SMB ([6.4](#64-lettura-con-dbgrsmb)), prima in sola lettura.
- **UART:** utile come console, non per il flash.
- **Non collegata all'EC, o connettore assente:** resta la via KBS ([6.3](#63-guida-rp2040-isp-dal-connettore-tastiera)).

La prima scrittura arriva solo dopo la verifica del dump ([2.2](2-modifiche-software.md#22-lettura-dellec)). Riporta poi il pinout in [5.2](5-hardware.md#52-porta-di-debug-ec_spi1).
