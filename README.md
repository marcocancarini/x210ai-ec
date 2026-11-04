# X210AI — ITE IT5571 EC: guida completa (reverse engineering, patch, dump/flash)

Firmware EC di una scheda **X210AI** con chip **ITE IT5571 rev. 2**: eFlash embedded 128 KiB,
core **8051**, package **LQFP-128** con piedini (14×14 mm, passo 0,4 mm), quindi la variante
`IT5571E-128` e **non** la VFBGA. Package visto in foto (§16); il marking completo è da leggere sul chip.
Questa guida è l'unico documento del progetto: contiene analisi, patch, dump/flash e
recovery. I materiali originali stanno in `inputs/` (`bios/`, `ec/`, `datasheets/`), i tool in `tools/`, i dump in `dumps/`.

## Stato del progetto

- **Firmware EC:** analizzato, patch verificate staticamente (§1-§7, §12).
- **Immagine BIOS:** **assente**, quindi il BIOS non è stato analizzato (§1, §18).
- **Brick segnalati:** meccanismo più probabile individuato nel codice di `ifu`, non riprodotto (§18).
- **Recovery:** procedure descritte ma **mai provate su questa scheda** (§13, §19).
- **Porta EC_SPI1:** pinout sconosciuto (§16, §17).

Nessun tool è stato eseguito su una X210AI: `ifu.efi`, `Fpt.efi` e i dump sono stati solo disassemblati.

## Indice

**Materiali e firmware**

