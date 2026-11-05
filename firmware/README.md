# Firmware EC X210AI

Tutte le versioni del firmware EC, con istruzioni di flash e conferma. Tutti i file sono da 131072 byte (128 KiB). Gli hash completi sono in [`SHA256SUMS`](SHA256SUMS): dalla cartella `firmware/` si controllano con `sha256sum -c SHA256SUMS`.

**Sulla scheda c'è `EC-V0.4.0-all-keys.bin`**. Tasti confermati, ma l'hash del dump dopo il flash non è ancora registrato.

## Versioni

| File | Contenuto | Nome sulla ESP | SHA256 | Stato sulla scheda |
|---|---|---|---|---|
| `patched/EC-V0.4.0-all-keys.bin` | ISO, JIS, scambio Fn↔L-Ctrl, Back, Forward, ThinkVantage, pull-up e fix del rilascio di Fn | `X210ALL.BIN` | `d96e1b3e6a4f` | **Installata**, confermata con `evtest` |
| `patched/EC-V0.4.0-iso-jis-fn-ctrl-swap.bin` | ISO, JIS, scambio Fn↔L-Ctrl | `X210SWAP.BIN` | `a3f1ff4e1bdd` | Funzionante |
| `patched/EC-V0.4.0-iso-jis.bin` | Solo ISO e JIS | `X210KEY.BIN` | `7ee70df08948` | Funzionante |
| `patched/EC-V0.4.0-fn-ctrl-swap.bin` | Solo scambio Fn↔L-Ctrl | `X210FN.BIN` | `e1f1386daef0` | Mai flashata |
| `original/EC-V0.4.0-20250723-lettura1.bin` | Firmware originale della scheda, build `V0.4.0` | `V040.BIN` | `9b8334bd5d59` | Originale, due letture identiche |
| `original/EC0416.BIN` | Build `V0.3.2`, più vecchia della `V0.4.0` | `EC0416.BIN` | `acaf8fed4b79` | Funzionante, tasti ISO assenti |
| `obsolete/EC0416_fn-ctrl-swap.BIN` | Patch errata: cambia Alt+SysRq, non Fn | - | `970431688f10` | **Non flashare** |
| `obsolete/EC0416_ctrl-caps-swap.BIN` | Demo L-Ctrl↔Caps, CRC vecchio | - | `21f63a733dd5` | **Non flashare** |

Le quattro immagini in `patched/` si rigenerano dal dump originale:

```fish
python3 tools/patch_keyboard.py firmware/original/EC-V0.4.0-20250723-lettura1.bin firmware/patched
```

## Cosa cambia in ogni versione

| Funzione | `iso-jis` | `fn-ctrl-swap` | `iso-jis-fn-ctrl-swap` | `all-keys` |
|---|---|---|---|---|
| `<>`, `ù`, tasti JIS | Sì | No | Sì | Sì |
| Scambio Fn↔L-Ctrl | No | Sì | Sì | Sì |
| Back, Forward, ThinkVantage | No | No | No | Sì |
| Pull-up interno di Fn | No | No | No | Sì |
| Fix del rilascio di Fn | No | No | No | Sì |
| Byte modificati, CRC escluso | 7 | 3 | 10 | 98 |
| Codice aggiunto | No | No | No | Sì, 78 byte a `0x5600` |

Senza il fix, nelle combinazioni con Fn va lasciato Fn per ultimo: altrimenti Fn+F2 lascia Win e L premuti.

## Flash

Il flash è sempre un rischio, e la recovery RP2040 non è pronta: se l'EC non riparte, `ifu` non serve più (README §9, §11). Nell'esempio il file è `all-keys`: per un'altra versione usare il suo file, nome e hash dalla tabella.

**1. Da CachyOS**, copia il file e controlla quello di ritorno:

```fish
sudo mkdir -p /boot/efi/EFI/tools
sudo cp usb-tools/ifu.efi /boot/efi/EFI/tools/ifu.efi
sudo cp firmware/patched/EC-V0.4.0-all-keys.bin /boot/efi/EFI/tools/X210ALL.BIN
sudo cp firmware/original/EC-V0.4.0-20250723-lettura1.bin /boot/efi/EFI/tools/V040.BIN
sudo stat -c '%s' /boot/efi/EFI/tools/X210ALL.BIN
sudo sha256sum /boot/efi/EFI/tools/X210ALL.BIN /boot/efi/EFI/tools/V040.BIN
sync
```

La dimensione deve essere `131072` e gli hash devono coincidere con la tabella. Altrimenti non proseguire.

**2. Dalla UEFI Shell**, con alimentatore DC e batteria, da un avvio pulito. Il volume può cambiare: sulla scheda era `fs1:`.

```
fs1:
cd EFI\tools
mm 66 -w 1 -IO -n
```

| Ultima cifra letta | Azione |
|---|---|
| `0`, `4`, `8`, `C` | Prosegui |
| Dispari | Esegui una volta `mm 62 -w 1 -IO -n` e ricontrolla |
| Valore `FF` | Fermati |

