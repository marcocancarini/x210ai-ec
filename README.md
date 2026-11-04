# X210AI — ITE IT5571 EC: guida completa

Reverse engineering del firmware EC della scheda **X210AI**, patch della tastiera, lettura, scrittura e recovery di EC e BIOS.

Il chip è un **ITE IT5571 rev. 2**: core **8051**, eFlash embedded da 128 KiB, package **LQFP-128** con piedini (14×14 mm, passo 0,4 mm). È quindi la variante `IT5571E-128`, non la VFBGA. Il package è visto in foto (§13): il marking completo va letto sul chip.

Questa guida è l'unico documento del progetto. I materiali originali stanno in `inputs/`, i dump in `dumps/`, i tool in `tools/`.

## Stato del progetto

| Area | Stato |
|---|---|
| Firmware EC | Analizzato, patch verificate staticamente (§2-§5) |
| Lettura EC | Più vie individuate, nessuna provata su questa scheda (§6, §7) |
| Scrittura EC | Rischi documentati (§9). Con RP2040 è possibile, ma con punti aperti (§7) |
| Immagine BIOS | **Assente**: il BIOS non è stato analizzato (§1, §8, §10) |
| Brick segnalati | Meccanismo più probabile trovato nel codice di `ifu`, non riprodotto (§9) |
| Recovery | Descritta, mai provata su questa scheda (§11) |
| Porta EC_SPI1 | Pinout parziale da foto: 4 contatti su 10 sono FSPI. Accesso all'eFlash non documentato, test mode da chiarire (§13, §14) |

**Nessun tool è stato eseguito su una X210AI.** `ifu.efi`, `Fpt.efi` e i dump sono stati solo disassemblati.

**Prossimi passi:**

1. Dump software con `ifu.efi /S 128`, finché l'EC funziona (§6).
2. Cicalino sui 15 piedini verso il connettore tastiera, iniziando da KSO1 sui contatti 16 e 18 (§7).
3. Cicalino sui contatti 1, 3, 7, 8, 9 e 10 di `EC_SPI1`: massa, EC 119, EC 100 e piedini SMBus (§13).
4. Accesso al connettore tastiera: cavo di una tastiera X201 guasta o spina JAE AA01 a 40 posizioni, codice non ancora trovato (§7).
5. Cablaggio RP2040, poi `isp id` e `isp read` con l'EC sano. Niente scritture prima (§7).

## Indice

**Firmware EC**