- §1 [File e hash](#1-file-e-hash)
- §2 [Architettura e mappa memoria](#2-architettura-e-mappa-memoria)
- §3 [Firme e checksum (16B-signature)](#3-firme-e-checksum)
- §4 [Tastiera PS/2: scansione e conversione scancode](#4-tastiera-ps2)
- §5 [ISO / JIS: supporto nelle due versioni](#5-iso--jis)
- §12 [Livello Fn / ThinkLight (Fn+PgUp)](#12-livello-fn--thinklight-fnpgup)

**Patch**

- §6 [Patch: rimappatura tasti e swap Fn↔Ctrl](#6-patch-rimappatura-tasti-e-swap-fnctrl)
- §7 [Verifica delle patch (dimensione/logica)](#7-verifica-delle-patch)

**Flash e rischi**

- §8 [Dump e flash via software interno](#8-dump-e-flash-via-software-interno)
- §18 [Flasher: rischi di ifu.efi](#18-flasher-rischi-di-ifuefi)

**Recovery e accesso hardware**

- §13 [Se il flash dell'EC fallisce (brick) e recovery](#13-brick-e-recovery)
- §19 [Guida RP2040: ISP dal connettore tastiera](#19-guida-rp2040-isp-dal-connettore-tastiera)
- §9 [Dump/flash hardware: XGecu T48 e CH341A (± mod 3.3V)](#9-dumpflash-hardware-t48-e-ch341a)
- §10 [Scrivere il chip EC "direttamente"?](#10-scrivere-il-chip-ec-direttamente)
- §11 [Database T48: ITE non supportato](#11-database-t48-ite-non-supportato)
- §14 [Comprare il chip IT5571 da terze parti](#14-chip-di-ricambio)

**Porta di debug**

- §16 [Porta di debug EC_SPI1](#16-porta-di-debug-ec_spi1)
- §17 [Guida: riconoscere il pinout di EC_SPI1](#17-guida-riconoscere-il-pinout-di-ec_spi1)

**Varie**

- §15 [Strumenti e convenzioni](#15-strumenti-e-convenzioni)

---

## 1. File e hash

| File | SHA256 | Note |
|---|---|---|
| `dumps/EC0416.BIN` | `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca` | EC nuova X210AI, 131072 B, build `V0.3.2` 2025-04-15 18:20:35, md5 `7392fa5138c906ac17c7049fa69514e7` |
| `dumps/EC0416_ctrl-caps-swap.BIN` | `21f63a733dd5ee8b338ffefcda093ffec8d38c38138bc97c1e82a65a20acd406` | patch demo L-Ctrl↔CapsLock (2 byte) |
| `dumps/EC0416_fn-ctrl-swap.BIN` | `970431688f10aa160973d3f276c453e5cc86427a28a01ee34ef43ea17dfabee8` | patch Fn→LCtrl (1 byte) |
| `inputs/ec/MTLH-NB06-ec-250322/MTLH-NB06_E03-250322.BIN` | md5 `4bbc1e54aad8cac51a3e0a5e5274ed28` | EC vecchia (build 2025-03-22, board MTLH-NB06) |
| `inputs/datasheets/IT5571E-128.pdf` | `a4e4afae8a157b7424401cf65c9dbecddce937b8b88a3dc1474124439bfc5753` | datasheet sintetico 29 pag |
| `inputs/datasheets/IT5570_A_V0.3.1_U.pdf` | `01666ebe44ece4a436b5ffaad40c9570c17f0b3480862caf224953585c59102f` | IT5570 V0.3.1 (parente stretto di IT5571, chip ID 0x5571≈IT8571) |
| `inputs/bios/X210AI0724BIOS.rar` | `a1090b7986e6e3cb2485333f73fd5f8d62822f64bedfe7cad5733e88ddd94663` | Pacchetto strumenti, estratto in `inputs/bios/extracted/`: Fpt.efi, fparts.txt, fb.nsh, UEFI Shell (`uefi-shell/`), tutorial. **Nessuna immagine BIOS** |
| `inputs/ec/X210AI-EC-updated-on-03-22.zip` | `b850c8941df6eecbea035aefe481eb1c50fe8d5da4ea9b333717fc7a7230bc4e` | Archivio originale di `MTLH-NB06-ec-250322/`, contenuto identico |

**Immagine BIOS assente.** Il pacchetto contiene solo gli strumenti: `fb.nsh` chiama `MTLH-NB06_B0.2.bin`, che non è incluso (verificato: nessun volume firmware in alcun file del progetto). Dettagli in §18.

## 2. Architettura e mappa memoria

- CPU **8051**; vettore reset `0x0000` → `LJMP 0x0070` (init: SP=0xC0, FPCFG `0x1001=0x3F`, copia tabelle XRAM, main `0x0400`). Vettori standard `0x03/0x0B/0x13/0x1B/0x23/0x2B`; interrupt estesi ITE: stub `LJMP 0x28xx` → dispatcher `0x2800`; trampoline "sw-interrupt" `0x2B6B–0x2BE0` (`MOV DPTR,#handler; AJMP 0x2800`).
- **4 banchi × 32 KiB**, finestra commutabile `0x8000-0xFFFF` (modulo Bank base xdata `0x1300h`; FLHCTRL2R `0x1032` scritto a `0x251E`). Mappa: banco0 `0x0000-0x54D4` (fisso) + firma testuale `0x7F80`; banco1 `0x8000-0xF8A4`; banco2 `0x10000-0x15515`; banco3 `0x18000-0x18132` (stub bank-switch); resto `0xFF`.
- Base registri (datasheet §3.2): SMFI `0x1000h` (FLHCTRL1R `0x1031`, ECINDAR `0x103B-0x103F`, protect P0BA `0x104F+`), INTC `0x1100h`, EC2I `0x1200h`, **Bank `0x1300h`**, Common `0x1400h`, PMC `0x1500h`, GPIO `0x1600h`, PS/2 `0x1700h`, WUC `0x1B00h`, KBS `0x1D00h`, BRAM `0x2200h`.
- Nel firmware: KBC host = xdata `0x004B/0x004C` (porte `0x64/0x60`); PD/UCSI in banco0 `0x3400-0x4300` (USB-C PD, controller esterno Analogix).

## 3. Firme e checksum

- **Nessuna firma crittografica trovata**: niente costanti SHA/RSA/MD5/CRC, somme non nulle, blocco `0x7F80` solo testo e non referenziato, reset `0x0070` non verifica la flash, e il firmware non legge da codice la zona `0x40-0x4F`.
- **Punto aperto, byte `0x4A-0x4B`:** valgono `26 E6` in `EC0416` e `F9 0C` nella build vecchia, mentre datasheet e System76 hanno `5A 5A` fissi. Non corrispondono a somme a 8/16 bit, XOR o CRC-16 con polinomi noti sugli intervalli provati. Il firmware System76 con `5A 5A` avvia su IT5570, quindi un controllo della boot ROM è improbabile, ma **non escluso** per valori diversi da `5A 5A`. Nessuna patch risulta provata sull'hardware.
- Il solo marcatore è la **16B-signature a `0x40`** (`A5…A4 95 85 12 26 E6 AA 00 55 55`): marcatore di power-on per localizzare la code base (datasheet §6.4.3.11.1, formato "implicit" → base `0x000000`). **Va preservata intatta nelle patch** (offset validi `0x40-0xF0`).
- Protezione in scrittura: P0BA (SMFI) + PRx del descriptor — gestite da boot ROM/host, mai toccate dal firmware. Verifica con `flashrom --wp-list` / `fpt.efi`.

## 4. Tastiera PS/2

- **KBS matrix 18×8** (base `0x1D00h`: KSOL/KSOH1/KSOCTRL/KSOH2/KSI@`0x1D04`/KSOxLSDR `0x1D10-0x1D21`). Driver scan in banco1 `0x9300-0x9F00`: loop 16 righe KSO, legge KSI, indice `0x4D=(col<<4)|row|0x08`.
- **Conversione scancode**: routine `0x0C09` (F0→break marker 0xFF, bit E7→casi speciali `0x83→0x41`/`0x84→0x54`, tabella `0x0D03`, break `\|0x80`) + tabella **set2→set1 `0x0D03`** (128 B). Estesi `0xE0`: tabella `0x305E`; sequenze multi-byte (Pausa `E1 14 77`): `0x25B2`; comandi PS/2: `0x2636`.
- KBC 8042 (IRQ1/IRQ12, A20G): init `0x0A76`, dispatcher eventi `0x0D9C` (flag bit `0x30-0x3D`), host I/O via `0x004B/0x004C`.
- Flusso: KBS scan → tabella matrice → scancode set2 → conversione set1 → buffer KBC → porta `0x60` + IRQ1.

## 5. ISO / JIS

- Matrice hardware 18×8 = 144 tasti (> ISO-105 e JIS-109); layout fisico = cablaggio tastiera.
- Tabella `0x0D03` copre tutti i set-2 `0x00-0x7F` incl. tasto extra ISO `0x61→0x56`; tasti E0 in `0x305E`.
- **Confronto old vs new (E03-250322 vs EC0416)**: tabella set2→set1 (`0x0D2C` vs `0x0D03`), matrice, ext, sequenze — **byte-identiche** → **ISO e JIS supportati in entrambe**. Se nella vecchia ù/<> non passavano all'OS, la causa è nel codice di scan/mappatura matrice di quella build (board MTLH-NB06), non nelle tabelle.

## 6. Patch: rimappatura tasti e swap Fn↔Ctrl

- **Livello scancode** (tasti host-visibili): tabella `0x0D03`. Demo: `dumps/EC0416_ctrl-caps-swap.BIN` (swap L-Ctrl `0x14`↔Caps `0x58`: byte `0x0D17`↔`0x0D5B`).
- **Fn↔Ctrl**: Fn è **fuori matrice** (pin dedicato, tipo T61 I/O18→GND — rif. github.com/thedalles77/USB_Laptop_Keyboard_Controller) e **non è uno scancode** → non si scambia via tabella; non c'è logica di swap né flag BIOS letto (BRAM `0x2200h` non usata come setting). Patch lato EC: `dumps/EC0416_fn-ctrl-swap.BIN` = 1 byte a `0x0C35` (caso `0x84` in `0x0C09`: `0x54→0x1D`) → codice interno `0x84` emette LCtrl. *Caveat: non confermato al 100% che `0x84`=Fn — serve lo schema del connettore tastiera.* La direzione inversa (Ctrl fisico che fa da Fn) richiede la posizione matrice di Ctrl (driver banco1, indice `0x4D`).
- **Regole di patch**: dimensione fissa 128 KiB (pad `0xFF`), 16B-signature `0x40` intatta, non spostare tabelle (indirizzi assoluti), nessun checksum noto da aggiornare (ma vedi il punto aperto in §3); verifica con diff byte + disassembly; flash con `ifu.efi <bin> 128`, leggendo prima §18. Il flash via `ifu` dipende dal firmware in esecuzione: una patch non deve toccare il gestore `0xDC` né il ciclo di flash.

## 7. Verifica delle patch

Confronto `EC0416.BIN` (originale) vs `EC0416_fn-ctrl-swap.BIN` (patch Fn→LCtrl):

| Check | Esito |
|---|---|
| Dimensione | 131072 B = 131072 B ✓ (128 KiB corretta) |
| Byte modificati | **1 solo**: `0x0C35`: `0x54 → 0x1D` |
| Hash patch | md5 `26ea0534446468c3e863e9f372d2de0a`, sha256 `97043168…fabee8` |
| 16B-signature `0x40` | identica ✓ |
| Vettori `0x0000-0x003F`, tabella `0x0D03`, firma `0x7F80`, banchi 1-3 | identici ✓ |
| Instruction stream | intatto: cambia solo l'operando di `MOV R7,#imm` a `0x0C34` (`0x7F 54`→`0x7F 1D`), lunghezza invariata |

Disassembly del punto patchato (routine conversione `0x0C09`):

```
0C30: EF        MOV A, R7
0C31: B4 84 04  CJNE A, #0x84, 0x0C38
0C34: 7F 1D     MOV R7, #0x1D     ; patchato (originale: 7F 54)
0C36: 7E 01     MOV R6, #0x01
```

Emulazione routine `0x0C09`: `0x84` → `0x1D`/`0x9D` make/break = stesso output di L-Ctrl (`0x14`); tutti gli altri tasti (0x83, 0x14, 0x58, 0x76, 0x5A, 0x29, 0x61) invariati. **Patch efficace, dimensione corretta, nessun problema di logica.**

## 8. Dump e flash via software interno

- Dal pacchetto BIOS (`inputs/bios/`): UEFI Shell su USB (`EFI/BOOT/BOOTX64.efi`), `fpt.efi -f <bios>.bin` (BIOS) e dump `fpt.efi -d full.bin`; **EC: `ifu.efi <EC>.bin 128`** (128 = KiB).
- Linux: `flashrom -p internal -r/-w` (legge la SPI host = BIOS; l'EC embedded non è lì).
- Verifica dump: size 131072, 16B-signature `0x40`, sha256 vs `acaf8fed…`.
- ISP via KBS (datasheet §7.23.3.3/§7.24.3.1): adattatore DB25 sul connettore tastiera (KSO0-7=PD0-7, KSO8=ACK#, KSO9=BUSY, KSO10=PE, KSO12=SLCT, KSI0=STB#) → boot ROM in modo programmazione → tool ITE fa read/write eFlash. L'ingresso è lo strap `KSI[5,4,2,1]=0011b` (DBGR/EPP). Host spento, ma il datasheet richiede **VSTBY presente** e l'EC saldato sulla scheda: mai alimentare la scheda dal programmatore. Tool e limiti in §16.

## 9. Dump/flash hardware: T48 e CH341A

- Flash clippabile = solo il chip SPI BIOS (SOIC-8; chip da `inputs/bios/extracted/fparts.txt`: W25Q128, MX25L12873, N25Q128… 3.3V). Package e tensione sono dedotti da quella lista, non dalla scheda: leggere il marking e controllare il datasheet del chip. Con una flash da 1,8 V serve un adattatore di livello.
- **XGecu T48**: tensione 3.3V via software (no mod); comandi flashrom `-p xgecu-t48-spi` (se supportato) o app XGecu/MiniPro con VCC=3.3V.
- **CH341A senza mod 3.3V**: linee a 5V → **pericoloso** su flash 3.3V; usare solo con chip 5V-tolerant o adattatore di livello. Comandi: `flashrom -p ch341a_spi -r/-w/-v`.
- **CH341A con mod 3.3V**: tagliare pista/dissaldare regolatore 5V (78L05), alimentare VCC con 3.3V → poi è sicuro. Stessi comandi.
- Procedura: dump 2× e confronto hash → verifica chip (RDID) → sblocca WP se protetta → write + verify → dump post-write. Mai interrompere; macchina spenta, 3.3V solo, backup sempre.

## 10. Scrivere il chip EC "direttamente"?

**No con clip SOIC**: LQFP-128 con eFlash embedded nel die; i pin FSPI sono solo per flash esterna (datasheet Table 5-5), quindi anche una clip sui piedini non darebbe accesso SPI all'eFlash. Vie valide: ISP via KBS (in-circuit), DBGR/SMB (§16), host LPC/eSPI (HLPC §6.4.3.8/9 = fpt/flashrom/ifu), debug I2EC via `2Eh/2Fh`, oppure dissaldare + zoccolo LQFP-128 su programmatore **che abbia l'algoritmo ITE** (il T48 no, vedi §11).

Il package a piedini aiuta comunque: ogni segnale è raggiungibile con il puntale del multimetro o con un filo sottile sul piedino (passo 0,4 mm, serve mano ferma), e i piedini permettono di ricostruire il pinout del connettore di debug (§16). Sostituzione e rework non richiedono reballing.

## 11. Database T48: ITE non supportato

Lista ufficiale `T48_List.txt` V13.16 (37103 IC, mirror github.com/Kreeblah/XGecu_Software `SupportLists/`): sezione `[ ITE [Testing] ]` = **"IC Support: 0 PCS"**, nessuna entry IT55xx/IT85xx/IT8xxx → **il T48 non programma gli EC ITE**. OK solo per la flash BIOS. Per l'EC: ISP via KBS, DBGR/SMB se raggiungibile (§16) o programmatore ITE dedicato ("ITE Download Board 4").

## 12. Livello Fn / ThinkLight (Fn+PgUp)

- La patch `0x0C35` tocca solo l'output scancode del codice `0x84`: **non altera il livello Fn** (flag impostato dal pin Fn dedicato, a monte della conversione) → Fn+PgUp non è impattato dalla patch.
- Nella build vecchia Fn+PgUp non andava: causa nel codice pin/livello Fn di quella build (diversa dal nuovo), non nelle tabelle (identiche).

## 13. Brick e recovery

- Rischi noti del flasher in §18.
- Il pacchetto del produttore **non contiene istruzioni di recovery**: quelle qui sotto sono note di progetto, mai provate su questa scheda.

| Cosa si è rotto | Via | Stato |
|---|---|---|
| BIOS (chip SPI esterno) | Programmatore sul chip (§9) | Serve un'immagine: oggi non ne abbiamo una. Il dump va fatto **prima** di flashare |
| EC (eFlash nel chip) | ISP dal connettore tastiera (§8, §19) | Metodo da datasheet, dump `EC0416.BIN` disponibile. Collegamenti da ricavare |
| EC tramite `EC_SPI1` | Porta di debug (§16) | Non è una via di recovery finché il pinout è sconosciuto |

`ifu` richiede il firmware EC in esecuzione: su una macchina con EC brickata non funziona.

- Flash EC corrotto → boot ROM (ROM mascherata, intatta) non trova la 16B-signature → EC in modo ISP. Sintomi: no power-on / no tastiera / no ricarica / ventola al max.
- **Recovery**: ISP via KBS + dump originale (`EC0416.BIN`) → riparte. Funziona anche con flash illeggibile, se il chip è vivo e VSTBY presente. Sempre verifica post-write. La porta EC_SPI1 è una possibile via in più solo se il pinout confermerà i segnali DBGR/SMB (§16): oggi non va considerata un piano di recovery.
- Chip morto elettricamente (5V, ESD…) → sostituire chip (rework LQFP ad aria calda o drag soldering, senza reballing) o scheda.

## 14. Chip di ricambio

- **Per questa scheda serve il package LQFP-128**: JLCPCB/LCSC `IT5571E-128/CX` (C24833823); AliExpress/eBay IT5571E-128. Le versioni VFBGA (`IT5571VG-128/CX`, C7429720, IT5571VG-128/256) **non sono compatibili con la piazzola**. IT5570E-128 ha lo stesso package ma è un altro chip; pre-programmati per modello su icchipforlaptop.com e simili. Prima di ordinare, leggere il marking sul chip.
- Chip nuovo = eFlash vuota → programmare dopo (ISP via KBS / LPC / programmatore ITE; **non T48**). Package/size devono combaciare (qui `E-128/CX`=LQFP; `-128`=128 KiB); firmware board-specific → flashare il proprio dump. Se è fallito solo il flash, non comprare nulla: riflash via ISP.

## 15. Strumenti e convenzioni

- `python3 tools/i8051.py <bin> 0 <start_hex> <end_hex>` — disassembler 8051 minimale (no deps; `0x12`=LCALL addr16, indirizzi 16-bit big-endian). `tools/output/strings.txt`, `tools/output/key-regions.asm` = artefatti generati.
- Convenzioni repo: commit raggruppati (batch per sessione); i due repo privati restano in sync con questa cartella. Hash dei file in `refs/DATASHEETS.md`.

## 16. Porta di debug EC_SPI1

![Connettore EC_SPI1 sopra il chip ITE](refs/img/ec-spi1-connettore.png)

**Stato: connettore individuato, pinout sconosciuto.** Nessun documento pubblico trovato descrive i segnali, quindi al momento non è dimostrato che da qui si possa leggere o scrivere l'EC.

### Cosa si sa

- Connettore FPC a passo fine, serigrafia `EC_SPI1`, subito sopra l'EC, sul lato della scheda opposto alla RAM. Serigrafia letta da foto a bassa risoluzione.
- Nello [schema del produttore](refs/img/scheda-porte-debug.png) i connettori **10, 12 e 20** sono "Debug port will be removed in the bulk". Per posizione EC_SPI1 è il **12**. Le schede di serie **potrebbero non averlo**: controllare la propria.
- Sulla [scheda assemblata](refs/img/ec-spi1-assemblato.png) il connettore è montato e si raggiunge dall'apertura nel telaio. Nella stessa foto, in basso a destra, c'è la serigrafia `ESPI` vicino a un altro connettore: forse il 10, da verificare. Il 20 non è identificato.

### Cosa può portare

Il datasheet prevede ISP solo tramite DBGR, su **EPP (pin KBS)** o **SMBus** (§7.23): nessuna delle due è un bus SPI. Il nome "SPI" quindi non garantisce che la porta serva a programmare. Numeri di piedino: LQFP-128, Table 4-1.

| Ipotesi | Piedini EC | Indizi dal firmware `EC0416` | Se confermata |
|---|---|---|---|
| **FSPI** (flash esterna) | FSCK 105, FSCE# 101, FMOSI 102, FMISO 103, VFSPI 106 | Nessuno: pin dedicati, fuori dalla tabella GPIO | Il nome è compatibile, ma il datasheet non descrive accesso esterno all'eFlash da qui: un programmatore SPI può non vedere nulla |
| **DBGR/SMB** | SMCLK0/SMDAT0 87/88, SMCLK1/SMDAT1 115/116, SMCLK2/SMDAT2 117/118 (canale da verificare) | Non disabilitato (vedi sotto) | È il caso utile: ISP e debug, ma con lo strumento giusto |
| **UART** | TXD 17, RXD 16 | Non verificato | Solo console di debug, se il firmware la usa |
| **SSPI** (master verso periferiche) | SSCK 32, SMOSI 56, SMISO 57, SSCE0# 100, SSCE1# 125, SBUSY 122 | Improbabile: nessun accesso ai registri `0x2600-0x2604`; SSCK/SMOSI/SMISO sono GPIO in uscita, SSCE# in ingresso | Nessun ISP |

**Il firmware non blocca il debug** (analisi statica, non provata sull'hardware):

- `KSICTRLR` `0x1D05` riceve `0x04` dalla tabella di init `0x2564-0x2599`: `OVRPPK=0`, DBGR/EPP non disabilitato. Il codice che carica questa tabella non è stato individuato.
- `SLVISELR` `0x1C34` non compare mai: `OVRSMDBG` resta `0`, DBGR/SMB non disabilitato.
- Configurazione dei pin: tabella GPIO `0x2643-0x2777` (103 triplette indirizzo + valore), caricata dal loop a `0xB290`.

### Come identificare il pinout

Procedura completa in §17. Non esiste un pinout standard: lo decide il progettista della scheda.

**Rischi**

- `FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2` sono anche gli strap del **test mode** (Table 5-21): non forzarli durante l'accensione.
- Non alimentare mai la scheda dal connettore.
- Niente CH341A a 5 V: livelli al massimo 3,3 V, e 1,8 V se VFSPI lo è.
- Il T48 non aiuta (§11).
- DBGR/SMB non si può lasciare senza reset dopo l'ingresso (§7.23.3.2): prevedere un ciclo di alimentazione.

### Strumenti da valutare

Nessuno è dichiarato compatibile con IT5571: partire sempre dalla sola lettura. La scelta dipende dalla via: **RP2040 per EPP** sul connettore tastiera (15 linee con handshake, c'è già un progetto; collegamenti in §19), **FT232H per DBGR/SMB** e per l'ascolto SPI, se i segnali si raggiungono da EC_SPI1 o dai piedini dell'EC.

| Via | Strumento | Stato |
|---|---|---|
| EPP sul connettore tastiera | [ITE-EC-Pico-USB-Parallel-ISP](https://github.com/bernTP/ITE-EC-Pico-USB-Parallel-ISP) (RP2040/RP2350) | Provato solo su IT5261; IT5570 citato solo come fonte del datasheet. Solo 3,3 V, resistenze in serie, GND dalla scheda |
| EPP sul connettore tastiera | [system76/ec, programmatore esterno](https://github.com/system76/ec/blob/master/docs/flashing.md) (Arduino Mega 2560) | Documentato per IT5570; mappa pin da adattare alla tastiera di questa scheda |
| DBGR/SMB | [`iteflash`, Chromium EC](https://chromium.googlesource.com/chromiumos/platform/ec/+/6555d8eefedd62af8f0b0e890cb3e696690a76cc/docs/ite-ec-reflashing.md) | Scritto per IT83xx su FT4232 (Servo v2): `check_chipid()` accetta solo `0x83xx` e l'interfaccia è la B, quindi per IT5571 + FT232H va modificato. Waveform 50 ms su clock e dati, poi I2C 400 kHz agli indirizzi `0x5A/0x35/0x79`. FT232H: solo 3,3 V, pull-up esterni, DO e DI uniti per SDA |

Le procedure di alimentazione differiscono (il progetto Pico tiene l'alimentatore collegato senza batteria, la guida System76 vuole la macchina senza alimentazione): seguire quella dello strumento scelto, confrontandola con il requisito VSTBY del datasheet.

## 17. Guida: riconoscere il pinout di EC_SPI1

Obiettivo: sapere cosa porta ogni contatto prima di collegarci qualcosa. Le fasi 1-3 si fanno **senza alimentazione**; la 4 non pilota nessuna linea.

**Servono:** multimetro con cicalino e prova diodi, puntali ad ago, calibro, lente o fotocamera macro, analizzatore logico compatibile con la tensione misurata, adattatore FPC-to-DIP con cavetto (fase 2).

### Fase 1: passo e numero di contatti

**Stima dalle foto:** **10 contatti, passo 0,5 mm**. È una stima da confermare sul pezzo prima di ordinare.

| Misura | Risultato | Come |
|---|---|---|
| Scala | circa 12 px/mm | [foto vista dall'alto](refs/img/ec-spi1-connettore.png): corpo EC da 14 mm = circa 169 px |
| Larghezza corpo connettore | circa 9,9 mm | stessa foto, 119 px |
| Contatti | 10 (±1) | [ingrandimento](refs/img/ec-spi1-contatti.png): 10 terminali visibili |
| Passo | circa 0,53 mm | terminali lunghi il 48% del corpo: 4,8 mm su 9 intervalli |

Passi da 0,3 mm o 1,0 mm non sono compatibili con queste misure. **Un 12 contatti da 0,4 mm non è escluso del tutto**, se la foto nasconde dei terminali.

**Misura sul pezzo:**

1. Conta i terminali saldati, con lente o foto macro. Non contare a occhio nudo.
2. Con il calibro misura dal centro del primo terminale al centro dell'ultimo.
3. **Passo = distanza / (contatti − 1).** Con 10 contatti: 4,5 mm = passo 0,5; 3,6 mm = passo 0,4.
4. Se il calibro non entra, fotografa dall'alto con un righello appoggiato alla stessa altezza, poi rapporta i pixel.
5. Prova finale: un cavo FFC con il passo trovato è largo circa (contatti + 1) × passo, cioè circa 5,5 mm per 10 contatti da 0,5. Deve entrare nella fessura senza gioco evidente.

Annota anche: posizione del pin 1 sulla serigrafia, tipo di blocco (sportellino basculante o a slitta) e se i contatti interni stanno sopra o sotto. Quest'ultimo dato decide il verso del cavetto e il tipo di FPC.

### Fase 2: accesso ai contatti

- Batteria principale staccata e alimentatore scollegato. Se i piedini dell'EC non si raggiungono dall'apertura del telaio, smonta la scheda.
- Compra adattatore FPC-to-DIP e cavetto del passo confermato. Non infilare puntali nel connettore.
- Il cavetto può invertire l'ordine. Prima del resto, verifica con il cicalino che il contatto 1 del connettore corrisponda al pin atteso dell'adattatore e **annota la corrispondenza**.

### Fase 3: mappa con la continuità

Nell'ordine:

1. **Massa:** ogni contatto contro un foro vite dorato.
2. **Candidati:** ogni contatto contro i piedini della tabella qui sotto.
3. **Scansione:** per i contatti rimasti, fai scorrere il puntale lungo i quattro lati dell'EC finché suona, poi restringi al singolo piedino.
4. **Altrove:** se non è sull'EC, prova il chip BIOS SOIC-8 e le piazzole vicine al connettore.

| Gruppo | Segnale | Piedino EC | Note |
|---|---|---|---|
| Massa | VSS | 1, 27, 49, 91, 104 | |
| Alimentazione | VSTBY / VCC / VFSPI | 121, 114, 92 / 11 / 106 | Se c'è, **non alimentarla da fuori** |
| Reset | WRST# | 14 | |
| FSPI | FSCK / FSCE# / FMOSI / FMISO | 105 / 101 / 102 / 103 | Strap test mode |
| SMBus 0 | SMCLK0 / SMDAT0 | 87 / 88 | |
| SMBus 1 | SMCLK1 / SMDAT1 | 115 / 116 | Attivo nel firmware (funzione alternata) |
| SMBus 2 | SMCLK2 / SMDAT2 | 117 / 118 | |
| UART | TXD / RXD | 17 / 16 | |
| SSPI | SSCK / SMOSI / SMISO / SSCE0# / SSCE1# / SBUSY | 32 / 56 / 57 / 100 / 125 / 122 | SSCE0# (100) coincide con GPG2, strap test mode |

**Come leggere le misure:**

- Sotto circa 1 Ω: collegamento diretto.
- Decine di ohm: probabile resistenza in serie, conta come collegato anche se il cicalino non suona.
- Qualche kΩ verso un'alimentazione: probabile pull-up, tipico delle linee SMBus.
- Niente da nessuna parte: contatto non collegato, oppure componente non montato nelle schede di serie. Cerca piazzole vuote lungo la pista.

**Scheda da compilare** (aggiungi righe se i contatti sono di più):

| Contatto | Pin adattatore | Ω verso massa | Prova diodi | Piedino EC / altro | Tensione standby | Segnale |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | | | | | |
| 8 | | | | | | |
| 9 | | | | | | |
| 10 | | | | | | |

### Fase 4: conferma con la scheda in standby

Solo con la scheda da compilare già piena.

1. Collega l'alimentatore, macchina spenta. Tieni il puntale nero fisso sulla massa.
2. **Misura la tensione** di ogni contatto, senza toccare i vicini. Stabilisce se le linee sono a 1,8 V o 3,3 V.
3. Imposta la soglia dell'analizzatore su quella tensione e registra durante l'accensione, solo in ascolto.
4. Decodifica con sigrok/PulseView:

| Cosa si vede | Segnale probabile |
|---|---|
| Clock a raffiche, con una linea che scende durante il traffico | SPI |
| Due linee a riposo alte, con start/stop e indirizzi | SMBus |
| Una linea a riposo alta, con bit di durata costante | UART |
| Tutto fermo | Nessuna attività all'accensione: non prova che la porta sia inutile |

### Fase 5: cosa fare col risultato

- **FSPI:** niente programmatore SPI collegato alla cieca. Il datasheet non descrive accesso esterno all'eFlash da questi pin.
- **SMBus con collegamento all'EC:** via DBGR/SMB da valutare (§16), prima in sola lettura.
- **UART:** utile come console, non per il flash.
- **Non collegata all'EC, o connettore assente:** resta la via KBS (§8, §16).

In ogni caso la prima scrittura arriva solo dopo due dump identici che corrispondono a `EC0416.BIN` (sha256 §1). Riporta poi il pinout nella §16.

## 18. Flasher: rischi di ifu.efi

**Stato:** ci sono segnalazioni di brick occasionali, non riprodotte qui. L'analisi statica non prova la causa di un caso specifico, ma indica un meccanismo probabile (vedi sotto) e mostra che `ifu` non ha margine d'errore: qualsiasi problema a metà scrittura lascia l'EC senza firmware avviabile. Nulla è stato eseguito: `ifu.efi`, `Fpt.efi` e i dump sono stati solo disassemblati.

### Cosa fa ogni file

| File | Ruolo | Note |
|---|---|---|
| `inputs/bios/extracted/uefi-shell/EFI/BOOT/BOOTX64.efi`, `BOOTIA32.efi` | UEFI Shell (build 2013) | **Non scrive nulla**: è solo l'ambiente da cui lanciare i flasher, da copiare in radice sulla chiavetta |
| `inputs/ec/MTLH-NB06-ec-250322/ifu.efi` | Flasher EC: ITE Flash Utility 2.3.1a, build DEBUG | Presente solo nel pacchetto EC, non in quello BIOS |
| `inputs/bios/extracted/Fpt.efi` + `fb.nsh` | Flasher BIOS: Intel Flash Programming Tool | Dettagli sotto. `fb.nsh` esegue `fpt.efi -f MTLH-NB06_B0.2.bin`, ma **quel file non è nel pacchetto** |
| `inputs/bios/extracted/fparts.txt` | Lista di 204 voci di flash SPI | Parametri per `Fpt`; il file stesso dice che le voci non sono validate |

### Come funziona il flash EC

`ifu` non scrive l'eFlash da solo: serve la collaborazione del **firmware in esecuzione**.

1. Invia `0xAD` al KBC e `0xDC` sulla porta `0x66`.
2. Il firmware disabilita gli interrupt, porta il ciclo di flash in Scratch ROM (`0xDC94`) e ci salta (`0x800C`; variante PMC2 `0xD9D3`, caso `0xDC` nella tabella `0xF61E`). Risponde `0x33` sulla porta `0x62`. Percorso PMC1: switch `0x0A0F` → `0x0A40` → `0x0928` → `0x8A62`, **senza alcuna condizione**.
3. L'host pilota il follow mode. Per ogni blocco: cancella, verifica la cancellazione, programma, verifica.
4. Alla fine invia `0xFE`: reset tramite watchdog. Con `/j` invia `0xFC`: salto a `0x0400`.

Finché il ciclo gira, l'EC fa solo questo. Ricarica, ventola e tastiera restano ferme nello stato corrente (deduzione dal codice del ciclo).

### Debolezze verificate nel codice

| Punto | Comportamento | Conseguenza |
|---|---|---|
| ACK `0x44A9` | Se non è `0x33`, stampa `EC ACK Fail` e **prosegue** | Il tool continua senza sapere se l'EC è entrato nel ciclo |
| Attese su `0x62/0x66` | Cicli **senza timeout**, compresa l'attesa WIP `0x27DC` | Se l'EC o la flash non rispondono il tool resta bloccato, e l'unica uscita è spegnere |
| Prima di `0xDC` | Nessuno svuotamento del buffer d'uscita (`0x43D0-0x4494`) | Un byte vecchio verrebbe letto come ACK, e il `0x33` slitterebbe sulla lettura successiva, come l'ID flash |
| Errore di cancellazione o verifica `0x46F4`, `0x4758` | **Nessun nuovo tentativo**: invia `0xFE` e termina | L'EC si riavvia da una flash danneggiata, invece di restare vivo in Scratch ROM |
| Esito `0x5150` | `main` ignora il risultato; `Flash Update Fail` non è su questo percorso | L'unico segnale è la riga ` -- Verify Fail.` a schermo |
| File in ingresso | Controllata solo la dimensione rispetto al parametro; nessun controllo trovato su 16B-signature o scheda | Un file sbagliato da 128 KiB viene scritto |
| Ordine | I blocchi vengono cancellati a partire da quello con il codice di avvio | Un errore precoce elimina subito la parte necessaria per ripartire |
| Ciclo firmware | Comandi su PMC senza autenticazione; `0xDC` senza condizioni e senza uscita a tempo | Qualsiasi altro accesso a `0x62/0x66` è un comando di flash; un `0xDC` inviato per errore congela l'EC fino a reset |

### Verificato, senza problemi

- File letto in memoria **prima** di iniziare: la chiavetta non è il rischio principale.
- `128` dimenticato o sbagliato: il tool si ferma (`File Size Paramter Lost`, `Paramter NOT Match`) prima di scrivere.
- Porte non decodificate: il tool si ferma se `0x62/0x66` leggono `0xFF`.
- Build vecchia e `EC0416`: stessa tabella GPIO di 103 voci, stesso ciclo a `0x8000-0x8100`, stesso switch di comandi. Non è una regressione.
- Protezione: il firmware non scrive i registri P0BA-P3ZR.

Attenzione invece ai nomi: entrambe le build si dichiarano `V0.3.2`, pur differendo per 46.608 byte. Solo la vecchia contiene `MTLH-NB06`. Per distinguerle usare data o sha256.

### Meccanismo di brick più probabile

Ipotesi principale, ricavata dal codice e non riprodotta: **un byte rimasto nel buffer della porta `0x62`**. La catena è deterministica una volta che il byte è presente, e spiegherebbe perché il problema è occasionale.

1. `ifu` svuota il buffer del KBC (`0x2758`), ma non quello del PMC1 prima di `0xDC` (`0x4475-0x449A`).
2. Dopo l'invio attende `IBF=0`, che si azzera appena il firmware legge il comando. Il `0x33` arriva solo dopo l'ingresso in Scratch ROM (`0x8018`), quindi `ifu` legge prima il byte vecchio.
3. Stampa `EC ACK Fail.` e prosegue (`0x44A9`). Il `0x33` resta nel buffer: da qui ogni lettura restituisce il byte precedente.
4. L'ID flash risulta sbagliato, ma nessun controllo ferma il tool. Il vendor `0xFF` della eFlash è ciò che seleziona la cancellazione a settori da 1 KiB (`0xD7`, `0x3173`). Con un altro vendor il tool usa la cancellazione `0x20` da 4 KiB e la scrittura a pagine (`0x3B00`).
5. La cancellazione del primo blocco avviene comunque (`0x46E0`).
6. La verifica `0x34D4` si ferma al primo byte diverso da `0xFF` (`0x35AD`). Il primo byte letto è quello in ritardo, quindi fallisce subito.
7. `ifu` invia `0xFE` (`0x479C-0x47D3`): l'EC si riavvia con il settore di avvio cancellato. **Brick.**

**Firma da cercare:** `EC ACK Fail.`, poi ` -- Verify Fail. counterN=0` subito dopo la prima cancellazione. Il tool termina in pochi secondi invece di scrivere tutto.

La causa del byte residuo non è determinabile senza il BIOS: serve un accesso precedente alla porta EC la cui risposta non è stata letta.

Lo stesso codice esclude altre spiegazioni:

- **Watchdog EC:** il watchdog CPU e quello esterno sono attivati solo per il reset volontario (`0xD832`, `0x8100`). Il firmware non li avvia durante il funzionamento normale, quindi non scattano a metà flash.
- **Selezione della eFlash:** `XRAM[0x9F]=0x4F` viene impostata all'avvio (`0x24B0` → `0x8C74`). `ifu` invia `0xDD/0xDE` solo per gli ID `0x8631`, `0x8632`, `0x8638`.

Resta aperto un secondo rischio: nel percorso di flash (`0x2700-0x5200`) non ci sono `cli` né `RaiseTPL`. Eventuali timer del BIOS possono inserirsi tra i comandi. Dopo i comandi `0x02/0x03` il byte seguente sulla `0x66` diventa dato SPI, quindi un comando estraneo verrebbe inviato alla flash.

### Possibili cause dei brick (ipotesi)

- Firmware BIOS/SMM che accede alle porte EC durante il flash. Non verificabile senza il BIOS della X210AI.
- Un byte vecchio nel buffer d'uscita: vedi il meccanismo descritto sopra.
- Alimentazione: l'EC è fermo mentre gestisce ricarica e USB-C PD, quindi un'alimentazione solo via USB-C è il caso più sospetto.
- Blocco dell'EC, seguito da spegnimento forzato.
- Errore isolato di cancellazione o programmazione, che il tool trasforma in reset su flash danneggiata.

### Come ridurre il rischio

1. **Prima di tutto la recovery:** prova la via ISP KBS (§8, §16) in sola lettura, con dump verificato. Senza questa, un brick significa rework.
2. Controlla lo sha256 del file sulla chiavetta (§1) e usa sempre il parametro `128`.
   Prima di lanciare `ifu`, leggi la porta `0x66` dalla UEFI Shell: se il bit 0 è a 1, leggi una volta `0x62` per svuotare il buffer. Sintassi attesa, non provata su questa shell: `mm 66 -IO -w 1 -n`.
3. Alimentatore DC sul connettore dedicato e batteria carica. Evita la sola USB-C.
4. Avvia la UEFI Shell direttamente da USB e non fare altro sulla macchina.
5. Fotografa lo schermo. `EC ACK Fail` o `Verify Fail` vanno trattati come flash non riuscito, anche se il tool termina normalmente.
6. Non spegnere durante la scrittura finché c'è ancora avanzamento. Il riavvio finale è brusco ed è normale.

### Cosa manca per chiudere l'analisi

- **Immagine BIOS:** `MTLH-NB06_B0.2.bin`, oppure un dump della X210AI con `fpt.efi -d full.bin` dalla UEFI Shell o `flashrom -p internal -r` da Linux. Sola lettura.
- **Tabelle ACPI**, con `acpidump` su quella macchina.
- **Dettagli di un brick reale:** alimentazione, messaggi a schermo, stato prima del flash.

### Flash BIOS con Fpt: cosa risulta dal pacchetto

- **Piattaforma coerente:** `Fpt.efi` contiene le stringhe `Meteor Lake Platform` e `Lunar Lake Platform`. La versione esatta non è ricavabile dal file, e nemmeno la compatibilità con il ME della scheda.
- **Verifica:** l'aiuto indica `-f <file> [NOVERIFY]`, e il tool ha le fasi `Programming Flash` e `Verifying Flash`. La verifica risulta quindi prevista di default, e `fb.nsh` non la disattiva.
- **Portata:** `fb.nsh` usa `-f` senza `-bios`, quindi scrive **dall'indirizzo zero**, su tutte le regioni presenti nell'immagine. Con `-bios` si limiterebbe alla regione BIOS. Dati specifici della singola macchina possono andare persi se l'immagine li copre.
- **Prompt:** il tool può chiedere conferma (`Do you want to continue?`, `Do you want to truncate the data and continue?`). Davanti a una richiesta di troncare, **rispondere no**: significa che immagine e flash non coincidono.
- **Flash:** il marking del chip va confrontato con `fparts.txt` prima di scrivere.
- **Requisito:** la UEFI Shell del pacchetto non è firmata, quindi va probabilmente disattivato il Secure Boot.

Senza l'immagine non si possono verificare descriptor, regioni, ME, protezioni né come il BIOS usa l'EC.

## 19. Guida RP2040: ISP dal connettore tastiera

**Stato: non provata sull'IT5571.** Il progetto [ITE-EC-Pico-USB-Parallel-ISP](https://github.com/bernTP/ITE-EC-Pico-USB-Parallel-ISP) è testato solo su IT5261 (ThinkPad T14s). I segnali coincidono con il datasheet IT5570 (§7.24.3.1, Table 5-19, Table 5-21), ma la numerazione del connettore tastiera della T14s non vale qui. I collegamenti vanno ricavati sulla scheda.

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

### Trovare i contatti

1. Scheda spenta, senza batteria e senza tastiera.
2. Multimetro in continuità: un puntale sul piedino dell'EC, l'altro sui contatti del connettore tastiera.
3. Annotare il contatto di ognuno dei 15 segnali. L'orientamento può risultare specchiato.
4. Con la scheda alimentata, misurare un KSI a riposo: circa 3,3 V. **Con 5 V fermarsi.**

Saldare su una breakout del connettore, non sui piedini dell'EC (passo 0,4 mm).

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

Leggere due volte, confrontare i dump e controllare la 16B-signature a `0x40` (§3). Tra un tentativo e l'altro spegnere e scaricare l'EC: il tool ammette un solo arresto della CPU per ciclo di alimentazione.

### Differenze attese rispetto all'IT5261

- **Chip ID:** il tool non lo blocca, ma il messaggio cita `52 61 02` come riferimento. Qui il valore sarà diverso.
- **Flash ID:** se non riconosciuto, per leggere si può aggiungere `--ignore-flash-id`.
- **Scrittura:** accettata solo con eFlash ID `ff ff fe`. Non è verificato che l'IT5571 lo restituisca.
- **Area dati:** per 128 KiB potrebbe mancare la voce nel tool. In quel caso `write` riscriverebbe tutta la flash senza proteggere quell'area.

**Non usare `write`** finché dump, ID e area dati non sono stati verificati su questo chip.

### Con il chip BIOS

In generale un RP2040 può leggere una flash SPI con `pico-serprog` e `flashrom`. Non è provato su questa scheda e lavora a 3,3 V: vedi §9 per la tensione del chip.
