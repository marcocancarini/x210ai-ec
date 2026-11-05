# IT5570 — come programmare l'EC e cosa può fare un XGecu T48

Analisi del 18/10/2026.

Fonti principali:
- il datasheet `IT5570_A_V0.3.1_U.pdf` (ITE, "For A Version", V0.3.1) che si trova in questa cartella;
- il firmware `MTLH-NB06_E03-250322.BIN`;
- la lista ufficiale dei dispositivi supportati dal T48 e i progetti open source citati in fondo.

Collegato a `report.md` (scambio Fn ↔ Ctrl): qui si parla di **come scrivere** l'immagine nel chip.

> ⚠️ Riprogrammare l'EC dall'esterno vuol dire lavorare sulla scheda madre con il portatile aperto. Un collegamento sbagliato (inversione del cavo, tensioni a 5 V, alimentazione presente) può danneggiare l'EC o altri componenti. Leggi tutta la sezione 7 prima di collegare qualsiasi cosa.

---

## Indice

1. [Risposta breve](#1-risposta-breve)
2. [Cosa dice il datasheet sulla memoria del firmware](#2-cosa-dice-il-datasheet-sulla-memoria-del-firmware)
3. [Le quattro vie per scrivere il firmware](#3-le-quattro-vie-per-scrivere-il-firmware)
4. [Il T48: cosa supporta e cosa no](#4-il-t48-cosa-supporta-e-cosa-no)
5. [Verifiche da fare sulla scheda prima di scegliere](#5-verifiche-da-fare-sulla-scheda-prima-di-scegliere)
6. [Procedure dettagliate](#6-procedure-dettagliate)
7. [Sicurezza e ripristino](#7-sicurezza-e-ripristino)
8. [Dati tecnici di riferimento](#8-dati-tecnici-di-riferimento)
9. [Fonti](#9-fonti)

---

## 1. Risposta breve

- **Con il T48 non si può programmare direttamente l'IT5570.** Il firmware non sta in un chip di memoria esterno: sta nella **flash integrata (e-flash) dentro l'EC** (IT5570E, 128 KiB, come la dimensione del file). Questa flash si raggiunge solo con protocolli proprietari ITE (DBGR) o dal PC stesso.
- Nella lista ufficiale dei dispositivi del T48 (XGPro V12.78, gennaio 2025) la sezione **`[ ITE [Testing] ]` contiene 0 chip**. Il T48 supporta alcuni EC ENE (KB9010/9012/9016/9018/9022), non gli ITE. Il protocollo DBGR, inoltre, ha bisogno di una forma d'onda speciale e di comandi che il T48 non permette di personalizzare.
- **Il T48 serve solo in due casi:**
  1. se sulla scheda l'EC usa una **flash SPI esterna** sui pin FSPI. È possibile con questo chip ma improbabile su questo portatile: va controllato (sezione 5);
  2. per fare un **backup del chip SPI del BIOS** prima di qualsiasi intervento. Quel chip **non contiene il firmware dell'EC**, ma è una buona assicurazione.
- **Strade praticabili per l'EC, in ordine di preferenza:**
  1. **`ifu.efi` dalla UEFI Shell**, cioè quello che c'è già nella cartella. Non serve hardware: il PC scrive l'e-flash attraverso l'interfaccia host (eSPI/LPC) con la collaborazione del firmware EC in esecuzione.
  2. **DBGR/EPP dal connettore della tastiera**, con un Arduino Mega 2560 e un cavo flat (metodo System76, usato proprio su IT5570E). È la via di **recupero** se l'EC non si avvia più.
  3. **DBGR/SMB dai pin SMBus**, con un adattatore USB-I2C capace di generare la forma d'onda speciale (FT232H/FT2232H, metodo `iteflash` di ChromiumOS). Va adattato all'IT5570: sperimentale.

## 2. Cosa dice il datasheet sulla memoria del firmware

### 2.1 Varianti del chip

Dalle caratteristiche generali (sezione 1 del datasheet):

| Variante | Flash |
|---|---|
| IT5570E/VG-128 | **128 KB di flash integrata** |
| IT5570E/VG-256 | 256 KB di flash integrata |
| (tutte) | interfaccia FSPI a 3,3 V/1,8 V per una flash SPI esterna opzionale |

- Durata della flash integrata: oltre 100.000 cicli di cancellazione/scrittura, conservazione dei dati oltre 10 anni.
- Contenitore: LQFP-128 o VFBGA-128.
- L'immagine `MTLH-NB06_E03-250322.BIN` è di **131072 byte = 128 KiB**, compatibile con un **IT5570E-128**. La sigla esatta va letta sul chip (sezione 5).

### 2.2 Mappa della memoria del codice (Figura 3-1)

| Spazio della CPU | Indirizzo nella flash | Dimensione | Condizione |
|---|---|---|---|
| Comune `0000h–7FFFh` | `00_0000h–00_7FFFh` | 32k | sempre |
| Banco 0 `8000h–FFFFh` | `00_8000h–00_FFFFh` | 32k | ECBB=00 |
| Banco 1 `8000h–FFFFh` | `01_0000h–01_7FFFh` | 32k | ECBB=01 |
| Banco 2 `8000h–FFFFh` | `01_8000h–01_FFFFh` | 32k | ECBB=10 |

Il file `.BIN` è quindi un'immagine 1:1 della flash dall'indirizzo 0: si scrive tutta, così com'è, partendo da `0x000000`.

### 2.3 Firma di 16 byte e rilevamento della flash all'accensione (sezione 6.4.3.11)

All'accensione l'EC cerca una firma di 16 byte in un indirizzo tra `40h` e `F0h` (a passi di 16 byte) per individuare la base del codice:

```
datasheet: A5 A5 A5 A5 A5 A5 A5 [flag] 85 12 5A 5A AA AA 55 55
immagine : A5 A5 A5 A5 A5 A5 A4  95    85 12 F9 0C AA 00 55 55   (offset 0x40)
```

- Il byte flag `95h` rispetta i bit richiesti (1001 0101).
- Il 14° byte indica il range di confronto tra e-flash e flash SPI esterna, in multipli di 1 KB. Nell'immagine vale **`00`**: nessun confronto con una flash esterna. È coerente con un EC che gira dalla flash integrata.
- **Differenze rispetto al datasheet:** il 7° byte (`A4` invece di `A5`) e l'11°–12° (`F9 0C` invece di `5A 5A`). Ho provato varie ipotesi di checksum (somme a 16 bit, CRC16 su diversi intervalli) senza riscontri. Il significato resta sconosciuto. **Questi byte non vanno toccati**, e la modifica Fn/Ctrl non li tocca.

### 2.4 Modi previsti dal chip per scrivere il firmware

| Modo | Sezione | Chi scrive | Note |
|---|---|---|---|
| HLPC / follow mode dal PC | 6.4.3.8–6.4.3.9 | il PC, tramite eSPI/LPC | serve la collaborazione del firmware EC, che deve copiare codice nella scratch SRAM e dare l'accesso in scrittura all'host. È il modo usato da `ifu.efi`. |
| **DBGR/EPP** (porta parallela sul connettore tastiera) | 7.23.3.1, 7.24 | programmatore esterno | funziona **a prescindere dal firmware**. Si attiva con lo strap KSI[5,4,2,1] = `0011b` all'accensione. |
| **DBGR/SMB** (SMBus) | 7.23.3.2 | programmatore esterno | slave SMBus dedicato. Hot-plug possibile, ma una volta entrati non si esce dal modo DBGR senza reset. Disattivabile dal firmware (bit OVRSMDBG di SLVISELR). |
| Flash SPI esterna su FSPI | 5.x, Tabella 5-5 | qualsiasi programmatore SPI (anche il T48) | **solo se** la scheda monta la flash esterna. GPG2 (pin 100) ha una pull-up se FSPI è usata, una pull-down altrimenti. |

Il datasheet dice esplicitamente che ISP e debug si fanno "with software provided by ITE": **il protocollo DBGR non è documentato**. Le informazioni pratiche vengono dai progetti open source (sezioni 3.3 e 3.4).

## 3. Le quattro vie per scrivere il firmware

### 3.1 Via A — `ifu.efi` dal PC (consigliata)

- È già nella cartella: `fe.nsh` contiene `ifu.efi MTLH-NB06_E03-250322.BIN 128`.
- Requisiti: l'EC deve essere funzionante (il firmware attuale collabora alla scrittura), l'alimentatore collegato, la batteria carica.
- Vantaggi: non serve aprire il portatile né avere hardware aggiuntivo.
- Limite: se la scrittura fallisce e l'EC non si avvia più, non si può ripetere da qui e serve la via B o C.

### 3.2 Via B — DBGR/EPP dal connettore della tastiera (recupero)

- Il chip espone un'interfaccia parallela IEEE 1284 sui pin della matrice tastiera (Figura 7-43, Tabella 5-19). Il connettore flat della tastiera sulla scheda madre diventa quindi la porta di programmazione.
- Due modi per realizzarla:
  1. **ITE originale**: PC con porta parallela, cavo ITE e software ITE. Difficile da trovare.
  2. **Arduino Mega 2560** che emula la porta parallela (progetto System76 `ec`, usato sui loro portatili con IT5570E). Lo strumento legge l'ID del chip e, se il collegamento è corretto, risponde `ID: 5570 VER: …`.
- Vantaggi: funziona anche con l'EC "morto", e il connettore è già presente.
- Difficoltà: bisogna ricostruire **quale pin del connettore tastiera corrisponde a quale KSI/KSO**, perché dipende dalla scheda (sezione 6.3), e adattare la mappatura nel firmware dell'Arduino.

### 3.3 Via C — DBGR/SMB dai pin SMBus (sperimentale)

- Lo strumento `iteflash` di ChromiumOS (pensato per gli ITE IT83xx) fa così:
  1. manda una **forma d'onda speciale non-I2C** su SCL/SDA per circa 50 ms, a passi di 2,5 µs (FTDI in bit-bang);
  2. passa a I2C a 400 kHz e parla con l'EC agli indirizzi **`0x5A`** (comandi), **`0x35`** (dati) e **`0x79`** (blocchi);
  3. legge il chip ID con i comandi `0x00`/`0x01`/`0x02`.
- Per l'IT5570 bisognerebbe almeno:
  - sostituire il controllo del chip ID (`0x83xx` nel codice → **`0x5570`**, valore preso dal datasheet: CHIPID1 = `55h`, CHIPID2 = `70h`);
  - verificare il calcolo della dimensione della flash e la cancellazione dei settori, che sono specifici per IT83xx.
- Il datasheet non dice **su quale canale SMBus** risponde lo slave di debug. Di solito è il canale 0 (SMCLK0 pin 87, SMDAT0 pin 88), ma va verificato.
- Valutazione: possibile, ma richiede sviluppo e prove. Senza un'immagine di recupero funzionante non lo consiglio come prima scelta.

### 3.4 Via D — T48 su flash SPI esterna (solo se presente)

- Vale solo se la sezione 5.2 conferma che c'è una flash SPI collegata ai pin FSPI dell'EC (FSCE# 101, FMOSI 102, FMISO 103, FSCK 105, alimentazione VFSPI 106).
- In quel caso è un normale chip 25xx (SOIC-8/WSON-8), programmabile con il T48 e una pinza SOIC-8 (sezione 6.4).

## 4. Il T48: cosa supporta e cosa no

| Cosa | Supportato dal T48 | Note |
|---|---|---|
| IT5570 / qualsiasi EC ITE | **No** | lista XGPro V12.78: `[ ITE [Testing] ]` → `IC Support: 0 PCS` |
| EC ENE KB9010/9012/9016/9018/9022 (LQFP128) | Sì | non riguarda questo portatile |
| Flash SPI 25xx (BIOS, eventuale flash EC esterna) | Sì | con pinza SOIC-8, adattatori, o modalità ICSP |
| Protocolli personalizzati (forma d'onda speciale DBGR, I2C con indirizzi arbitrari) | No | XGPro usa algoritmi per dispositivi predefiniti e non permette di scriverne di nuovi |
| Generare l'emulazione della porta parallela | No | — |

**Conclusione:** per l'EC il T48 è utile solo come strumento di supporto (backup del BIOS, eventuale flash esterna). Per la scrittura dell'e-flash servono `ifu.efi`, un Arduino Mega 2560 (via B) o un adattatore FTDI (via C).

Aggiorna comunque XGPro all'ultima versione e cerca "IT55" o "ITE" nella lista dei dispositivi: se in futuro venisse aggiunto il supporto, la sezione "[ITE [Testing]]" smetterebbe di essere vuota.

## 5. Verifiche da fare sulla scheda prima di scegliere

Con il portatile spento, l'alimentatore scollegato e la batteria scollegata:

### 5.1 Identificare il chip

- Trova l'EC: un LQFP-128 quadrato con marchio **ITE** e sigla **IT5570E-128** (o `IT5570VG-128`). Di solito è vicino al connettore della tastiera.
- Fotografa la sigla completa, incluso il lotto. "E" o "VG" = flash integrata, "-128" = 128 KB.
- Se la sigla non corrisponde (ad es. -256), **fermati**: un'immagine da 128 KiB su un chip da 256 KB richiede attenzione al layout.

### 5.2 Cercare un'eventuale flash SPI dedicata all'EC

- Segui le piste dei pin **101–105** dell'EC (lato con FSCE#/FMOSI/FMISO/FSCK, accanto a VFSPI 106).
- Se arrivano a un chip a 8 pin (25xxx), quella è la flash esterna dell'EC: si può usare il T48 (via D).
- Se i pin non sono collegati, o vanno solo a resistenze o test point: **flash solo integrata** (il caso più probabile, coerente con il 14° byte della firma = `00`).
- Non confondere questo chip con il **chip SPI del BIOS** (di solito 16–32 MB, Winbond/Macronix/GigaDevice, collegato al chipset Intel e non all'EC).

### 5.3 Identificare il connettore della tastiera (per la via B)

- Annota il numero di pin (24, 26, 30…) e il passo (0,5 mm o 1,0 mm).
- Con il multimetro in modalità continuità, ricostruisci **quale pin del connettore va a quale pin KSI/KSO** dell'EC (tabella in sezione 8.2). Su LQFP-128 si misura direttamente sui piedini del chip.
- Annota anche eventuali pin di massa, LED o retroilluminazione: **non vanno collegati** all'Arduino.

### 5.4 Identificare SMBus0 (per la via C)

- Controlla dove vanno i pin 87 (SMCLK0) e 88 (SMDAT0): spesso a batteria/caricabatterie o a un test point. Annota le pull-up presenti (a 3,3 V).

## 6. Procedure dettagliate

### 6.1 Prima di tutto: backup

1. **Immagine EC originale**: è già in questa cartella (`MTLH-NB06_E03-250322.BIN`). Tienine più copie e calcola un hash:
   ```bash
   sha256sum MTLH-NB06_E03-250322.BIN > MTLH-NB06_E03-250322.BIN.sha256
   ```
2. **Backup del BIOS con il T48** (consigliato, anche se il BIOS non contiene l'EC):
   - portatile spento, batteria e alimentatore scollegati, batteria tampone CMOS possibilmente scollegata;
   - pinza SOIC-8 sul chip del BIOS (pin 1 = punto o tacca sul chip = filo rosso della pinza);
   - XGPro: **Detect/ID** per riconoscere il chip, poi scegli il modello esatto, poi **Read** e salva, poi rileggi e confronta i due file;
   - se la lettura in circuito non funziona (altri componenti alimentati dalla pinza), l'alternativa è dissaldare il chip.

### 6.2 Via A — scrittura con `ifu.efi`

1. Genera l'immagine modificata (vedi `report.md`) e controlla che differisca dall'originale solo nei byte previsti (`cmp -l`).
2. Su una chiavetta FAT32 copia: `ifu.efi`, l'immagine modificata, l'immagine originale, e gli script:
   ```
   fe_mod.nsh :  ifu.efi MTLH-NB06_FNSWAP.BIN 128
   fe_orig.nsh:  ifu.efi MTLH-NB06_E03-250322.BIN 128
   ```
3. Collega l'alimentatore, verifica che la batteria sia carica, chiudi tutto il resto.
4. Avvia la UEFI Shell (dal menu di avvio o da una chiavetta con `shellx64.efi`), passa alla chiavetta (`fs0:` o simile) e lancia `fe_mod.nsh`.
5. `ifu` controlla la dimensione (`128`), stampa il checksum e scrive. **Non spegnere e non toccare niente** finché non finisce. Alla fine l'EC si resetta e il portatile può spegnersi: togli e rimetti l'alimentazione, poi riaccendi.

### 6.3 Via B — DBGR/EPP con Arduino Mega 2560 (recupero)

**Materiale:**
- Arduino Mega 2560 **con ATmega16U2** come chip USB (non le versioni con CH340G);
- una scheda breakout FPC → passo 2,54 mm con il connettore dello stesso passo e numero di pin della tastiera (0,5 o 1,0 mm);
- cavi flat FFC dello stesso passo, sia "dritti" sia "invertiti" (contatti dallo stesso lato o da lati opposti), così il pin 1 arriva comunque al pin 1;
- un cavo USB tra portatile e PC host per avere la massa in comune;
- il repository `system76/ec` (contiene `tools/mega2560` e lo strumento di flash).

**Mappatura dei segnali** (dal datasheet, Figura 7-43 e Tabella 5-19). L'EC fa da "periferica parallela":

| Segnale parallelo | Pin EC | Funzione normale |
|---|---|---|
| STB# | 58 | KSI0 |
| AFD# | 59 | KSI1 |
| INIT# | 60 | KSI2 |
| SLIN# | 61 | KSI3 |
| (strap) | 62, 63 | KSI4, KSI5 → nel cavo ITE tramite 1 kΩ (la figura non dice verso cosa; per avere `0` dovrebbe essere massa) |
| PD0–PD7 | 36–43 | KSO0–KSO7 |
| ACK# | 44 | KSO8 |
| BUSY | 45 | KSO9 |
| PE | 46 | KSO10 |
| ERR# | 51 | KSO11 |
| SLCT | 52 | KSO12 |

L'ingresso nel modo DBGR/EPP avviene se, quando arriva l'alimentazione, KSI[5,4,2,1] = `0011b`, cioè KSI5 = 0, KSI4 = 0, KSI2 = 1, KSI1 = 1. Il programmatore deve quindi imporre questi livelli.

**Procedura:**
1. Con la continuità (sezione 5.3), compila una tabella "pin connettore tastiera → KSI/KSO" per il tuo portatile.
2. Nel firmware dell'Arduino (`tools/mega2560/parallel.c` del progetto System76) adatta la mappatura dei pin del Mega ai pin del connettore. La mappatura di System76 vale per i loro portatili, **non è garantito che coincida con il tuo**.
3. Compila e carica il firmware sul Mega:
   ```bash
   make -C tools/mega2560
   make -C tools/mega2560 flash
   ```
4. Portatile: **spento, alimentatore scollegato, batteria scollegata**. Scollega il flat della tastiera e collega al suo posto il cavo del programmatore, con il pin 1 sul pin 1.
5. Collega il cavo USB di massa e il Mega al PC host.
6. Fai prima una **lettura dell'ID e una lettura completa** della flash, e confrontala con l'immagine originale. Solo dopo, scrivi.
7. L'ID atteso è `5570`. Una risposta come `FF7F` indica collegamenti o configurazione sbagliati: **non andare avanti**.

**Limiti noti:**
- Lo strumento di System76 è pensato per scrivere il *loro* firmware sulle *loro* schede. Per scrivere un `.BIN` qualsiasi su un'altra scheda può servire adattare i comandi: verifica nel codice come accetta il file da scrivere.
- Livelli logici: il Mega lavora a 5 V e l'EC a 3,3 V. Il progetto System76 lo usa così sui loro portatili, ma il datasheet indica per i pin KBS interfacce a 3,3 V. Per sicurezza valuta **resistenze in serie o traslatori di livello**: è una mia raccomandazione prudenziale, non verificata su questa scheda.

### 6.4 Via D — T48 su flash SPI esterna (solo se presente)

1. Portatile spento, batterie scollegate.
2. Identifica il chip (sigla) e la tensione (1,8 V o 3,3 V, che deve essere uguale a VFSPI): **per un chip a 1,8 V serve l'adattatore 1,8 V del T48**.
3. Pinza SOIC-8 sul chip, poi XGPro: Detect, poi Read due volte, confronta, salva.
4. Il contenuto letto deve contenere la firma `A5 A5 A5 …` a un indirizzo tra `0x40` e `0xF0`: se c'è, è davvero il firmware EC.
5. Scrivi l'immagine modificata, rileggi e verifica.

### 6.5 Via C — DBGR/SMB con FT232H/FT2232H (sperimentale)

1. Adattatore FTDI FT232H o FT2232H (bit-bang + MPSSE I2C), con livelli a 3,3 V.
2. Collegamenti: SCL → SMCLK0 (pin 87), SDA → SMDAT0 (pin 88), GND. Le pull-up sono quelle presenti sulla scheda. Togli o isola gli altri dispositivi sullo stesso bus, se possibile.
3. Prendi `util/iteflash.c` di ChromiumOS e modifica almeno:
   - `CHIP_ID` → `0x5570` e il relativo controllo;
   - il calcolo della dimensione della flash, impostandola a 128 KiB;
   - verifica le dimensioni di pagina e settore per la cancellazione.
4. Prima prova: **solo lettura del chip ID e lettura completa**, da confrontare con il `.BIN` originale. Se coincide, il canale funziona.
5. Solo dopo valuta la scrittura.

## 7. Sicurezza e ripristino

- **Niente alimentazione** durante i collegamenti esterni (vie B, C, D): alimentatore scollegato, batteria principale scollegata. Il chip si alimenta da VSTBY a 3,3 V, che la batteria mantiene anche a portatile "spento".
- **Pin 1**: controllalo tre volte sui cavi flat. Un'inversione mette tensione su pin sbagliati.
- **Massa comune** tra programmatore, PC host e portatile.
- **Leggi prima di scrivere**: ogni metodo esterno va validato con una lettura completa confrontata con l'immagine nota.
- **Non toccare** i byte della firma a `0x40–0x4F`.
- **Piano di ripristino**: prima di flashare la versione modificata con `ifu.efi`, prepara e prova almeno la *lettura* con un metodo esterno (B o C). Così, se l'EC non si avvia, hai già una via di recupero funzionante.
- **ESD**: braccialetto antistatico, piano non conduttivo.

## 8. Dati tecnici di riferimento

### 8.1 Identificazione

| Registro | Valore |
|---|---|
| CHIPID1 / ECHIPID1 | `55h` |
| CHIPID2 / ECHIPID2 | `70h` |
| Flash integrata | 128 KB (–128) / 256 KB (–256) |
| Firma nell'immagine | offset `0x40`: `A5 A5 A5 A5 A5 A5 A4 95 85 12 F9 0C AA 00 55 55` |

### 8.2 Pin utili (LQFP-128, Tabella 4-1)

| Funzione | Pin |
|---|---|
| KSO0–KSO7 (PD0–PD7) | 36–43 |
| KSO8–KSO10 (ACK#, BUSY, PE) | 44, 45, 46 |
| KSO11–KSO15 | 51–55 |
| KSO16 / KSO17 | 56 / 57 |
| KSI0–KSI7 | 58–65 |
| SMCLK0 / SMDAT0 | 87 / 88 |
| FSCE# / FMOSI / FMISO / FSCK | 101 / 102 / 103 / 105 |
| VFSPI | 106 |
| GPG2 (strap FSPI: pull-up = flash esterna usata) | 100 |
| VSTBY | 26, 50, 92, 114, 121, 127 |
| VSS (massa) | 1, 27, 49, 91, 104 |
| VCC / VCORE | 11 / 12 |

### 8.3 Strap hardware (Tabella 5-21)

| Pin | Significato |
|---|---|
| KSI[5,4,2,1] (63, 62, 60, 59) | `0011b` = ingresso DBGR/EPP |
| FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2 | ingresso nel modo di test: **non mettere pull-up su GPG6** |
| GPG0 (125) | abilitazione del comparatore di tensione |
| ID[7:0] | identificazione della versione per il firmware |

### 8.4 Costanti DBGR/SMB (da `iteflash`, ChromiumOS; pensate per IT83xx)

| Costante | Valore |
|---|---|
| Indirizzo I2C comandi | `0x5A` |
| Indirizzo I2C dati | `0x35` |
| Indirizzo I2C blocchi | `0x79` |
| Velocità I2C | 400 kHz |
| Forma d'onda speciale | circa 50 ms, passo 2,5 µs, pattern `0x0000020301010302` sui bit SCL/SDA |
| Lettura ID | comandi `0x00`, `0x01` (ID), `0x02` (versione) |
| Reset in DBGR | scritture `2F←20`, `2E←06`, `30←40`, `27←80` |
| Uscita da DBGR | `2F←1C`, `2E←08`, `30 |= 0x10` |

## 9. Fonti

- `IT5570_A_V0.3.1_U.pdf` (in questa cartella): sezioni 1 (caratteristiche), 3 (mappa memoria), 4–5 (pin e strap), 6.4 (SMFI, programmazione HLPC, rilevamento e-flash), 7.7.4.26 (SLVISELR), 7.23 (DBGR), 7.24 (porta parallela).
- Lista dispositivi XGecu T48, XGPro V12.78: <https://www.epromirok.hu/downloads/t48_list.pdf>
- ChromiumOS EC, riprogrammazione ITE: <https://chromium.googlesource.com/chromiumos/platform/ec/+/6555d8eefedd62af8f0b0e890cb3e696690a76cc/docs/ite-ec-reflashing.md> e <https://chromium.googlesource.com/chromiumos/platform/ec/+/6555d8eefedd62af8f0b0e890cb3e696690a76cc/util/iteflash.md>
- `iteflash.c`: <https://chromium.googlesource.com/chromiumos/platform/ec/+/firmware-twinkie-9628.B/util/iteflash.c>
- System76 EC, flashing esterno: <https://github.com/system76/ec/blob/master/docs/flashing.md> e <https://github.com/system76/ec/blob/master/docs/mega2560.md>
