# 07 — Tasti ISO (ù, <>) non passati all'OS nella vecchia EC: analisi old vs new

Domanda: in `MTLH-NB06_E03-250322.BIN` (old) i tasti ISO ù / <> non arrivavano all'OS;
 nella nuova `EC0416.BIN` sì. Perché? Cosa cambia?

## Cosa è risultato identico (verificato byte-a-byte)

| Elemento | OLD | NEW | Esito |
|---|---|---|---|
| Tabella set2→set1 (128 B) | `0x0D2C` | `0x0D03` | **identica** (0 diff); ISO `0x61→0x56` in entrambe |
| Tabella matrice (finestra 0x200) | `0x2257` | `0x2126` | identica nella parte tabella; oltre è codice |
| Tabella flag tasti `0xE0` | `0x31BB` | `0x305E` | **identica** (144 B) |
| Sequenze multi-byte (Pausa `E1 14 77`) | `0x272B` | `0x25DC` | **identiche** |
| Routine conversione scancode | `0x0C32` | `0x0C09` | **stessa logica** (shift `+0x29`): F0→0xFF, E7→tabella, 0x83→0x41, 0x84→0x54, break `\|0x80` |
| Chiamante conversione / output KBC | `0x0BE9` | `0x0BC0` | stessa logica |
| Driver scan KBS (banco 1, loop 16 righe, KSI `0x1D04`) | `0x9300-0xA000` | idem | stessa logica; diff solo costanti shiftate (buffer xdata, LCALL) |
| Init (`0x0400`: `0x1042=0x07`, ECINDAR, FLHCTRL3R) | `0x0400` | `0x0400` | identico |
| 16B-signature `0x40`, build block `0x7F80` | presente | presente | stessa struttura |

## Cosa differisce davvero

- Il **banco 0 è ricompilato diversamente** (46608 byte totali diversi; non è uno shift
  uniforme — match a +0x29 solo ~1.7%): la vecchia è la build per board **MTLH-NB06**
  (stringa `MTLH-NB06$V0.3.2$` @ `0x1032`), la nuova per X210AI. Cambia codice di
  configurazione board, non le tabelle tastiera.
- In bank1 (`0x9300-0xA000`) 235 byte differiscono, ma dall'analisi sono costanti
  (indirizzi buffer `0x0831→0x0836` ecc.) e target di LCALL shiftati, non logica di filtro.

## Conclusione

A livello di **tabelle scancode e pipeline di conversione**, la vecchia E03-250322
**supportava già ISO/JIS esattamente come la nuova** (ISO `0x61→0x56` presente in entrambe).
Se ù/<> non arrivavano all'OS con la vecchia EC, la causa non è la traduzione scancode:
è a monte, nella **mappatura matrice fisica** (posizione riga/colonna del tasto) o nella
configurazione KBS/GPIO specifica della board MTLH-NB06 — il codice banco 0/1 di quella
build è diverso e lì va cercato il filtro/maschera che quelle posizioni non producevano.

## Come si verifica/fix su una build

1. Individuare la posizione (riga,col) del tasto ISO nella matrice (con il metodo del
   progetto T61: `Matrix_Decoder_T61.ino` / keylist).
2. Trovare la entry corrispondente nella tabella matrice del firmware e verificare che
   sia mappata (non 0x00/0xFF).
3. Se è 0x00: patcharla con lo scancode set-2 del tasto (ISO `<>` = `0x61`; la tabella
   `0x0D03`/`0x0D2C` lo traduce poi in set-1 `0x56`).
4. Verificare con disassembly (`tools/i8051.py`) e flashare (vedi doc 04/05).