- §1 [File e hash](#1-file-e-hash)
- §2 [Architettura e mappa memoria](#2-architettura-e-mappa-memoria)
- §3 [Firme e checksum](#3-firme-e-checksum)
- §4 [Tastiera, ISO e JIS](#4-tastiera-iso-e-jis)
- §5 [Patch della tastiera](#5-patch-della-tastiera)

**Lettura**

- §6 [Lettura dell'EC](#6-lettura-dellec)
- §7 [Guida RP2040: ISP dal connettore tastiera](#7-guida-rp2040-isp-dal-connettore-tastiera)
- §8 [Lettura del BIOS](#8-lettura-del-bios)

**Scrittura e recovery**

- §9 [Scrittura dell'EC con ifu: rischi](#9-scrittura-dellec-con-ifu-rischi)
- §10 [Scrittura del BIOS con Fpt](#10-scrittura-del-bios-con-fpt)
- §11 [Brick e recovery](#11-brick-e-recovery)
- §12 [Chip di ricambio](#12-chip-di-ricambio)

**Interfaccia EC_SPI1**

- §13 [Porta di debug EC_SPI1](#13-porta-di-debug-ec_spi1)
- §14 [Guida: riconoscere il pinout](#14-guida-riconoscere-il-pinout)

**Varie**

- §15 [Strumenti e convenzioni](#15-strumenti-e-convenzioni)

---

## 1. File e hash

| File | SHA256 | Note |
|---|---|---|
| `dumps/EC0416.BIN` | `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca` | EC nuova, 131072 B, build `V0.3.2` 2025-04-15 18:20:35, md5 `7392fa5138c906ac17c7049fa69514e7` |
| `dumps/EC0416_ctrl-caps-swap.BIN` | `21f63a733dd5ee8b338ffefcda093ffec8d38c38138bc97c1e82a65a20acd406` | Patch demo L-Ctrl↔CapsLock (2 byte) |
| `dumps/EC0416_fn-ctrl-swap.BIN` | `970431688f10aa160973d3f276c453e5cc86427a28a01ee34ef43ea17dfabee8` | Patch Fn→LCtrl (1 byte) |
| `inputs/ec/MTLH-NB06-ec-250322/MTLH-NB06_E03-250322.BIN` | `151edd7a59cad1eb4a3d7b0827ee0937f73f0645a3cbf8d532f5e6bc0de5bbde` | EC vecchia, build 2025-03-22, md5 `4bbc1e54aad8cac51a3e0a5e5274ed28` |
| `inputs/ec/X210AI-EC-updated-on-03-22.zip` | `b850c8941df6eecbea035aefe481eb1c50fe8d5da4ea9b333717fc7a7230bc4e` | Archivio originale di `MTLH-NB06-ec-250322/` |
| `inputs/bios/X210AI0724BIOS.rar` | `a1090b7986e6e3cb2485333f73fd5f8d62822f64bedfe7cad5733e88ddd94663` | Solo strumenti, estratti in `inputs/bios/extracted/`. **Nessuna immagine BIOS** |
| `inputs/datasheets/IT5571E-128.pdf` | `a4e4afae8a157b7424401cf65c9dbecddce937b8b88a3dc1474124439bfc5753` | Datasheet sintetico, 29 pagine |
| `inputs/datasheets/IT5570_A_V0.3.1_U.pdf` | `01666ebe44ece4a436b5ffaad40c9570c17f0b3480862caf224953585c59102f` | IT5570 V0.3.1, parente stretto dell'IT5571 |

Sezioni del datasheet usate: `refs/DATASHEETS.md`.

**Immagine BIOS assente.** `fb.nsh` chiama `MTLH-NB06_B0.2.bin`, che non è incluso: nessun file del progetto contiene volumi firmware, regione ME o marcatori BIOS.

| File del pacchetto | Ruolo | Note |
|---|---|---|
| `inputs/bios/extracted/uefi-shell/EFI/BOOT/BOOTX64.efi`, `BOOTIA32.efi` | UEFI Shell, build 2013 | Non scrive nulla: è l'ambiente da cui lanciare i tool, da copiare in radice sulla chiavetta |
| `inputs/ec/MTLH-NB06-ec-250322/ifu.efi` | ITE Flash Utility 2.3.1a, build DEBUG | Legge e scrive l'EC. Presente solo nel pacchetto EC |
| `inputs/bios/extracted/Fpt.efi` + `fb.nsh` | Intel Flash Programming Tool | Legge e scrive il chip SPI del BIOS |
| `inputs/bios/extracted/fparts.txt` | Lista di 204 flash SPI | Le voci non sono validate, lo dice il file stesso |
| Tutorial `.docx` nel pacchetto BIOS | Guida generica con esempi di un altro modello (R51) | Non tratta backup, alimentazione, errori o recovery |

## 2. Architettura e mappa memoria

- CPU **8051**; vettore reset `0x0000` → `LJMP 0x0070` (init: SP=0xC0, FPCFG `0x1001=0x3F`, copia tabelle XRAM, main `0x0400`). Vettori standard `0x03/0x0B/0x13/0x1B/0x23/0x2B`; interrupt estesi ITE: stub `LJMP 0x28xx` → dispatcher `0x2800`; trampoline `0x2B6B-0x2BE0` (`MOV DPTR,#handler; AJMP 0x2800`).
- **4 banchi × 32 KiB**, finestra commutabile `0x8000-0xFFFF` (Bank base xdata `0x1300h`; FLHCTRL2R `0x1032` scritto a `0x251E`). Banco0 `0x0000-0x54D4` (fisso) + firma testuale `0x7F80`; banco1 `0x8000-0xF8A4`; banco2 `0x10000-0x15515`; banco3 `0x18000-0x18132` (stub bank-switch); resto `0xFF`.
- Base registri (datasheet, sezione 3.2): SMFI `0x1000h` (FLHCTRL1R `0x1031`, ECINDAR `0x103B-0x103F`, protect P0BA `0x104F+`), INTC `0x1100h`, EC2I `0x1200h`, **Bank `0x1300h`**, Common `0x1400h`, PMC `0x1500h`, GPIO `0x1600h`, PS/2 `0x1700h`, WUC `0x1B00h`, KBS `0x1D00h`, BRAM `0x2200h`.
- KBC host = xdata `0x004B/0x004C` (porte `0x64/0x60`); PD/UCSI in banco0 `0x3400-0x4300` (USB-C PD, controller esterno Analogix).

## 3. Firme e checksum

- **Nessuna firma crittografica trovata**: niente costanti SHA/RSA/MD5/CRC, somme non nulle, blocco `0x7F80` solo testo e non referenziato, reset `0x0070` non verifica la flash, e il firmware non legge da codice la zona `0x40-0x4F`.
- **16B-signature a `0x40`** (`A5…A4 95 85 12 26 E6 AA 00 55 55`): marcatore di power-on per localizzare la code base (datasheet, sezione 6.4.3.11.1, formato "implicit" → base `0x000000`). **Va preservata nelle patch** (offset validi `0x40-0xF0`).
- **Punto aperto, byte `0x4A-0x4B`:** valgono `26 E6` in `EC0416` e `F9 0C` nella build vecchia, mentre datasheet e System76 hanno `5A 5A` fissi. Non corrispondono a somme a 8/16 bit, XOR o CRC-16 con polinomi noti sugli intervalli provati. Il firmware System76 con `5A 5A` avvia su IT5570, quindi un controllo della boot ROM è improbabile, ma **non escluso** per valori diversi. Nessuna patch risulta provata sull'hardware.
- Protezione in scrittura: il firmware non scrive i registri P0BA-P3ZR.

## 4. Tastiera, ISO e JIS

- **KBS matrix 18×8** (base `0x1D00h`: KSOL/KSOH1/KSOCTRL/KSOH2/KSI@`0x1D04`/KSOxLSDR `0x1D10-0x1D21`). Driver in banco1 `0x9300-0x9F00`: loop 16 righe KSO, legge KSI, indice `0x4D=(col<<4)|row|0x08`.
- **Conversione scancode**: routine `0x0C09` (F0→break marker 0xFF, bit E7→casi speciali `0x83→0x41`/`0x84→0x54`, break `\|0x80`) e tabella **set2→set1 `0x0D03`** (128 B). Estesi `0xE0`: tabella `0x305E`; sequenze multi-byte (Pausa `E1 14 77`): `0x25B2`; comandi PS/2: `0x2636`.
- KBC 8042 (IRQ1/IRQ12, A20G): init `0x0A76`, dispatcher eventi `0x0D9C` (flag bit `0x30-0x3D`).
- Flusso: KBS scan → tabella matrice → scancode set2 → conversione set1 → buffer KBC → porta `0x60` + IRQ1.
- **ISO/JIS:** la matrice ha 144 posizioni e la tabella `0x0D03` copre tutti i set-2 `0x00-0x7F`, incluso il tasto extra ISO `0x61→0x56`. Il layout fisico dipende dal cablaggio della tastiera.
- **Build vecchia e `EC0416`:** tabelle set2→set1 (`0x0D2C` vs `0x0D03`), matrice, estesi e sequenze sono identiche, quindi ISO e JIS sono supportati in entrambe. Se nella vecchia ù/<> non passavano all'OS, o Fn+PgUp non funzionava, la causa è nel codice di scansione o di gestione Fn di quella build, non nelle tabelle.

## 5. Patch della tastiera

**Regole:** dimensione fissa 128 KiB (pad `0xFF`), 16B-signature intatta, tabelle non spostate (indirizzi assoluti), nessun checksum noto da aggiornare (ma vedi il punto aperto in §3). Una patch non deve toccare il gestore `0xDC` né il ciclo di flash, da cui dipende `ifu`. Prima di flashare leggere §9.

- **Tasti visibili all'host:** tabella `0x0D03`. Demo `dumps/EC0416_ctrl-caps-swap.BIN`: swap L-Ctrl `0x14`↔Caps `0x58`, byte `0x0D17`↔`0x0D5B`.
- **Fn→LCtrl:** Fn è **fuori matrice** (pin dedicato, tipo T61 I/O18→GND, rif. github.com/thedalles77/USB_Laptop_Keyboard_Controller) e non è uno scancode. Non c'è logica di swap né flag BIOS (BRAM `0x2200h` non usata come setting). La patch `dumps/EC0416_fn-ctrl-swap.BIN` cambia 1 byte a `0x0C35` (caso `0x84` in `0x0C09`: `0x54→0x1D`).
- **Limite:** non è confermato al 100% che `0x84` sia Fn. Nello schema della tastiera X201 (§7) Fn è `HOTKEY` sul contatto 1: seguendolo fino all'EC si identifica il pin. La direzione inversa (Ctrl fisico che fa da Fn) richiede la posizione matrice di Ctrl (driver banco1, indice `0x4D`).
- **Livello Fn:** la patch tocca solo l'output scancode, a valle del flag del pin Fn, quindi Fn+PgUp non è influenzato.

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

## 6. Lettura dell'EC

L'eFlash è dentro il chip, quindi una clip SOIC o un programmatore SPI non la raggiungono: i pin FSPI servono solo per una flash esterna (datasheet Table 5-5). `flashrom -p internal` e `Fpt` leggono il BIOS, non l'EC.

Nessuna via è stata provata sull'IT5571. Partire sempre dalla sola lettura.

| Via | Strumento | Serve EC funzionante? | Stato |
|---|---|---|---|
| **Software** | `ifu.efi /S 128` | Sì | **Più semplice**: niente hardware. Vedi sotto |
| **EPP dal connettore tastiera** | RP2040 + [ITE-EC-Pico-USB-Parallel-ISP](https://github.com/bernTP/ITE-EC-Pico-USB-Parallel-ISP) | No | **Via consigliata per la recovery.** Provato solo su IT5261 (§7) |
| **EPP dal connettore tastiera** | Arduino Mega 2560 + [system76/ec](https://github.com/system76/ec/blob/master/docs/flashing.md) | No | Documentato per IT5570. Mappa pin da adattare |
| **EPP con porta parallela reale** | Cavo DB25 (datasheet, sezione 7.24.3.1) + tool ITE | No | Cavo documentato, tool ITE non disponibile |
| **DBGR/SMB** | FT232H + [`iteflash`](https://chromium.googlesource.com/chromiumos/platform/ec/+/6555d8eefedd62af8f0b0e890cb3e696690a76cc/docs/ite-ec-reflashing.md) | No | Serve accesso alle linee SMBus. Tool da modificare, vedi sotto |
| **Fuori scheda** | Dissaldatura + zoccolo LQFP-128 + programmatore con algoritmo ITE ("ITE Download Board 4") | No | Ultima risorsa. Il T48 non serve: `T48_List.txt` V13.16 ha 0 IC ITE |

Il debug I2EC sulle porte `2Eh/2Fh` accede alla memoria dell'EC dal lato host: non è una via documentata per il dump della eFlash.

La procedura di alimentazione cambia con lo strumento: il progetto Pico tiene l'alimentatore collegato senza batteria, la guida System76 vuole la macchina senza alimentazione. Seguire quella dello strumento, confrontandola con il requisito VSTBY del datasheet.

### Lettura con ifu

`ifu.efi` ha un'opzione **non documentata** nell'help, trovata nel codice (`0x4DCA`, `0x5174`):

```
ifu.efi /S 128
```

Salva 128 KiB in `ITEFW.bin` nella cartella corrente. La routine `0x422C` usa solo la lettura veloce `0x0B`, senza cancellazioni né scritture, quindi **non può causare il brick descritto in §9**.

- Usa lo stesso ingresso `0xDC`: l'EC si ferma durante la lettura e alla fine viene riavviato con `0xFE`. Aspettarsi uno spegnimento brusco.
- Se il tool si blocca non c'è timeout: serve togliere l'alimentazione, compresa la batteria.
- Con un byte residuo sulla porta `0x62` (§9) il dump esce spostato di una posizione. Controllare dimensione e firma.
- Non funziona su un EC brickato.

### Lettura con DBGR/SMB

`iteflash` è scritto per IT83xx su FT4232 (Servo v2): `check_chipid()` accetta solo `0x83xx` e usa l'interfaccia B, quindi per IT5571 e FT232H va modificato. Protocollo: waveform 50 ms su clock e dati, poi I2C 400 kHz agli indirizzi `0x5A/0x35/0x79`. FT232H: solo 3,3 V, pull-up esterni, DO e DI uniti per SDA. DBGR/SMB si attiva a caldo, ma si esce solo con un reset (datasheet, sezione 7.23.3.2): prevedere un ciclo di alimentazione.

### Verifica del dump

Ogni dump va controllato così, qualunque sia lo strumento:

1. Dimensione 131072 byte.
2. 16B-signature a `0x40` (§3).
3. Due letture identiche.
4. Confronto con `EC0416.BIN` o con la build vecchia (§1), se il firmware installato è lo stesso.

## 7. Guida RP2040: ISP dal connettore tastiera

**Non provata sull'IT5571.** Il progetto è testato su IT5261 (ThinkPad T14s), dove ha letto e aggiornato il firmware. I segnali coincidono con il datasheet IT5570 (sezione 7.24.3.1, Table 5-19, Table 5-21), ma la numerazione del connettore della T14s non vale qui: i collegamenti vanno ricavati sulla scheda.

| Operazione | Giudizio | Motivo |
|---|---|---|
| **Lettura** | **Probabile** | Il datasheet prevede ISP via EPP, il firmware non disabilita DBGR/EPP (§13) e il tool gestisce gli ID `0x5xxx`. Con `-s 128` si forza la dimensione |
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

La mappa dei GPIO sta in `firmware/hwconfig.h` del progetto: PD0-PD7 devono restare su 8 GPIO consecutivi.

**Mai collegare `3V3` o `VBUS` del Pico alla scheda:** in comune c'è solo la massa.

### Connettore tastiera

![EC e connettore tastiera](refs/img/ec-connettore-tastiera.png)

Il connettore è il **11** dello [schema del produttore](refs/img/scheda-porte-debug.png): un board-to-board per tastiera **ThinkPad X201**, 40 contatti su 2 file da 20, passo 0,5 mm. Serigrafia letta da foto: `BTB_R…`. Non è un FPC, quindi una breakout FFC non entra.

Il riferimento è lo [schema dell'adattatore X201](https://github.com/bulat-chu/Thinkpad-X6x-X20x-keyboard-USB-Adapter), che usa il connettore JAE `AA01B-S040VA1`. Nel suo simbolo 41-44 sono a massa: i segnali sono 40. **Descrive la tastiera, non la X210AI.**

- **Numerazione:** contatti pari sulla fila verso l'EC, con `2` a sinistra e `40` a destra (EC a destra del connettore). Il pallino indica il contatto 1 sull'altra fila.
- **Ipotesi di mappa:** `DRVn` della tastiera = `KSOn` dell'EC, `SENSEn` = `KSIn`.
- **Verifica da foto:** le piste di KSO0-KSO4 portano ai contatti 22, 16, 14, 10, 2. Lo schema dà 22, 18, 14, 10, 2. Quattro su cinque coincidono, il KSO1 differisce di un contatto. Per i KSI non c'è nessun riscontro.

| Segnale EC | Pin EC | Contatto | GPIO Pico |
|---|---|---|---|
| KSO0 | 36 | 22 | GP0 |
| KSO1 | 37 | 18 (foto: 16) | GP1 |
| KSO2 | 38 | 14 | GP2 |
| KSO3 | 39 | 10 | GP3 |
| KSO4 | 40 | 2 | GP4 |
| KSO5 | 41 | 4 | GP5 |
| KSO6 | 42 | 8 | GP6 |
| KSO7 | 43 | 12 | GP7 |
| KSI0 | 58 | 5 | GP8 |
| KSI1 | 59 | 13 | GP9 |
| KSI2 | 60 | 9 | GP10 |
| KSI3 | 61 | 7 | GP11 |
| KSI4 | 62 | 11 | GP12 |
| KSI5 | 63 | 3 | GP13 |
| KSO9 | 45 | 20 | GP14 |

**Ogni riga va confermata col cicalino prima di saldare.**

**Da non collegare:** nello schema il 38 è +5 V e il 35 è +3,3 V, il 36 è la massa del tasto Fn (`HOTKEY` sul contatto 1), 31 e 34 sono massa. 37, 39 e 40 sono il TrackPoint a 5 V. Sulla X210AI vanno misurati: l'adattatore fornisce queste alimentazioni da sé.

**Accesso ai contatti:** l'adattatore monta una presa come quella della scheda, quindi non si innesta qui. Serve la spina JAE AA01 a 40 posizioni, il cui codice non è stato trovato, oppure il cavo piatto di una tastiera X201 guasta.

### Trovare i contatti

1. Scheda spenta, senza batteria e senza tastiera.
2. Multimetro in continuità: un puntale sul piedino dell'EC, l'altro sui contatti del connettore tastiera.
3. Annotare il contatto di ognuno dei 15 segnali. L'orientamento può risultare specchiato.
4. Con la scheda alimentata, misurare un KSI a riposo: circa 3,3 V. **Con 5 V fermarsi.**

Non saldare sui piedini dell'EC (passo 0,4 mm). Le vie sono i candidati da valutare: filo smaltato sottile, ancorato alla scheda, se risultano scoperte. In alternativa serve il connettore corrispondente con una breakout su misura, o i terminali del connettore. Con la tastiera scollegata nessun altro pilota queste linee.

### Sola lettura

1. Con BOOTSEL premuto, copiare `firmware/prebuilt/ite_pp_isp_pico.uf2` sul Pico.
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

Verificare il dump (§6). Tra un tentativo e l'altro spegnere e scaricare l'EC: il tool ammette un solo arresto della CPU per ciclo di alimentazione.

### Punti aperti prima di scrivere

Verificati nel codice del tool (`host/itepp/`).

- **Dimensione flash:** è il punto più serio. Il tool la ricava da EC `0x1080`, che sul datasheet IT5570 è `FLHCTRL5R`, non un registro di dimensione documentato. In lettura `-s 128` la forza, ma **`write` non ha quell'opzione**: se il valore rilevato non è 128 KiB, il tool va modificato.
- **Flash ID:** `write` accetta solo `ff ff fe`. Non è verificato che l'IT5571 lo restituisca. `ifu` ha un ramo per il vendor `0xFF` con cancellazione da 1 KiB (`0xD7`), compatibile con questa ipotesi. In lettura si può aggiungere `--ignore-flash-id`.
- **Programmazione:** il tool usa AAI word, `ifu` usa AAI byte (`0xAF`, `0x3644`). Il primo funziona su IT5261, ma non è provato qui.
- **Protect path:** prima di cancellare, il tool azzera EC `0x20A0-0x20BF`. Quei registri non sono nell'elenco del datasheet IT5570 e il firmware non li referenzia direttamente. Valutare `--keep-protect-path`.
- **Area dati:** `EC_DATA_AREA` ha una voce solo per 256 KiB, quindi a 128 KiB `write` tratta tutta la flash come codice. In `EC0416.BIN` e nella build vecchia gli ultimi 16 KiB sono vuoti, ma va controllato il dump reale.
- **Chip ID e firma:** nessun blocco atteso. `0x5571` entra nel ramo IT5xxxx e `52 61 02` è solo un riferimento stampato. La sequenza `0xA5` richiesta nei primi 4 KiB è presente a `0x40`.

**Non usare `write`** finché lettura, dimensione, ID e area dati non sono verificati su questo chip. Il primo test di scrittura dev'essere un singolo settore riscritto con il proprio contenuto, usando `-R`.

## 8. Lettura del BIOS

Il BIOS sta su un chip SPI esterno, quindi qui un programmatore funziona. Fare il dump **prima di qualsiasi flash**: oggi non esiste un'immagine da usare per la recovery.

**Dalla macchina funzionante:**

- UEFI Shell: `fpt.efi -d full.bin`
- Linux: `flashrom -p internal -r full.bin`

**Dal chip, a macchina spenta:** package SOIC-8, secondo `fparts.txt` W25Q128, MX25L12873, N25Q128 e simili a 3,3 V. Package e tensione sono dedotti da quella lista, non dalla scheda: leggere il marking e controllare il datasheet. Con una flash da 1,8 V serve un adattatore di livello.

| Programmatore | Note |
|---|---|
| **XGecu T48** | 3,3 V via software. App XGecu/MiniPro, oppure `flashrom -p xgecu-t48-spi` se supportato |
| **CH341A con mod 3,3 V** | Tagliare la pista o dissaldare il regolatore 5 V (78L05), alimentare VCC a 3,3 V. `flashrom -p ch341a_spi -r/-w/-v` |
| **CH341A senza mod** | Linee a 5 V: **pericoloso** su flash a 3,3 V. Solo con adattatore di livello |
| **RP2040** | `pico-serprog` + `flashrom`. Solo 3,3 V, non provato su questa scheda |

Procedura: dump due volte e confronto hash, verifica del chip (RDID), sblocco WP se protetta, scrittura e verifica, nuovo dump. Mai interrompere.

## 9. Scrittura dell'EC con ifu: rischi

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

Attenzione ai nomi: entrambe le build si dichiarano `V0.3.2`, pur differendo per 46.608 byte. Solo la vecchia contiene `MTLH-NB06`. Per distinguerle usare data o sha256.

### Come ridurre il rischio

1. **Prima la recovery:** prova la via ISP in sola lettura (§7). Senza, un brick significa rework.
2. Salva il firmware attuale con `ifu.efi /S 128` (§6) e verifica il dump.
3. Controlla lo sha256 del file sulla chiavetta (§1) e usa sempre il parametro `128`.
4. Dalla UEFI Shell leggi la porta `0x66`: se il bit 0 è a 1, leggi una volta `0x62` per svuotare il buffer. Sintassi attesa, non provata su questa shell: `mm 66 -IO -w 1 -n`.
5. Usa l'alimentatore DC sul connettore dedicato e la batteria carica. Evita la sola USB-C.
6. Avvia la UEFI Shell direttamente da USB e non fare altro sulla macchina.
7. Fotografa lo schermo. `EC ACK Fail` o `Verify Fail` indicano un flash non riuscito, anche se il tool termina normalmente.
8. Non spegnere finché c'è avanzamento. Il riavvio finale è brusco ed è normale.

### Cosa manca per chiudere l'analisi

- Immagine BIOS (§8).
- Tabelle ACPI, con `acpidump` sulla X210AI.
- Dettagli di un brick reale: alimentazione, messaggi a schermo, stato prima del flash.

## 10. Scrittura del BIOS con Fpt

**Con i file forniti non è possibile:** manca `MTLH-NB06_B0.2.bin`. Comando di `fb.nsh`: `fpt.efi -f MTLH-NB06_B0.2.bin`.

- **Piattaforma:** `Fpt.efi` contiene `Meteor Lake Platform` e `Lunar Lake Platform`. La versione esatta non si ricava dal file, né la compatibilità con il ME della scheda.
- **Verifica:** prevista di default (`-f <file> [NOVERIFY]`, fasi `Programming Flash` e `Verifying Flash`). `fb.nsh` non la disattiva.
- **Portata:** `fb.nsh` usa `-f` senza `-bios`, quindi scrive **dall'indirizzo zero** tutte le regioni presenti nell'immagine. Con `-bios` si limiterebbe alla regione BIOS. Dati specifici della macchina possono andare persi.
- **Backup:** né `fb.nsh` né il tutorial lo prevedono. Farlo prima (§8).
- **Prompt:** davanti a `Do you want to truncate the data and continue?` **rispondere no**: immagine e flash non coincidono.
- **Flash:** confrontare il marking del chip con `fparts.txt`.
- **Secure Boot:** la UEFI Shell non è firmata, quindi va probabilmente disattivato.

Senza l'immagine non si possono verificare descriptor, regioni, ME, protezioni né come il BIOS usa l'EC.

## 11. Brick e recovery

Il pacchetto del produttore **non contiene istruzioni di recovery**. Queste sono note di progetto, mai provate su questa scheda.

| Cosa si è rotto | Via | Stato |
|---|---|---|
| **EC** (eFlash nel chip) | ISP dal connettore tastiera (§7) + `EC0416.BIN` | Metodo da datasheet, collegamenti da ricavare |
| **BIOS** (chip SPI esterno) | Programmatore sul chip (§8) | Serve un dump fatto **prima**: oggi non ne abbiamo uno |
| **EC tramite `EC_SPI1`** | Porta FSPI (§13) | Non è un piano di recovery finché non si chiarisce il test mode |

**EC corrotto:** la boot ROM è intatta, ma non trova la 16B-signature. Sintomi: niente accensione, tastiera o ricarica, ventola al massimo. `ifu` non serve, perché richiede il firmware in esecuzione. Il chip è vivo, quindi l'ISP dovrebbe funzionare anche con flash illeggibile, se VSTBY è presente. Verificare sempre dopo la scrittura.

**Chip morto elettricamente** (5 V, ESD): sostituire chip o scheda. Il rework LQFP si fa ad aria calda o drag soldering, senza reballing (§12).

## 12. Chip di ricambio

- **Serve il package LQFP-128:** JLCPCB/LCSC `IT5571E-128/CX` (C24833823), AliExpress/eBay IT5571E-128. Le versioni VFBGA (`IT5571VG-128/CX`, C7429720) **non sono compatibili con la piazzola**. IT5570E-128 ha lo stesso package, ma è un altro chip. Esistono chip pre-programmati per modello (icchipforlaptop.com e simili). Prima di ordinare, leggere il marking.
- Un chip nuovo ha l'eFlash vuota: va programmato via ISP o programmatore ITE, **non con il T48**. Il firmware è specifico della scheda: usare il proprio dump.
- Se è fallito solo il flash, non serve comprare nulla: basta riscrivere via ISP.

## 13. Porta di debug EC_SPI1

![Pinout EC_SPI1 ricavato dalle foto](refs/img/ec-spi1-pinout.png)

**Pinout parziale, ricavato dalle foto del 2026-11-04.** Quattro contatti sono l'interfaccia FSPI dell'EC, gli altri sei restano da misurare. Nessuna misura elettrica è stata fatta.

| Contatto | Segnale | Da dove viene | Stato |
|---|---|---|---|
| 1 | Alimentazione? | Pista larga, il tratto vicino al contatto è coperto dal triangolo | Da misurare |
| 2 | **FSCE#** | EC 101 | Pista seguita |
| 3 | GND? | Via subito sotto il contatto | Da misurare |
| 4 | **FMOSI** | EC 102 | Pista seguita |
| 5 | **FMISO** | EC 103 | Pista seguita |
| 6 | **FSCK** | EC 105, con una via sulla pista | Pista seguita |
| 7 | ? | Nessuna pista visibile | Da misurare |
| 8 | ? | Via subito sotto il contatto | Da misurare |
| 9 | ? | Piazzola dorata destra, poi verso EC 108 o 109 | Da misurare |
| 10 | ? | Piazzola dorata sinistra, poi via vicino a EC 125 | Da misurare |

Il contatto 1 è sul lato del triangolo, il 10 sul lato della serigrafia `10`. Il pinout vale sul connettore della scheda: un cavetto FFC può invertire l'ordine.

**Perché la numerazione è affidabile:**

- Le foto mostrano 32 piedini per lato, quindi un LQFP-128, e un piedino 97 accanto all'angolo in alto a destra.
- Le tacche serigrafate attorno al chip cadono ogni 5 piedini: misurate su 105, 110, 115 in alto e 90, 95 a destra. Solo questa rotazione del chip le fa cadere su multipli di 5.
- Le quattro piste arrivano su posizioni 101, 102, 103 e 105, con un buco sul 104, che è VSS.
- Il datasheet colloca sullo stesso lato FSCE#, FMOSI, FMISO, VSS e FSCK, in quest'ordine.

**Limiti delle foto:**

- I contatti 9 e 10 entrano nelle piazzole sotto la serigrafia: l'abbinamento in tabella è il più probabile, non visibile.
- La pista del contatto 9 sparisce sotto la serigrafia del chip: EC 108 è `AC_IN#`, EC 109 è `LID_SW#`. Nessuno dei due è un segnale di debug.
- La pista larga del contatto 1 arriva a un componente vicino ai piedini 97-100. Un resistore su GPG2 (EC 100) avrebbe senso, perché il datasheet lo vuole in pull-up se FSPI è in uso (Table 5-20). Non è verificato.
- Il lato inferiore della scheda non è stato fotografato: le vie dei contatti 3, 6, 8 e 10 proseguono lì o su strati interni.

**Conseguenze:**

- Nel funzionamento normale FSPI è il bus verso una flash esterna, con l'EC come master: FSCK e FSCE# sono sue uscite (Table 5-5).
- Nessun accesso esterno all'eFlash da FSPI è documentato, ma **non è escluso**.
- **Test mode, punto aperto:** FSCK, FMISO, FMOSI e FSCE# sono anche strap del test mode (Table 5-21), insieme a GPG6 (EC 119) e GPG2 (EC 100). Il datasheet ne cita solo l'ingresso, senza protocollo né funzione. Se i contatti ignoti portassero anche GPG6 e GPG2, il connettore avrebbe tutti gli strap, e una funzione di fabbrica diventerebbe un'ipotesi seria.
- Un programmatore SPI collegato alla cieca non ha un protocollo noto da seguire, e rischia di pilotare linee contro l'EC.
- Il firmware non scrive `FLHCTRL5R` `0x1080`. Il suo unico accesso a `FLHCTRL6R` `0x1081` è a `0xDC22`, non analizzato.
- Ascoltare FSPI non pilota nulla, ma se l'EC legge dall'eFlash queste linee possono restare ferme.
- Da misurare sui contatti 7, 8, 9 e 10: EC 119, EC 100 e i piedini SMBus. Le piste visibili di 9 e 10 non portano a SMBus.

**Dal disegno del produttore:**

- Nello [schema](refs/img/scheda-porte-debug.png) i connettori **10, 12 e 20** sono "Debug port will be removed in the bulk". Per posizione EC_SPI1 è il **12**, ma sulla scheda fotografata è montato.
- Sulla [scheda assemblata](refs/img/ec-spi1-assemblato.png) si raggiunge dall'apertura nel telaio. La serigrafia in basso a destra si legge `ESPI_DEBUG1`.

### Piedini dell'EC

![Piedini LQFP-128, vista dall'alto](refs/img/it5571-pinout-lqfp128.png)

Datasheet `IT5571E-128.pdf`, pagina 9, intestata IT5570E. Nelle prime foto (`EC_SPI1` in alto) il chip è orientato come nella figura, con l'angolo smussato del pin 1 in alto a sinistra.

### Cosa può portare


Il datasheet prevede ISP solo via DBGR, su **EPP (pin KBS)** o **SMBus** (sezione 7.23): nessuno dei due è SPI. FSPI è confermata dalle piste, le altre righe valgono solo per i contatti ancora ignoti. Piedini da LQFP-128, Table 4-1.

| Ipotesi | Piedini EC | Indizi da `EC0416` | Se confermata |
|---|---|---|---|
| **FSPI** (flash esterna) | FSCK 105, FSCE# 101, FMOSI 102, FMISO 103, VFSPI 106 | Nessuno: pin dedicati, fuori dalla tabella GPIO | **Confermata per i contatti 2, 4, 5 e 6.** VFSPI non verificato. Nessun accesso esterno all'eFlash descritto |
| **DBGR/SMB** | SMCLK0/SMDAT0 87/88, SMCLK1/SMDAT1 115/116, SMCLK2/SMDAT2 117/118 | Non disabilitato | Il caso utile: ISP e debug (§6) |
| **UART** | TXD 17, RXD 16 | Non verificato | Solo console, se il firmware la usa |
| **SSPI** (master verso periferiche) | SSCK 32, SMOSI 56, SMISO 57, SSCE0# 100, SSCE1# 125, SBUSY 122 | Improbabile: nessun accesso a `0x2600-0x2604`, SSCK/SMOSI/SMISO GPIO in uscita, SSCE# in ingresso | Nessun ISP |

**Il firmware non blocca il debug** (analisi statica):

- `KSICTRLR` `0x1D05` riceve `0x04` dalla tabella `0x2564-0x2599`: `OVRPPK=0`, DBGR/EPP attivo. Il codice che carica la tabella non è stato individuato.
- `SLVISELR` `0x1C34` non compare mai: `OVRSMDBG=0`, DBGR/SMB attivo.
- Configurazione dei pin: tabella GPIO `0x2643-0x2777` (103 voci), caricata dal loop a `0xB290`.

**Strumenti:** FT232H per DBGR/SMB e per l'ascolto SPI, se i segnali si raggiungono. L'RP2040 è la scelta per EPP sul connettore tastiera, che non passa da questa porta (§7).

### Rischi

- `FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2` sono anche strap del **test mode** (Table 5-21): non forzarli durante l'accensione.
- Non alimentare mai la scheda dal connettore.
- Niente CH341A a 5 V: livelli al massimo 3,3 V, e 1,8 V se VFSPI lo è. Il T48 non aiuta.

## 14. Guida: riconoscere il pinout

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
4. **Altrove:** prova il chip BIOS SOIC-8 e le piazzole vicine al connettore.

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
- **SMBus collegato all'EC:** valutare DBGR/SMB (§6), prima in sola lettura.
- **UART:** utile come console, non per il flash.
- **Non collegata all'EC, o connettore assente:** resta la via KBS (§7).

La prima scrittura arriva solo dopo la verifica del dump (§6). Riporta poi il pinout in §13.

## 15. Strumenti e convenzioni

- `python3 tools/i8051.py <bin> 0 <start_hex> <end_hex>`: disassembler 8051 minimale, senza dipendenze. `tools/output/strings.txt` e `tools/output/key-regions.asm` sono artefatti generati.
- Commit raggruppati per sessione. La cartella locale non è un repo git e `inputs/` non viene pubblicata. Hash e sezioni del datasheet in `refs/DATASHEETS.md`.
