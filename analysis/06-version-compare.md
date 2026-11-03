# 06 — Confronto EC vecchio (MTLH-NB06_E03-250322) vs nuovo (EC0416) — ISO/JIS

## File confrontati

| | Vecchio | Nuovo |
|---|---|---|
| File | `MTLH-NB06-ec-250322/MTLH-NB06_E03-250322.BIN` | `dumps/EC0416.BIN` |
| Size | 131072 (128 KiB) | 131072 (128 KiB) |
| MD5 | `4bbc1e54aad8cac51a3e0a5e5274ed28` | `7392fa5138c906ac17c7049fa69514e7` |
| Build block `0x7F80` | `ITE Tech. Inc.$ 2025/03/22$ 14:47:00$ V0.3.2$` | `ITE Tech. Inc.$ 2025/04/15$ 18:20:35$ V0.3.2$` |
| Prodotto | stringa `MTLH-NB06$V0.3.2$` @ `0x1032` | — |
| Core | `ITE EC-V14.6` | `ITE EC-V14.6` |
| 16B-signature `0x40` | presente (variante) | presente |

Byte differenti: 46608/131072 — per lo più codice (banco 0 `0x49E-0x27F2`, `0x2D0B-0x5E78`, banco 1): build diversa (board MTLH-NB06 vs X210AI), nonUGuale ma stessa base V0.3.2.

## Tabelle tastiera: old vs new (allineate agli offset propri)

| Tabella | OLD @ | NEW @ | Diff |
|---|---|---|---|
| set2→set1 (128 B) | `0x0D2C` | `0x0D03` | **0 differenze** |
| matrice (coppie) | `0x2257` | `0x2126` | **0 differenze** (176 B) |
| flag tasti E0 | `0x31BB` | `0x305E` | **0 differenze** (144 B) |
| sequenze multi-byte (Pausa `E1 14 77` ecc.) | `0x272B` | `0x25DC` | **0 differenze** (48 B) |
| rif. registri KBS `0x1D00-0x1D25` nel codice | 14 | 14 | uguali |
| rif. tabella conversione (`MOV DPTR,#base`) | `0x0C46` → `0x0D2C` | `0x0C1D` → `0x0D03` | stessa routine, shift `+0x29` |

## ISO / JIS

- Tasto extra ISO: set-2 `0x61` → set-1 `0x56` in **entrambe** le versioni (verificato byte).
- La tabella set2→set1 copre l'intera gamma `0x00–0x7F` in entrambe; matrice hardware 18×8 = 144 tasti.

**Conclusione: la vecchia versione E03-250322 supportava già ISO e JIS esattamente come la
nuova EC0416** — le tabelle tastiera sono byte-identiche; le differenze tra le due build
riguardano altro codice (configurazione board), non il supporto layout tastiera.
