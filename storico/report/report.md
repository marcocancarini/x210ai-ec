# Firmware EC IT5570 — gestione del tasto Fn e scambio Fn ↔ Ctrl sinistro

Analisi del 17–18/10/2026. Firmware analizzato: `MTLH-NB06_E03-250322.BIN`.

Questo documento spiega come il firmware dell'Embedded Controller (EC) gestisce la tastiera e il tasto Fn, e descrive la procedura completa per scambiare Fn e Ctrl sinistro. La procedura è scritta per poter essere ripetuta su una release futura dello stesso firmware: gli script trovano le tabelle tramite **firme di codice** e non tramite indirizzi fissi.

> ⚠️ **Attenzione.** Riscrivere il firmware dell'EC è un'operazione rischiosa. Se l'immagine è sbagliata o il flash si interrompe, il portatile può non accendersi più (niente accensione, niente ricarica), e per recuperarlo serve un programmatore SPI/ITE esterno. Conserva sempre l'immagine originale e un modo per riscriverla.

---

## Indice

1. [Sintesi](#1-sintesi)
2. [File nella cartella](#2-file-nella-cartella)
3. [Architettura del firmware](#3-architettura-del-firmware)
4. [Percorso di un tasto, dalla matrice al PC](#4-percorso-di-un-tasto-dalla-matrice-al-pc)
5. [Formato delle tabelle](#5-formato-delle-tabelle)
6. [Gestione del tasto Fn](#6-gestione-del-tasto-fn)
7. [Matrice di questa release (V0.3.2)](#7-matrice-di-questa-release-v032)
8. [Procedura di modifica: scambio Fn ↔ Ctrl sinistro](#8-procedura-di-modifica-scambio-fn--ctrl-sinistro)
9. [Applicare la procedura a una release futura](#9-applicare-la-procedura-a-una-release-futura)
10. [Rischi, verifiche e ripristino](#10-rischi-verifiche-e-ripristino)
11. [Appendice A — script `find_tables.py`](#appendice-a--find_tablespy)
12. [Appendice B — script `swap_fn_ctrl.py`](#appendice-b--swap_fn_ctrlpy)
13. [Appendice C — script `read_last_key.py`](#appendice-c--read_last_keypy)
14. [Appendice D — disassemblatore 8051 `d51.py`](#appendice-d--d51py)
15. [Appendice E — riferimenti rapidi (indirizzi V0.3.2)](#appendice-e--riferimenti-rapidi-indirizzi-v032)

---

## 1. Sintesi

- Il firmware è un EC **ITE IT5570** (CPU 8051) con kernel ITE standard (`ITE EC-V14.6`), progetto `MTLH-NB06`, versione `V0.3.2`.
- Il tasto Fn è un **modificatore interno**: non manda nessuno scancode al PC. Mette a 1 il bit 6 del byte di stato tastiera (RAM interna `0x29`), e le tabelle Fn usano quel bit per scegliere il codice alternativo di alcuni tasti.
- Nella matrice il Fn deve comparire con il codice interno **`0x8E`**, mentre Ctrl sinistro ha il codice **`0x8C`**.
- **In V0.3.2 nessuna cella della matrice contiene `0x8E`.** Il bit Fn non può mai diventare 1, quindi il layer Fn gestito dall'EC è inattivo. Il tasto Fn fisico o finisce su una cella vuota, o non è collegato alla matrice.
- Lo scambio si fa **modificando 2 byte** della tabella della matrice:
  - nella cella di Ctrl sinistro, `0x8C` diventa `0x8E` (il tasto diventa Fn);
  - nella cella del Fn fisico, `0x00` (o `0x8E` in una release dove il Fn è mappato) diventa `0x8C` (il tasto diventa Ctrl).
- L'immagine non contiene un checksum da aggiornare.
- Dato mancante: **la posizione (riga KSI, colonna KSO) del Fn fisico**. Si ricava leggendo dall'EC l'ultima cella premuta (sezione 8.2).

## 2. File nella cartella

| File | Cosa è |
|---|---|
| `MTLH-NB06_E03-250322.BIN` | Immagine del firmware EC, 128 KiB (131072 byte). Dati utili fino a `0x18132`, il resto è `0xFF`. |
| `ifu.efi` | Flasher ITE per UEFI (applicazione EDK2, x86-64). Calcola e stampa un checksum del file ("EC file %s checksum : %04X") e controlla che la dimensione passata corrisponda. |
| `fe.nsh` | Script della UEFI Shell: `ifu.efi MTLH-NB06_E03-250322.BIN 128`. L'ultimo parametro è la dimensione in KiB. |
| `IT5570_A_V0.3.1_U.pdf` | Datasheet ITE IT5570: registri, GPIO, pinout. |

## 3. Architettura del firmware

### 3.1 CPU e memoria

- **CPU 8051** con banking del codice:
  - `0x0000–0x7FFF`: area comune, sempre visibile;
  - `0x8000–0xFFFF`: finestra a banchi. Banco 0 = offset file `0x8000–0xFFFF`, banco 1 = offset `0x10000–0x17FFF`, e così via. Il banco si sceglie con i bit P1.0–P1.2.
- Le chiamate fra banchi passano da **trampolini** nell'area comune, nella forma `mov dptr,#dest ; ajmp 0x2800`, e `0x2800`, `0x2814`, … sono i selettori di banco (`0x2800` = banco 0). Tutte le routine e le tabelle della tastiera stanno nell'area comune o nel banco 0, quindi **offset nel file = indirizzo 8051**.
- **XDATA** (memoria esterna, letta con `movx`):
  - `0x0000–0x0FFF`: RAM di lavoro del firmware;
  - `0x0400–0x04FF`: **spazio RAM ACPI dell'EC**, cioè i comandi ACPI 0x80/0x81 dell'host leggono e scrivono qui (routine a `0xDB8C`/`0xDB9F`);
  - `0x1000–0x2FFF`: registri hardware (`0x1500` canale PM/ACPI, `0x1600` GPIO, …).
- **RAM interna (IRAM)**: `0x20–0x2F` indirizzabile a bit, `0x80–0xFF` solo in modo indiretto (`@r0`/`@r1`).
- Compilatore Keil C51: chiamate indirette via `0x5A32`/`0x5AA2` e puntatori generici a 3 byte (`FF hh ll` = memoria codice).

### 3.2 Registri e variabili usati dalla tastiera

| Posizione | Significato |
|---|---|
| IRAM `0x29` | **Byte di stato dei modificatori** (`Scanner_State`). Bit: 0 NumLock, 1 Shift sinistro, 2 Shift destro, 3 Alt, 4 Ctrl, 5 Overlay, **6 Fn**. In accesso a bit: `29h.6` = bit `0x4E`. |
| IRAM `0xBC` | Copia di lavoro di `0x29`, fatta all'inizio dell'elaborazione di ogni tasto e riscritta in `0x29` alla fine. |
| XDATA `0x0027–0x0028` | Puntatore (alto, basso) alla matrice principale nella memoria codice. |
| XDATA `0x0029–0x002A` | Puntatore alla matrice estesa (colonne KSO16+). |
| XDATA `0x0826` | Cella dell'evento: nibble alto = KSO, bit 0–2 = KSI. |
| XDATA `0x0827` | Tipo di evento (pressione / ripetizione / rilascio). |
| XDATA `0x0828–0x0829` | Codice in elaborazione e tipo di evento. |
| XDATA `0x00E0–0x00EF` | Bitmap per tasto che inverte il Fn (sezione 6.3), azzerata all'avvio. |
| XDATA `0x00FA` / `0x00FB` | **Ultima cella scansionata**: KSI / KSO. Viene scritta per ogni evento, anche per le celle vuote. Per la matrice estesa: KSO + 16. |
| XDATA `0x00FC` | Marcatore della modalità di cattura scansione (`0x33`), attiva se XDATA `0x00FF` bit 6 = 1. |
| XDATA `0x1601` | Registro dati GPIO porta A (GPDRA). Il bit 6 è il pin GPA6/PWM6. |

## 4. Percorso di un tasto, dalla matrice al PC

```
Scansione hardware KSO/KSI
        │  (evento in XDATA 0x826/0x827)
        ▼
0x8C85  scan_to_code
        indice = (KSI << 4) | KSO
        codice = MOVC [matrice + indice]              ← tabella 8×16
        lcall 0xB658 → XDATA 0xFA = KSI, 0xFB = KSO   ← "ultima cella"
        ▼
0x8D77  process_code(codice, evento)
        hook OEM 0xB64C / 0xB655 (vuoti)
        IRAM 0xBC ← IRAM 0x29                         ← copia lo stato modificatori
        ├─ codice ≥ 0xE0 → tabella coppie Fn (0x31A3): [normale, Fn]
        │                  scelta = Fn_attivo XOR bit_tasto (0x8CFA)
        ├─ 0x9C ≤ codice < 0xE0 → tabella 0x3140 (flag + puntatore)
        │                  flag 0x20: [normale, Fn]
        │                  flag 0x30: [normale, NumLock, Fn, Fn+NumLock]
        └─ altrimenti codice invariato
        ▼
0x8E41  emit(codice)
        ├─ codice < 0x80 → scancode Set 2 diretto (gestore 0)
        └─ codice ≥ 0x80 → tabella SS2 (0x31BD)[codice & 0x7F] = (dato, gestore)
                           gestore → tabella 0x26FA → funzione
        ▼
IRAM 0x29 ← IRAM 0xBC                                 ← salva lo stato modificatori
```

La matrice estesa (KSO16 in su) segue un percorso parallelo: `0x9C81`, indice = KSI×3 + (KSO−16), stessa `process_code`.

## 5. Formato delle tabelle

### 5.1 Matrice principale (`0x3010` in V0.3.2)

- 128 byte = 8 righe (KSI 0–7) × 16 colonne (KSO 0–15), indice = `KSI*16 + KSO`.
- Valori:

| Valore | Significato |
|---|---|
| `0x00` | Cella vuota, ignorata. |
| `0x01–0x7F` | Scancode PS/2 Set 2 inviato direttamente (es. `0x1C` = A). |
| `0x80–0x9B` | Codice speciale risolto dalla tabella SS2 (modificatori, tasti E0, ecc.). |
| `0x9C–0xDF` | Tasto con varianti, tramite la tabella `0x3140`. |
| `0xE0–0xFF` | Tasto con coppia normale/Fn, tramite la tabella `0x31A3`, con memoria dello stato Fn per tasto. |

### 5.2 Matrice estesa (`0x3090` in V0.3.2)

24 byte = 8 KSI × 3 colonne extra. In V0.3.2 è **tutta a zero**.

### 5.3 Tabella SS2 (`0x31BD`): codici `0x80–0xFF`

Ogni voce è di 2 byte, `[dato, gestore]`, e la voce n corrisponde al codice `0x80 + n`. I gestori sono puntatori generici nella tabella `0x26FA`, 3 byte ciascuno:

| Gestore | Indirizzo | Funzione |
|---|---|---|
| 0 | `0x8F82` | Invia lo scancode `dato`. |
| 1 | `0x9010` | Invia `E0` + `dato`. |
| 2 | `0x9127` | (tasti speciali con sequenze, non usato qui) |
| 3 | `0x9196` | (non usato qui) |
| 4 | `0x91DA` | Pause / Break / PrtSc, con sequenze dalle tabelle `0x272B`/`0x2734`. |
| 5 | `0x923C` | **Modificatore**: `dato` = maschera dei bit nel byte di stato. Alla pressione fa OR, al rilascio AND NOT, e invia i prefissi Shift/Alt/Ctrl. |
| 6 | `0x92B5` | Modificatore con prefisso E0 (Alt destro, Ctrl destro). |
| 7 | `0x8FD6` | **Hotkey**: `dato` = indice nella tabella hotkey `0x30A8`. |

Voci importanti:

| Codice | Voce | Significato |
|---|---|---|
| `0x88` | `02 / h5` | Shift sinistro |
| `0x89` | `04 / h5` | Shift destro |
| `0x8A` | `08 / h5` | Alt sinistro |
| `0x8B` | `08 / h6` | Alt destro |
| **`0x8C`** | **`10 / h5`** | **Ctrl sinistro** |
| `0x8D` | `10 / h6` | Ctrl destro |
| **`0x8E`** | **`40 / h5`** | **Fn** |
| `0x8F` | `20 / h5` | Overlay |
| `0x82`/`0x83`/`0x84` | `E0 1F` / `E0 27` / `E0 2F` | Win sinistro / Win destro / Menu |
| `0x94–0x9B` | E0 + … | Home End PgUp PgDn Su Giù Sinistra Destra |
| `0x9C–0x9F` | E0 + … | Traccia successiva, Traccia precedente, Stop, Play |
| `0xA0–0xA2` | E0 + … | Muto, Vol−, Vol+ |
| `0xD0–0xDF` | `n / h7` | HOTKEY 0–15 |

### 5.4 Tabella `0x3140`: codici `0x9C–0xDF`

Ogni voce è di 3 byte, `[flag, puntatore alto, puntatore basso]`, e la voce n corrisponde al codice `0x9C + n`. Il flag dice da quali modificatori dipende la variante:

| Bit del flag | Bit di stato | Effetto sull'indice |
|---|---|---|
| 1 | Shift (sx o dx) | aggiunge un bit |
| 2 | Alt | aggiunge un bit |
| 3 | Ctrl | aggiunge un bit |
| 4 | NumLock | aggiunge un bit |
| 5 | **Fn** (con memoria per tasto) | aggiunge un bit |

- Flag `0x20` → il puntatore indica una coppia `[normale, Fn]`.
- Flag `0x30` → il puntatore indica 4 byte `[normale, NumLock, Fn, Fn+NumLock]`. È il tastierino numerico incorporato.

Il risultato può essere a sua volta un codice ≥ `0x80`, che viene risolto con la tabella SS2.

### 5.5 Tabella coppie Fn `0x31A3`: codici `0xE0–0xFF`

Ogni voce è di 2 byte, `[normale, Fn]`, e la voce n corrisponde al codice `0xE0 + n`. La scelta usa la funzione `0x8CFA` (sezione 6.3).

### 5.6 Tabella hotkey `0x30A8`

16 puntatori generici a trampolini (`0x2D0A`, `0x2D0F`, …), ognuno dei quali salta a una funzione nel banco 0 (`0xB5B7`, `0xB5BD`, …). La funzione riceve in `r7` il tipo di evento. Dopo ogni hotkey il firmware confronta i due nibble di IRAM `0x4A` e, se diversi, chiama `0x0B55` (invio dal buffer).

## 6. Gestione del tasto Fn

### 6.1 Pressione e rilascio

1. La matrice restituisce `0x8E`.
2. `emit` → SS2[`0x0E`] = `40 / gestore 5`.
3. Il gestore 5 (`0x923C`):
   - alla **pressione** fa `IRAM[0xBC] |= 0x40` e, se il bit 6 è nella maschera, salta a `0xB6D6` (hook "Fn premuto", vuoto in V0.3.2);
   - al **rilascio** chiama `0xB6D7` (hook "Fn rilasciato", vuoto) e fa `IRAM[0xBC] &= ~0x40`;
   - non invia nessuno scancode, perché Shift/Alt/Ctrl hanno prefissi ma il bit `0x40` no.
4. Alla fine di `process_code` lo stato viene riscritto in IRAM `0x29`.

**Verifica fatta:** ho cercato in tutta l'immagine ogni accesso a `0x29` e al bit `0x4E` (`setb`/`clr`/`jb`/`jnb 4Eh`, `mov 29h,…`, `orl`/`anl 29h`). Oltre al gestore 5 ci sono solo gli azzeramenti all'avvio (`0x14DD`, `0x25DA`). Quindi **il bit Fn può essere messo a 1 solo da un codice `0x8E` che arriva dalla matrice.** `process_code` viene chiamata solo da `0x8CEB` (matrice principale) e da `0x9CBB` (matrice estesa).

### 6.2 Layer Fn di V0.3.2

| Tasto (cella) | Normale | Con Fn |
|---|---|---|
| F2, F3, F5, F7, F9, F12 | tasto F | HOTKEY 1, 2, 4, 6, 8, 11: **funzioni vuote**, il tasto non viene inviato |
| **F8** | F8 | **HOTKEY 7 (`0xB5E1`): commuta GPA6** (XDATA `0x1601` bit 6, pin PWM6). Probabilmente la retroilluminazione della tastiera, non confermato. |
| Home, End, PgUp, Spazio | tasto | HOTKEY 12, 13, 14, 15: funzioni vuote |
| F4 | F4 | Sleep (`E0 3F`) |
| Freccia su / giù / sinistra / destra | freccia | Stop / Play-Pausa / Traccia precedente / Traccia successiva |
| PrtSc | `E0 7C` | SysRq (`84`) |
| ScrollLock | ScrLk | NumLock |
| Pause | Pause | Break |
| Ins, Del, Muto, Vol−, Vol+ | tasto | uguale (passano dalla tabella Fn solo per coerenza) |
| F1, F6, F10, F11, PgDn | tasto | nessuna variante |

Il tastierino numerico incorporato (7 8 9 0 / U I O P / J K L ; / M , . /) esiste nella tabella `0x3140` (codici `0x9C–0xAB`), ma **non è usato**: nella matrice quei tasti hanno i loro scancode semplici.

### 6.3 Memoria dello stato Fn per tasto (`0x8CFA`)

Per i codici ≥ `0x9C` la funzione `0x8CFA` calcola `i = codice − 0x9C` e legge il bit `i % 8` del byte XDATA `0x00E0 + i/8`. Restituisce:

```
variante_Fn = (bit 6 di IRAM[0xBC]) XOR bitmap[i]
```

La bitmap viene azzerata all'avvio (`0x8CEF`) e nel firmware non ho trovato codice che la scriva. Funziona quindi come una maschera "inverti il Fn su questo tasto" (una specie di Fn-Lock per singolo tasto). Ma la bitmap non è nello spazio ACPI `0x400–0x4FF`, quindi l'host non può impostarla con i comandi standard.

## 7. Matrice di questa release (V0.3.2)

Output di `find_tables.py` (Appendice A):

```
Header: ITE EC-V14.6 | progetto: MTLH-NB06$V0.3.2$
Init puntatori matrice @0xB6BE -> matrice 0x3010, estesa 0x3090
Tabella codici 0x80+ @0x31BD (riferita da 0x8E6C)
Tabella coppie Fn codici 0xE0+ @0x31A3
Tabella codici 0x9C+ @0x3140
Tabella gestori @0x26FA, tabella hotkey @0x30A8
Stato modificatori: IRAM 0x29 (copia di lavoro 0xBC); Fn = bit6
Ultima cella: KSI -> XDATA 0xFA, KSO -> XDATA 0xFB

Matrice (riga = KSI, colonna = KSO; "X|Fn:Y" = tasto con variante Fn)
KSI0: 0:` | 1:F1 | 2:F2|Fn:HOTKEY1 | 3:5 | 4:6 | 5:= | 6:F8|Fn:HOTKEY7 | 7:- | 8:F9|Fn:HOTKEY8 | 9:Ins|Fn:Ins | 10:Del|Fn:Del | 11:PgUp|Fn:HOTKEY14 | 12:Home|Fn:HOTKEY12 | 15:Ctrl
KSI1: 0:1 | 1:2 | 2:3 | 3:4 | 4:7 | 5:8 | 6:9 | 7:0 | 8:F10 | 9:F12|Fn:HOTKEY11 | 10:F11 | 11:PgDn | 12:End|Fn:HOTKEY13 | 13:PrtSc|Fn:SysRq
KSI2: 0:Q | 1:W | 2:E | 3:R | 4:U | 5:I | 6:O | 7:P | 10:Vol-|Fn:Vol- | 11:LWin | 13:ScrLk|Fn:NumLk
KSI3: 0:Tab | 1:Caps | 2:F3|Fn:HOTKEY2 | 3:T | 4:Y | 5:] | 6:F7|Fn:HOTKEY6 | 7:[ | 8:Bksp | 10:Vol+|Fn:Vol+ | 14:LShift
KSI4: 0:A | 1:S | 2:D | 3:F | 4:J | 5:K | 6:L | 7:; | 8:\ | 10:Mute|Fn:Mute | 11:Menu
KSI5: 0:Esc | 2:F4|Fn:Sleep | 3:G | 4:H | 5:F6 | 7:' | 8:F5|Fn:HOTKEY4 | 12:Up|Fn:Stop | 13:Alt
KSI6: 0:Z | 1:X | 2:C | 3:V | 4:M | 5:, | 6:. | 8:Enter | 12:Pause|Fn:Break | 14:RShift | 15:RCtrl
KSI7: 3:B | 4:N | 7:/ | 8:Space|Fn:HOTKEY15 | 9:Right|Fn:Next | 10:Down|Fn:Play | 12:Left|Fn:Prev | 13:RAlt
Matrice estesa (KSO16-18): tutta vuota

Ctrl sinistro (0x8C): ['KSI0 KSO15 @0x301F']
Fn (0x8E): NON PRESENTE nella matrice
Codice 0x8E nella tabella 0x80+: Fn | 0x8C: Ctrl
Celle vuote: 0/13 0/14 1/14 1/15 2/8 2/9 2/12 2/14 2/15 3/9 3/11 3/12 3/13 3/15 4/9 4/12 4/13 4/14 4/15 5/1 5/6 5/9 5/10 5/11 5/14 5/15 6/7 6/9 6/10 6/11 6/13 7/0 7/1 7/2 7/5 7/6 7/11 7/14 7/15

Hotkey (Fn+tasto), destinazioni:
  HOTKEY0  trampolino 0x2D0A -> funzione 0xB5B7
  HOTKEY1  trampolino 0x2D0F -> funzione 0xB5BD
  HOTKEY2  trampolino 0x2D14 -> funzione 0xB5C3
  HOTKEY3  trampolino 0x2D19 -> funzione 0xB5C9
  HOTKEY4  trampolino 0x2D1E -> funzione 0xB5CF
  HOTKEY5  trampolino 0x2D23 -> funzione 0xB5D5
  HOTKEY6  trampolino 0x2D28 -> funzione 0xB5DB
  HOTKEY7  trampolino 0x2D2D -> funzione 0xB5E1
  HOTKEY8  trampolino 0x2D32 -> funzione 0xB5F8
  HOTKEY9  trampolino 0x2D37 -> funzione 0xB5FE
  HOTKEY10 trampolino 0x2D3C -> funzione 0xB604
  HOTKEY11 trampolino 0x2D41 -> funzione 0xB60A
  HOTKEY12 trampolino 0x2D46 -> funzione 0xB610
  HOTKEY13 trampolino 0x2D4B -> funzione 0xB616
  HOTKEY14 trampolino 0x2D50 -> funzione 0xB61C
  HOTKEY15 trampolino 0x2D55 -> funzione 0xB622
```

Lettura: `KSIr: c:Nome`, dove `c` è la colonna KSO. `X|Fn:Y` = tasto con variante Fn.

- **Ctrl sinistro: KSI 0, KSO 15, offset file `0x301F`.**
- **Fn (`0x8E`): assente.** Il tasto Fn fisico è in una delle celle vuote elencate, oppure non è collegato alla matrice.

## 8. Procedura di modifica: scambio Fn ↔ Ctrl sinistro

### 8.1 Cosa cambia

| Tasto fisico | Prima | Dopo |
|---|---|---|
| Ctrl sinistro | Ctrl (`0x8C`) | Fn (`0x8E`): attiva il layer Fn della sezione 6.2 |
| Fn | niente (cella vuota) | Ctrl sinistro pieno (`0x8C`) |

Conseguenze da conoscere:

- Con il nuovo Fn premuto, F2/F3/F5/F7/F9/F12/Home/End/PgUp/Spazio **non inviano nulla**, perché vanno su hotkey vuoti. Fn+F8 commuta GPA6.
- Ctrl destro (`0x8D`) non cambia.
- Le scorciatoie Ctrl+… si fanno con il tasto in posizione Fn.

### 8.2 Passo 1 — trovare la cella del tasto Fn fisico

Il firmware scrive in XDATA `0x00FA`/`0x00FB` riga e colonna di **ogni** evento, comprese le celle vuote. Queste due posizioni non sono nello spazio ACPI, quindi vanno lette con l'interfaccia di debug **I2EC** della Super I/O ITE (porte `0x2E`/`0x2F`, a volte `0x4E`/`0x4F`).

Su Linux, sul portatile da modificare:

```bash
# 1. premi e rilascia SOLO il tasto Fn
# 2. subito dopo:
sudo python3 read_last_key.py
# risultato atteso, ad es.: "ultima cella: KSI=7 KSO=14"
```

Controlli:

1. Premi un tasto noto (ad es. `A` = KSI 4, KSO 0) e verifica che lo script lo legga correttamente. Questo conferma che l'I2EC funziona.
2. Premi Fn e annota KSI/KSO.
3. Verifica che la cella sia tra le **celle vuote** della sezione 7.

Casi particolari:

- Risposta `FF FF` → l'I2EC è disabilitato o le porte sono diverse. Prova a cambiare `0x2E`/`0x2F` in `0x4E`/`0x4F` nello script.
- I valori non cambiano quando premi Fn → il Fn non è collegato alla matrice (ad es. è su un GPIO). Lo scambio come descritto **non è possibile**, e bisognerebbe trovare il GPIO e aggiungere codice.
- KSO ≥ 16 → il Fn è nella matrice estesa. Va modificato il byte `matrice_estesa + KSI*3 + (KSO-16)` (lo script swap gestisce solo la matrice principale).
- Alternativa senza I2EC: la porta seriale di debug dell'EC stampa `[SCN]KSO:%d, KSI:%d` per ogni tasto (`[SCN]Et KSO…` per quelli estesi).
- Alternativa senza I2EC e senza seriale: una build di prova in cui ogni cella vuota ha uno scancode diverso e innocuo (ad es. F13–F24, Set 2 `0x08 0x10 0x18 0x20 0x28 0x30 0x38 0x40 0x48 0x50 0x57 0x5F`), da leggere con `evtest`/`showkey -s`. Richiede due flash.

### 8.3 Passo 2 — generare l'immagine modificata

```bash
python3 swap_fn_ctrl.py MTLH-NB06_E03-250322.BIN MTLH-NB06_FNSWAP.BIN <KSI> <KSO>
```

Lo script:

1. controlla l'header `ITE EC-V`;
2. trova la matrice con la firma della routine di init (non con un indirizzo fisso);
3. controlla che `0x8C` compaia esattamente una volta e che la cella indicata sia vuota;
4. scrive `0x8E` nella cella di Ctrl e `0x8C` nella cella del Fn;
5. stampa i 2 byte cambiati e la somma a 16 bit del file.

Se una release futura avrà già il Fn mappato (`0x8E` presente), basta lanciarlo **senza** KSI/KSO: scambia i due byte esistenti.

Verifica del risultato:

```bash
cmp -l MTLH-NB06_E03-250322.BIN MTLH-NB06_FNSWAP.BIN
# devono esserci esattamente 2 righe (offset decimale 1-based, valori ottali):
#   12320 214 216      ← 0x301F: 0x8C → 0x8E
#   <off>   0 214      ← cella Fn: 0x00 → 0x8C
python3 find_tables.py MTLH-NB06_FNSWAP.BIN | grep -E "Ctrl sinistro|Fn \(0x8E\)"
```

### 8.4 Passo 3 — flash

1. Copia su una chiavetta FAT32: `ifu.efi`, l'immagine modificata, l'immagine **originale** e uno script `.nsh` per ognuna:
   - `fe_swap.nsh`: `ifu.efi MTLH-NB06_FNSWAP.BIN 128`
   - `fe_orig.nsh`: `ifu.efi MTLH-NB06_E03-250322.BIN 128` (il `fe.nsh` originale)
2. Collega l'alimentatore e assicurati che la batteria sia carica. Avvia la UEFI Shell e lancia `fe_swap.nsh`.
3. Il checksum stampato da `ifu` deve cambiare rispetto all'originale. Non ho verificato con quale algoritmo lo calcola `ifu`, quindi la somma stampata da `swap_fn_ctrl.py` serve solo come riferimento indicativo.
4. Non interrompere il flash. Alla fine l'EC si riavvia, il portatile di solito si spegne del tutto, e potrebbe servire togliere e rimettere l'alimentazione.

### 8.5 Passo 4 — test

1. `evtest` / `showkey -s`: il tasto in posizione Fn deve generare `KEY_LEFTCTRL` (scancode `1d`).
2. Il tasto Ctrl fisico da solo non deve generare nulla.
3. Ctrl fisico + freccia su → Stop multimediale; Ctrl fisico + F4 → Sleep (attenzione: mette davvero in sospensione).
4. Controlla che Ctrl destro, Shift e Alt funzionino come prima.

## 9. Applicare la procedura a una release futura

### 9.1 Procedura automatica

```bash
python3 find_tables.py NUOVO.BIN
```

Lo script cerca 9 firme di codice, ognuna delle quali deve comparire **una sola volta**:

| # | Cosa trova | Firma (byte, `..` = indirizzo variabile) | Istruzioni 8051 |
|---|---|---|---|
| 1 | Puntatori matrice | `90 00 27 74 HH F0 A3 74 LL F0 90 00 29 74 HH F0 A3 74 LL F0 22` | `mov dptr,#0027h; mov a,#HH; movx…` (init) |
| 2 | Lettura matrice | `90 00 27 E0 FC A3 E0 2F F5 82 E4 3C F5 83 E4 93` | conferma indice `(KSI<<4)\|KSO` |
| 3 | Tabella SS2 | `90 .. 93 FE EF A3 93` | `mov dptr,#SS2; movc; …; inc dptr; movc` |
| 4 | Coppie Fn E0 | `90 08 2A E0 90 .. 80` | `mov dptr,#082Ah; movx; mov dptr,#E0T; sjmp` |
| 5 | Tabella 9C | `75 F0 03 90 .. 12` | `mov b,#3; mov dptr,#T9C; lcall` |
| 6 | Tabella gestori | `EC 75 F0 03 A4 24 LL F5 82 E4 34 HH F5 83 12` | `mul ab; add a,#LL; …; addc a,#HH` |
| 7 | Tabella hotkey | `CE EF CE CF ED CF 75 F0 03 EE 90 .. 12` | ingresso del gestore 7 |
| 8 | Stato tastiera | `78 .. A6 ..` | `mov r0,#BCh; mov @r0,29h` |
| 9 | Ultima cella | `90 08 28 E0 90 00 FA F0 90 08 29 E0 90 00 FB F0` | scrittura XDATA `0xFA`/`0xFB` |

Poi controlla nell'output:

1. **Header / progetto**: deve essere un IT5570 / `MTLH-NB06`.
2. **`Codice 0x8E … : Fn | 0x8C: Ctrl`**: se in SS2 questi codici hanno ancora quel significato, i valori da scrivere restano `0x8E`/`0x8C`. Altrimenti cerca nella tabella SS2 la voce con gestore 5 e maschera `0x40` (Fn) e quella con gestore 5 e maschera `0x10` (Ctrl sinistro), e usa i loro codici.
3. **`Fn (0x8E)`**: se ora è presente, la nuova release mappa il Fn e la posizione si legge direttamente da lì.
4. **Matrice**: deve contenere tasti sensati (lettere, F1–F12). Se è senza senso, la firma 1 ha trovato un falso positivo.

Se Fn è presente: `swap_fn_ctrl.py NUOVO.BIN OUT.BIN`. Altrimenti: passo 8.2 e poi `swap_fn_ctrl.py NUOVO.BIN OUT.BIN KSI KSO`.

### 9.2 Se una firma non viene trovata (analisi manuale)

Il compilatore può cambiare l'assegnazione dei registri o l'ordine delle istruzioni. Ecco come ritrovare a mano ogni elemento:

1. **Matrice (euristica sui dati)**: cerca una finestra di 128 byte con molti scancode Set 2 di lettere (`1C 32 21 23 24 2B 34 33 43 3B 42 4B 3A 31 44 4D 15 2D 1B 2C 3C 2A 1D 22 35 1A`). La matrice ha praticamente tutte le 26 lettere. Nota: anche la tabella di traduzione Set2→Set1 (`FF 43 41 3F 3D 3B 3C 58 64 44 42 40 3E 0F 29 59…`, a `0x0D2C` in V0.3.2) dà molti riscontri, ma ha una forma riconoscibile e non va confusa. Subito dopo la matrice (128 byte) inizia la matrice estesa (24 byte).
   ```python
   L=set(b'\x1c\x32\x21\x23\x24\x2b\x34\x33\x43\x3b\x42\x4b\x3a\x31\x44\x4d\x15\x2d\x1b\x2c\x3c\x2a\x1d\x22\x35\x1a')
   for i in range(len(d)-128):
       if len(L & set(d[i:i+128])) >= 24: print(hex(i))
   ```
2. **Tabella SS2**: subito dopo la matrice di solito ci sono le altre tabelle. Si riconosce dalla sequenza iniziale `83 00 5A 01 1F 01 27 01 2F 01 37 01 3F 01 5E 01` (F7, KPEnter, LWin, RWin, Menu, Power, Sleep, Wake) seguita da `02 05 04 05 08 05 08 06 10 05 10 06 40 05 20 05` (i modificatori: la coppia `40 05` è il Fn, all'indice 0x0E → codice `0x8E`).
3. **Tabella coppie Fn E0**: cerca coppie `[scancode normale, codice Fn]`. In V0.3.2 inizia con `C3 C1 7E 77 91 92 0C 86`.
4. **Tabella 9C**: voci da 3 byte che iniziano con `30 30 DE 30 30 E2 …` (flag `0x30` e puntatori crescenti di 4) e poi `20 31 1E 20 31 20 …` (flag `0x20`, passo 2).
5. **Byte di stato**: cerca `78 BC` (`mov r0,#BCh`) nelle routine della tastiera. La copia `A6 xx` indica l'indirizzo IRAM dello stato.
6. **Disassemblare**: `python3 d51.py NUOVO.BIN <inizio> <fine>` (Appendice D). Il disassemblatore è lineare: in mezzo ai dati può perdere l'allineamento, quindi parti sempre dall'inizio di una funzione (dopo un `ret` `22` o da un target di `lcall`). Per trovare chi usa un indirizzo cerca `90 HH LL` (`mov dptr,#HHLL`). Per le chiamate fra banchi cerca i trampolini `90 HH LL 01 00` (`mov dptr; ajmp 2800`).

### 9.3 Cose da ricontrollare su una release nuova

- Che il **Fn fisico** sia ancora sulla stessa cella (normalmente sì, perché dipende dal cablaggio della tastiera, non dal firmware). Se il fornitore ha aggiunto `0x8E` nella matrice, quella è la conferma.
- Che **Ctrl sinistro** sia ancora `0x8C` e compaia una sola volta.
- Che gli **hook Fn** (`0xB6D6`/`0xB6D7` in V0.3.2) e le funzioni hotkey abbiano ancora lo stesso comportamento: se ora fanno qualcosa (luminosità, Wi-Fi, …), il layer Fn sarà più utile.
- Che `ifu.efi` accetti ancora il file: stessa dimensione (128 KiB) e parametro `128` nello script `.nsh`.

## 10. Rischi, verifiche e ripristino

- **Modifica minima**: cambiano solo 2 byte di dati in una tabella costante, non il codice. Se i valori sono codici validi, il rischio legato alla modifica in sé è basso. Il rischio vero è il **processo di flash**.
- **Celle fantasma**: non riempire tutte le celle vuote con Ctrl "per sicurezza". Una tastiera senza diodi, con certe combinazioni di tre tasti, fa scattare celle inesistenti (ghosting), e ne risulterebbero pressioni di Ctrl involontarie.
- **Ripristino**: tieni sempre `fe_orig.nsh` e l'immagine originale sulla chiavetta. Se l'EC non si avvia più, serve un programmatore esterno compatibile ITE (ad es. tramite l'interfaccia di debug ITE/SMBus) o la riscrittura del chip flash.
- **`read_last_key.py`** accede direttamente alle porte I/O come root. Legge soltanto (scrive solo i registri di indice della Super I/O), ma resta un accesso diretto all'hardware: usalo solo sul portatile giusto.
- **Ipotesi non verificate**: la funzione di GPA6 (forse la retroilluminazione), l'algoritmo del checksum di `ifu`, e il fatto che l'I2EC sia abilitato su questo portatile.

---

## Appendice A — `find_tables.py`

Localizza le tabelle e decodifica la matrice. Non modifica nulla.

```python
#!/usr/bin/env python3
"""Localizza nel firmware EC ITE (kernel 8051) le tabelle della tastiera.

Uso: python3 find_tables.py FIRMWARE.BIN
Non modifica nulla: stampa indirizzi, matrice decodificata, posizione di
Fn / Ctrl sinistro, celle vuote e layer Fn.
"""
import re
import sys

d = open(sys.argv[1], 'rb').read()


def find(name, pattern, group=1):
    """Cerca una firma (regex su bytes); deve comparire esattamente una volta."""
    hits = list(re.finditer(pattern, d, re.S))
    if len(hits) != 1:
        sys.exit('FIRMA "%s": %d occorrenze (attesa 1) -> analisi manuale' % (name, len(hits)))
    return hits[0]


def w(m, g):
    b = m.group(g)
    return b[0] << 8 | b[1]


print('Header:', d[0x50:0x5C].decode(errors='replace'),
      '| progetto:', (re.search(rb'[A-Z0-9-]{4,}\$V[0-9.]+\$', d) or [b'?'])[0].decode())

# 1. Puntatori alla matrice principale (XDATA 0x27/28) e a quella estesa (0x29/2A)
m = find('init matrice',
         rb'\x90\x00\x27\x74(.)\xf0\xa3\x74(.)\xf0\x90\x00\x29\x74(.)\xf0\xa3\x74(.)\xf0\x22')
MATRIX = m.group(1)[0] << 8 | m.group(2)[0]
EXT = m.group(3)[0] << 8 | m.group(4)[0]
print('Init puntatori matrice @0x%04X -> matrice 0x%04X, estesa 0x%04X' % (m.start(), MATRIX, EXT))

# 2. Lettura matrice: indice = (KSI<<4)|KSO
find('lookup matrice', rb'\x90\x00\x27\xe0\xfc\xa3\xe0\x2f\xf5\x82\xe4\x3c\xf5\x83\xe4\x93')

# 3. Tabella codici speciali 0x80-0xFF (2 byte: dato, n. gestore)
m = find('tabella ss2 0x80+', rb'\x90(..)\x93\xfe\xef\xa3\x93')
SS2 = w(m, 1)
print('Tabella codici 0x80+ @0x%04X (riferita da 0x%04X)' % (SS2, m.start()))

# 4. Tabella coppie Fn per codici 0xE0+ (normale, con Fn)
m = find('tabella E0 Fn', rb'\x90\x08\x2a\xe0\x90(..)\x80')
E0T = w(m, 1)
print('Tabella coppie Fn codici 0xE0+ @0x%04X' % E0T)

# 5. Tabella codici 0x9C-0xDF (3 byte: flag, puntatore)
m = find('tabella 9C', rb'\x75\xf0\x03\x90(..)\x12')
T9C = w(m, 1)
print('Tabella codici 0x9C+ @0x%04X' % T9C)

# 6. Tabella gestori (puntatori generici Keil, 3 byte) e tabella hotkey
m = find('tabella gestori', rb'\xec\x75\xf0\x03\xa4\x24(.)\xf5\x82\xe4\x34(.)\xf5\x83\x12')
HND = m.group(2)[0] << 8 | m.group(1)[0]
m = find('tabella hotkey', rb'\xce\xef\xce\xcf\xed\xcf\x75\xf0\x03\xee\x90(..)\x12')
HOT = w(m, 1)
print('Tabella gestori @0x%04X, tabella hotkey @0x%04X' % (HND, HOT))

# 7. Byte di stato tastiera (copia IRAM 0x29 -> 0xBC)
m = find('stato tastiera', rb'\x78(.)\xa6(.)')
print('Stato modificatori: IRAM 0x%02X (copia di lavoro 0x%02X); Fn = bit6'
      % (m.group(2)[0], m.group(1)[0]))

# 8. Registrazione ultima cella premuta (XDATA 0xFA/0xFB)
m = find('ultima cella', rb'\x90\x08\x28\xe0\x90\x00(.)\xf0\x90\x08\x29\xe0\x90\x00(.)\xf0')
print('Ultima cella: KSI -> XDATA 0x%02X, KSO -> XDATA 0x%02X' % (m.group(1)[0], m.group(2)[0]))

# --- Decodifica -------------------------------------------------------------
S2 = {0x76: 'Esc', 0x05: 'F1', 0x06: 'F2', 0x04: 'F3', 0x0C: 'F4', 0x03: 'F5', 0x0B: 'F6',
      0x0A: 'F8', 0x01: 'F9', 0x09: 'F10', 0x78: 'F11', 0x07: 'F12', 0x0E: '`', 0x16: '1',
      0x1E: '2', 0x26: '3', 0x25: '4', 0x2E: '5', 0x36: '6', 0x3D: '7', 0x3E: '8', 0x46: '9',
      0x45: '0', 0x4E: '-', 0x55: '=', 0x66: 'Bksp', 0x0D: 'Tab', 0x15: 'Q', 0x1D: 'W',
      0x24: 'E', 0x2D: 'R', 0x2C: 'T', 0x35: 'Y', 0x3C: 'U', 0x43: 'I', 0x44: 'O', 0x4D: 'P',
      0x54: '[', 0x5B: ']', 0x5D: '\\', 0x58: 'Caps', 0x1C: 'A', 0x1B: 'S', 0x23: 'D',
      0x2B: 'F', 0x34: 'G', 0x33: 'H', 0x3B: 'J', 0x42: 'K', 0x4B: 'L', 0x4C: ';', 0x52: "'",
      0x5A: 'Enter', 0x1A: 'Z', 0x22: 'X', 0x21: 'C', 0x2A: 'V', 0x32: 'B', 0x31: 'N',
      0x3A: 'M', 0x41: ',', 0x49: '.', 0x4A: '/', 0x29: 'Space', 0x61: '<>', 0x77: 'NumLk',
      0x7E: 'ScrLk', 0x84: 'SysRq', 0x7C: 'KP*', 0x7B: 'KP-', 0x79: 'KP+', 0x83: 'F7'}
E0N = {0x1F: 'LWin', 0x27: 'RWin', 0x2F: 'Menu', 0x37: 'Power', 0x3F: 'Sleep', 0x5E: 'Wake',
       0x5A: 'KPEnter', 0x6C: 'Home', 0x69: 'End', 0x7D: 'PgUp', 0x7A: 'PgDn', 0x75: 'Up',
       0x72: 'Down', 0x6B: 'Left', 0x74: 'Right', 0x4D: 'Next', 0x15: 'Prev', 0x3B: 'Stop',
       0x34: 'Play', 0x23: 'Mute', 0x32: 'Vol-', 0x21: 'Vol+', 0x70: 'Ins', 0x71: 'Del',
       0x7C: 'PrtSc', 0x4A: 'KP/', 0x48: 'Mail', 0x10: 'WWW', 0x3A: 'Home*', 0x2B: 'Calc'}
MODS = {0x02: 'LShift', 0x04: 'RShift', 0x08: 'Alt', 0x10: 'Ctrl', 0x20: 'Overlay', 0x40: 'Fn'}


def ss2(c):
    """Nome di un codice 0x80-0xFF secondo la tabella SS2."""
    v, h = d[SS2 + 2 * (c - 0x80)], d[SS2 + 2 * (c - 0x80) + 1]
    if h == 0:
        return S2.get(v, '%02X' % v) if v else '-'
    if h == 1:
        return E0N.get(v, 'E0_%02X' % v)
    if h == 4:
        return ['Pause', 'Break', 'PrtSc'][v] if v < 3 else 'h4_%d' % v
    if h in (5, 6):
        return ('R' if h == 6 else '') + MODS.get(v, 'mod%02X' % v)
    if h == 7:
        return 'HOTKEY%d' % v
    return 'h%d_%02X' % (h, v)


def res(c):
    """Nome di un codice risultato (dopo le tabelle Fn): <0x80 Set 2, altrimenti SS2."""
    return S2.get(c, '%02X' % c) if c < 0x80 else ss2(c)


def name(c):
    if c == 0:
        return ''
    if c < 0x80:
        return S2.get(c, '%02X' % c)
    if c >= 0xE0:
        i = c - 0xE0
        return '%s|Fn:%s' % (res(d[E0T + 2 * i]), res(d[E0T + 2 * i + 1]))
    if c >= 0x9C:
        e = T9C + 3 * (c - 0x9C)
        flag, p = d[e], d[e + 1] << 8 | d[e + 2]
        if flag == 0x20:
            return '%s|Fn:%s' % (res(d[p]), res(d[p + 1]))
        return '%s|Num/Fn:%s' % (res(d[p]), res(d[p + 1]))
    return ss2(c)


print('\nMatrice (riga = KSI, colonna = KSO; "X|Fn:Y" = tasto con variante Fn)')
fn_cells, ctrl_cells, empty = [], [], []
for ksi in range(8):
    row = []
    for kso in range(16):
        off = MATRIX + ksi * 16 + kso
        c = d[off]
        row.append(name(c))
        if c == 0x8E:
            fn_cells.append((ksi, kso, off))
        if c == 0x8C:
            ctrl_cells.append((ksi, kso, off))
        if c == 0:
            empty.append((ksi, kso))
    print('KSI%d: ' % ksi + ' | '.join('%d:%s' % (k, n) for k, n in enumerate(row) if n))
ext = d[EXT:EXT + 24]
print('Matrice estesa (KSO16-18): ' + (' '.join('%02X' % b for b in ext) if any(ext) else 'tutta vuota'))

print('\nCtrl sinistro (0x8C):', ['KSI%d KSO%d @0x%04X' % c for c in ctrl_cells] or 'NON TROVATO')
print('Fn (0x8E):', ['KSI%d KSO%d @0x%04X' % c for c in fn_cells] or 'NON PRESENTE nella matrice')
print('Codice 0x8E nella tabella 0x80+:', ss2(0x8E), '| 0x8C:', ss2(0x8C))
print('Celle vuote:', ' '.join('%d/%d' % c for c in empty))

print('\nHotkey (Fn+tasto), destinazioni:')
for i in range(16):
    e = HOT + 3 * i
    tramp = d[e + 1] << 8 | d[e + 2]
    tgt = d[tramp + 1] << 8 | d[tramp + 2] if d[tramp] == 0x90 else None
    print('  HOTKEY%-2d trampolino 0x%04X -> funzione 0x%s' % (i, tramp, '%04X' % tgt if tgt else '?'))
```

## Appendice B — `swap_fn_ctrl.py`

Genera l'immagine con Fn e Ctrl scambiati. Non flasha.

```python
#!/usr/bin/env python3
"""Genera una copia del firmware EC ITE con Fn e Ctrl sinistro scambiati.

Uso:
  swap_fn_ctrl.py INPUT.BIN OUTPUT.BIN               # se Fn (0x8E) e' gia' nella matrice
  swap_fn_ctrl.py INPUT.BIN OUTPUT.BIN KSI KSO       # se Fn manca: cella del Fn fisico

Trova la matrice tramite la firma della routine di init, non per indirizzo
fisso, quindi funziona anche se una nuova release sposta le tabelle.
Non flasha nulla.
"""
import re
import sys

FN, LCTRL = 0x8E, 0x8C   # codici interni ITE: Fn = modificatore 0x40, LCtrl = 0x10

src, dst = sys.argv[1], sys.argv[2]
d = bytearray(open(src, 'rb').read())
assert d[0x50:0x58] == b'ITE EC-V', 'non sembra un firmware EC ITE'

hits = list(re.finditer(
    rb'\x90\x00\x27\x74(.)\xf0\xa3\x74(.)\xf0\x90\x00\x29\x74(.)\xf0\xa3\x74(.)\xf0\x22', d, re.S))
assert len(hits) == 1, 'firma init matrice trovata %d volte: serve analisi manuale' % len(hits)
MATRIX = hits[0].group(1)[0] << 8 | hits[0].group(2)[0]
print('matrice @0x%04X' % MATRIX)

cells = d[MATRIX:MATRIX + 128]
ctrl = [i for i, c in enumerate(cells) if c == LCTRL]
fn = [i for i, c in enumerate(cells) if c == FN]
assert len(ctrl) == 1, 'Ctrl sinistro trovato %d volte' % len(ctrl)
ctrl_off = MATRIX + ctrl[0]

if len(sys.argv) == 5:
    ksi, kso = int(sys.argv[3]), int(sys.argv[4])
    assert 0 <= ksi < 8 and 0 <= kso < 16
    assert not fn, 'Fn e\' gia\' nella matrice: lancia senza KSI/KSO'
    fn_off = MATRIX + ksi * 16 + kso
    assert d[fn_off] == 0x00, 'la cella indicata non e\' vuota: 0x%02X' % d[fn_off]
else:
    assert len(fn) == 1, 'Fn non presente nella matrice: indica KSI e KSO del tasto Fn fisico'
    fn_off = MATRIX + fn[0]

old_ctrl, old_fn = d[ctrl_off], d[fn_off]
d[ctrl_off], d[fn_off] = FN, LCTRL
open(dst, 'wb').write(d)
for off, old, new in ((ctrl_off, old_ctrl, FN), (fn_off, old_fn, LCTRL)):
    i = off - MATRIX
    print('0x%05X (KSI%d KSO%d): %02X -> %02X' % (off, i // 16, i % 16, old, new))
print('somma 16 bit del file (riferimento, algoritmo ifu non verificato): %04X' % (sum(d) & 0xFFFF))
```

## Appendice C — `read_last_key.py`

Legge via I2EC l'ultima cella scansionata (XDATA `0xFA`/`0xFB`). Va eseguito come root sul portatile.

```python
#!/usr/bin/env python3
"""Legge (sola lettura) l'ultima cella KSI/KSO scansionata dall'EC IT5570.

Il firmware scrive a ogni evento tasto KSI in XDATA 0x00FA e KSO in 0x00FB,
anche per le celle vuote. Lettura via interfaccia I2EC della Super I/O
(porte 0x2E/0x2F). Richiede root. Uso: premi e rilascia Fn, poi lancia.
"""
import os

fd = os.open('/dev/port', os.O_RDWR)

def outb(port, val):
    os.lseek(fd, port, 0); os.write(fd, bytes([val]))

def inb(port):
    os.lseek(fd, port, 0); return os.read(fd, 1)[0]

def sio(reg, val=None):
    outb(0x2E, 0x2E); outb(0x2F, reg); outb(0x2E, 0x2F)
    if val is None:
        return inb(0x2F)
    outb(0x2F, val)

def xdata(addr):
    sio(0x11, addr >> 8)
    sio(0x10, addr & 0xFF)
    return sio(0x12)

ksi, kso = xdata(0x00FA), xdata(0x00FB)
print('ultima cella: KSI=%d KSO=%d' % (ksi, kso))
if ksi == 0xFF and kso == 0xFF:
    print('lettura 0xFF: probabilmente I2EC disabilitato o porta diversa (0x4E/0x4F)')
```

## Appendice D — `d51.py`

Disassemblatore 8051 minimale e lineare, scritto per questa analisi. Uso: `python3 d51.py FILE.BIN <inizio_hex> <fine_hex>`.

```python
import sys
# minimal 8051 disassembler
T={}
def r(o,n,f): T[o]=(n,f)
r(0x00,1,'nop');r(0x02,3,'ljmp {a16}');r(0x03,1,'rr a');r(0x04,1,'inc a');r(0x05,2,'inc {d1}');r(0x06,1,'inc @r0');r(0x07,1,'inc @r1')
for i in range(8): r(0x08+i,1,'inc r%d'%i)
r(0x10,3,'jbc {b1},{rel3}');r(0x12,3,'lcall {a16}');r(0x13,1,'rrc a');r(0x14,1,'dec a');r(0x15,2,'dec {d1}');r(0x16,1,'dec @r0');r(0x17,1,'dec @r1')
for i in range(8): r(0x18+i,1,'dec r%d'%i)
r(0x20,3,'jb {b1},{rel3}');r(0x22,1,'ret');r(0x23,1,'rl a');r(0x24,2,'add a,#{i1}');r(0x25,2,'add a,{d1}');r(0x26,1,'add a,@r0');r(0x27,1,'add a,@r1')
for i in range(8): r(0x28+i,1,'add a,r%d'%i)
r(0x30,3,'jnb {b1},{rel3}');r(0x32,1,'reti');r(0x33,1,'rlc a');r(0x34,2,'addc a,#{i1}');r(0x35,2,'addc a,{d1}');r(0x36,1,'addc a,@r0');r(0x37,1,'addc a,@r1')
for i in range(8): r(0x38+i,1,'addc a,r%d'%i)
r(0x40,2,'jc {rel2}');r(0x42,2,'orl {d1},a');r(0x43,3,'orl {d1},#{i2}');r(0x44,2,'orl a,#{i1}');r(0x45,2,'orl a,{d1}');r(0x46,1,'orl a,@r0');r(0x47,1,'orl a,@r1')
for i in range(8): r(0x48+i,1,'orl a,r%d'%i)
r(0x50,2,'jnc {rel2}');r(0x52,2,'anl {d1},a');r(0x53,3,'anl {d1},#{i2}');r(0x54,2,'anl a,#{i1}');r(0x55,2,'anl a,{d1}');r(0x56,1,'anl a,@r0');r(0x57,1,'anl a,@r1')
for i in range(8): r(0x58+i,1,'anl a,r%d'%i)
r(0x60,2,'jz {rel2}');r(0x62,2,'xrl {d1},a');r(0x63,3,'xrl {d1},#{i2}');r(0x64,2,'xrl a,#{i1}');r(0x65,2,'xrl a,{d1}');r(0x66,1,'xrl a,@r0');r(0x67,1,'xrl a,@r1')
for i in range(8): r(0x68+i,1,'xrl a,r%d'%i)
r(0x70,2,'jnz {rel2}');r(0x72,2,'orl c,{b1}');r(0x73,1,'jmp @a+dptr');r(0x74,2,'mov a,#{i1}');r(0x75,3,'mov {d1},#{i2}');r(0x76,2,'mov @r0,#{i1}');r(0x77,2,'mov @r1,#{i1}')
for i in range(8): r(0x78+i,2,'mov r%d,#{i1}'%i)
r(0x80,2,'sjmp {rel2}');r(0x82,2,'anl c,{b1}');r(0x83,1,'movc a,@a+pc');r(0x84,1,'div ab');r(0x85,3,'mov {d2},{d1}');r(0x86,2,'mov {d1},@r0');r(0x87,2,'mov {d1},@r1')
for i in range(8): r(0x88+i,2,'mov {d1},r%d'%i)
r(0x90,3,'mov dptr,#{i16}');r(0x92,2,'mov {b1},c');r(0x93,1,'movc a,@a+dptr');r(0x94,2,'subb a,#{i1}');r(0x95,2,'subb a,{d1}');r(0x96,1,'subb a,@r0');r(0x97,1,'subb a,@r1')
for i in range(8): r(0x98+i,1,'subb a,r%d'%i)
r(0xa0,2,'orl c,/{b1}');r(0xa2,2,'mov c,{b1}');r(0xa3,1,'inc dptr');r(0xa4,1,'mul ab');r(0xa5,1,'db a5');r(0xa6,2,'mov @r0,{d1}');r(0xa7,2,'mov @r1,{d1}')
for i in range(8): r(0xa8+i,2,'mov r%d,{d1}'%i)
r(0xb0,2,'anl c,/{b1}');r(0xb2,2,'cpl {b1}');r(0xb3,1,'cpl c');r(0xb4,3,'cjne a,#{i1},{rel3}');r(0xb5,3,'cjne a,{d1},{rel3}');r(0xb6,3,'cjne @r0,#{i1},{rel3}');r(0xb7,3,'cjne @r1,#{i1},{rel3}')
for i in range(8): r(0xb8+i,3,'cjne r%d,#{i1},{rel3}'%i)
r(0xc0,2,'push {d1}');r(0xc2,2,'clr {b1}');r(0xc3,1,'clr c');r(0xc4,1,'swap a');r(0xc5,2,'xch a,{d1}');r(0xc6,1,'xch a,@r0');r(0xc7,1,'xch a,@r1')
for i in range(8): r(0xc8+i,1,'xch a,r%d'%i)
r(0xd0,2,'pop {d1}');r(0xd2,2,'setb {b1}');r(0xd3,1,'setb c');r(0xd4,1,'da a');r(0xd5,3,'djnz {d1},{rel3}');r(0xd6,1,'xchd a,@r0');r(0xd7,1,'xchd a,@r1')
for i in range(8): r(0xd8+i,2,'djnz r%d,{rel2}'%i)
r(0xe0,1,'movx a,@dptr');r(0xe2,1,'movx a,@r0');r(0xe3,1,'movx a,@r1');r(0xe4,1,'clr a');r(0xe5,2,'mov a,{d1}');r(0xe6,1,'mov a,@r0');r(0xe7,1,'mov a,@r1')
for i in range(8): r(0xe8+i,1,'mov a,r%d'%i)
r(0xf0,1,'movx @dptr,a');r(0xf2,1,'movx @r0,a');r(0xf3,1,'movx @r1,a');r(0xf4,1,'cpl a');r(0xf5,2,'mov {d1},a');r(0xf6,1,'mov @r0,a');r(0xf7,1,'mov @r1,a')
for i in range(8): r(0xf8+i,1,'mov r%d,a'%i)
for k in range(8):
    r(0x01+k*0x20,2,'ajmp {a11}'); r(0x11+k*0x20,2,'acall {a11}')
SFR={0x81:'sp',0x82:'dpl',0x83:'dph',0xe0:'acc',0xf0:'b',0xd0:'psw',0xa8:'ie',0x90:'p1',0x80:'p0',0xa0:'p2',0xb0:'p3'}
def dis(d,base,start,end,banklo=0):
    pc=start
    out=[]
    while pc<end:
        o=d[pc-base]; n,f=T.get(o,(1,'db %02x'%o))
        b=d[pc-base:pc-base+n]
        def dd(x): return SFR.get(x,'%02xh'%x)
        def bb(x):
            if x<0x80: return '%02xh.%d'%(0x20+x//8,x%8)
            return '%s.%d'%(dd(x&0xf8),x&7)
        s=f
        if '{a16}' in s: s=s.replace('{a16}','%04x'%(b[1]<<8|b[2]))
        if '{i16}' in s: s=s.replace('{i16}','%04xh'%(b[1]<<8|b[2]))
        if '{a11}' in s: s=s.replace('{a11}','%04x'%(((pc+2)&0xf800)|((o>>5)<<8)|b[1]))
        if '{rel2}' in s: s=s.replace('{rel2}','%04x'%((pc+2+((b[1]^0x80)-0x80))&0xffff))
        if '{rel3}' in s: s=s.replace('{rel3}','%04x'%((pc+3+((b[2]^0x80)-0x80))&0xffff))
        if o==0x85: s='mov %s,%s'%(dd(b[2]),dd(b[1]))
        else:
            s=s.replace('{d1}',dd(b[1]) if n>1 else '').replace('{b1}',bb(b[1]) if n>1 else '')
            s=s.replace('{i1}','%02xh'%b[1] if n>1 else '').replace('{i2}','%02xh'%b[2] if n>2 else '')
        out.append('%04x: %-9s %s'%(pc,b.hex(),s))
        pc+=n
    return out
if __name__=='__main__':
    d=open(sys.argv[1],'rb').read()
    s=int(sys.argv[2],16); e=int(sys.argv[3],16); base=int(sys.argv[4],16) if len(sys.argv)>4 else 0
    print('\n'.join(dis(d,-base,s,e)))
```

## Appendice E — riferimenti rapidi (indirizzi V0.3.2)

| Indirizzo | Cosa |
|---|---|
| `0x0050` | Stringa `ITE EC-V14.6` |
| `0x0D2C` | Tabella di traduzione Set2 → Set1 (8042) |
| `0x26FA` | Tabella gestori SS2 (8 × 3 byte) |
| `0x2800` | Selettore banco 0 (trampolini) |
| `0x2D0A` | Trampolini hotkey |
| `0x3010` | **Matrice principale 8×16** |
| `0x301F` | **Cella Ctrl sinistro (KSI0/KSO15) = `0x8C`** |
| `0x3090` | Matrice estesa 8×3 (vuota) |
| `0x30A8` | Tabella hotkey (16 × 3 byte) |
| `0x30DE` | Tastierino incorporato (4 byte per voce) |
| `0x311E` | Coppie Fn per codici `0xAC–0xBC` |
| `0x3140` | Tabella codici `0x9C+` (3 byte per voce) |
| `0x31A3` | Coppie Fn per codici `0xE0+` |
| `0x31BD` | Tabella SS2 codici `0x80+` (2 byte per voce) |
| `0x8C85` | scan_to_code (matrice principale) |
| `0x8CEF` | Azzeramento bitmap XDATA `0xE0–0xEF` |
| `0x8CFA` | Scelta della variante Fn (XOR con bitmap) |
| `0x8D77` | process_code |
| `0x8E41` | emit (risoluzione SS2) |
| `0x8E8F` | Calcolo indice variante (Shift/Alt/Ctrl/NumLock/Fn) |
| `0x923C` | Gestore 5: modificatori (incluso Fn) |
| `0x97CE` | Init tastiera (chiama `0xB6BE`) |
| `0x9C81` | scan_to_code (matrice estesa) |
| `0xB5E1` | HOTKEY 7 (Fn+F8): commuta GPA6 |
| `0xB658` | Scrittura ultima cella in XDATA `0xFA`/`0xFB` |
| `0xB6BE` | Init puntatori matrice |
| `0xB6D6` / `0xB6D7` | Hook Fn premuto / rilasciato (vuoti) |
| `0xDB8C` / `0xDB9F` | Lettura / scrittura RAM ACPI (XDATA `0x400+`) |