Non aggiungere mai un valore dopo l'indirizzo: `mm` scriverebbe sulla porta. Poi:

```
ifu.efi X210ALL.BIN 128
```

Le opzioni di `ifu` distinguono maiuscole e minuscole. Fotografa lo schermo e non spegnere finché c'è avanzamento. Il riavvio finale è brusco ed è normale. `EC ACK Fail` o `Verify Fail` indicano un flash non riuscito: in quel caso non spegnere.

## Conferma

**1. Dump.** Dalla UEFI Shell, nella stessa cartella:

```
ifu.efi /S 128 /k /j
reset -s
```

Da CachyOS l'hash deve coincidere con quello del file flashato:

```fish
sudo sha256sum /boot/efi/EFI/tools/ITEFW.bin
```

**2. Tasti.** La tastiera è `event3` su questa macchina. Con il tasto premuto `value 1`, rilasciato `value 0`, tenuto `value 2`:

```fish
sudo evtest /dev/input/event3 | grep --line-buffered EV_KEY
```

| Tasto | Atteso | Versioni | Confermato |
|---|---|---|---|
| `<>` | `code 86 (KEY_102ND)` | Con ISO/JIS | ISO |
| `ù`, `]` su JIS | `code 43 (KEY_BACKSLASH)` | Con ISO/JIS | ISO, JIS |
| Yen | `code 124 (KEY_YEN)` | Con ISO/JIS | JIS |
| Ro | `code 89 (KEY_RO)` | Con ISO/JIS | JIS |
| Muhenkan | `code 94 (KEY_MUHENKAN)` | Con ISO/JIS | JIS |
| Henkan | `code 92 (KEY_HENKAN)` | Con ISO/JIS | JIS |
| Katakana/Hiragana | `code 93 (KEY_KATAKANAHIRAGANA)` | Con ISO/JIS | JIS |
| Hankaku/Zenkaku | `code 41 (KEY_GRAVE)` | Tutte | JIS |
| Fn fisico | `code 29 (KEY_LEFTCTRL)` | Con scambio | ISO, JIS |
| L-Ctrl fisico | Nessuna riga, fa da Fn | Con scambio | Sì |
| Back | `code 158 (KEY_BACK)` | `all-keys` | ISO, JIS |
| Forward | `code 159 (KEY_FORWARD)` | `all-keys` | ISO, JIS |
| ThinkVantage | `code 183 (KEY_F13)` | `all-keys` | ISO |

`KEY_GRAVE` su Hankaku è corretto: lo interpreta il layout `jp`. F13 si assegna in KDE.

**3. Rilascio di Fn**, solo `all-keys`: premi Fn, poi F2, lascia prima Fn e poi F2. Non deve restare premuto nulla. Confermato sulla scheda.

**Combinazioni con Fn ricavate dal firmware, non ancora provate:**

| Combinazione | Atteso |
|---|---|
| Fn + Freccia su / giù / sinistra / destra | `KEY_STOPCD`, `KEY_PLAYPAUSE`, `KEY_PREVIOUSSONG`, `KEY_NEXTSONG` |
| Fn + F7 | `KEY_LEFTMETA` + `KEY_P` |
| Fn + Spazio | `KEY_LEFTMETA` + `KEY_S` |
| Fn + F4 | `KEY_SLEEP`: può sospendere la macchina |
| Fn + ScrLk | `KEY_NUMLOCK`: premilo due volte, con Num Lock attivo alcune lettere diventano numeri |
| Fn + PrtSc | Alt+SysRq: non aggiungere altri tasti |
| Fn + F3, F5, F8, F9, F12, PgUp, Home, End | Nessuna riga su `event3`: effetto da verificare |

## Tornare indietro

Se l'EC parte ma qualcosa non va, ripeti il controllo della porta e flasha una versione funzionante:

```
ifu.efi X210SWAP.BIN 128
ifu.efi V040.BIN 128
```

Il primo comando torna alla versione senza codice aggiunto, il secondo all'originale. Se l'EC non parte, serve la recovery (README §11).

## Storico dei flash

Tutti eseguiti il 2026-11-05 con `ifu`, dalla ESP.

| Ordine | File | Esito |
|---|---|---|
| 1 | `EC0416.BIN` sopra `V0.4.0` | Riuscito. `ù` ancora assente: la matrice è la stessa |
| 2 | `EC-V0.4.0-iso-jis.bin` | Riuscito. Tastiera ISO funzionante, il CRC ricalcolato non blocca l'avvio |
| 3 | `EC-V0.4.0-iso-jis-fn-ctrl-swap.bin` | Riuscito. Scambio funzionante, quindi linea di Fn e contatto 36 sono collegati |
| 4 | `EC-V0.4.0-all-keys.bin` | Riuscito. Il codice aggiunto parte, tasti confermati su ISO e JIS, rilascio di Fn confermato |

Gli esiti sono riferiti dopo le prove sulla scheda. Nessuno di questi flash ha ancora un dump con hash registrato.
