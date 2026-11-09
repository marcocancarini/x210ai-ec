# Parte 1: Studio del dump e del firmware

Cosa c'è nel firmware EC e nei dump: file, architettura, firme, tastiera e differenze tra le build. Il BIOS è letto ma non ancora analizzato ([1.1](#11-file-e-hash)). La ventola ha una parte propria ([parte 3](3-curve-ventola.md)).

## 1.1 File e hash

| File | SHA256 | Note |
|---|---|---|
| `dumps/ec/EC-V0.4.0-20250723-lettura1.bin`, `-lettura2.bin` | `9b8334bd5d5986ce97dfc5d8503fa643a97d8abb6c6166ce181c0525ec722311` | **Firmware originale della scheda**, letto il 2026-11-04. 131072 B, build `V0.4.0` 2025-07-23 18:11:04. Due letture identiche. Base delle patch e file di ritorno |
| `firmware/patched/EC-V0.4.0-all-keys.bin` | `d96e1b3e6a4f0fd1a3ea288b234afae3ad41dcb460b40419300df3ea40005894` | ISO, JIS, scambio Fn↔LCtrl, Back, Forward, ThinkVantage, pull-up e rilascio di Fn (98 byte + CRC). **Installata sulla scheda**, tasti ISO e JIS e rilascio di Fn confermati |
| `firmware/patched/EC-V0.4.0-iso-jis.bin` | `7ee70df0894832da7ed47dab8e2fda7674ea505c643ffb4b75d113f491471a74` | `V0.4.0` con tasti ISO e JIS (7 byte + CRC). ISO confermata, JIS confermata su `all-keys` con le stesse celle. File di ritorno |
| `firmware/patched/EC-V0.4.0-fn-ctrl-swap.bin` | `e1f1386daef06d7b51c5d65d8c1fc4764be7b33173d82a192db95b68f15be07f` | `V0.4.0` con scambio Fn↔LCtrl (3 byte + CRC), mai provata |
| `firmware/patched/EC-V0.4.0-iso-jis-fn-ctrl-swap.bin` | `a3f1ff4e1bdd374692f2854a7a8be4a48375938c5959f3e4643539e88675d57f` | ISO/JIS e scambio (10 byte + CRC). ISO e scambio confermati, JIS confermata su `all-keys` con le stesse celle. File di ritorno |
| `firmware/vendor/EC0416.BIN` | `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca` | Installata il 2026-11-05 e poi sostituita, più vecchia della `V0.4.0` originale. 131072 B, build `V0.3.2` 2025-04-15 18:20:35, md5 `7392fa5138c906ac17c7049fa69514e7` |
| `firmware/obsolete/EC0416_ctrl-caps-swap.BIN` | `21f63a733dd5ee8b338ffefcda093ffec8d38c38138bc97c1e82a65a20acd406` | Patch demo L-Ctrl↔CapsLock (2 byte). **CRC non aggiornato, non flashare** |
| `firmware/obsolete/EC0416_fn-ctrl-swap.BIN` | `970431688f10aa160973d3f276c453e5cc86427a28a01ee34ef43ea17dfabee8` | **Errata, non usare:** cambia Alt+SysRq, non Fn, e ha il CRC vecchio ([1.3](#13-firme-e-checksum), [2.1](2-modifiche-software.md#21-patch-della-tastiera)) |
| `inputs/ec/MTLH-NB06-ec-250322/MTLH-NB06_E03-250322.BIN` | `151edd7a59cad1eb4a3d7b0827ee0937f73f0645a3cbf8d532f5e6bc0de5bbde` | EC vecchia, build 2025-03-22, md5 `4bbc1e54aad8cac51a3e0a5e5274ed28` |
| `inputs/ec/X210AI-EC-updated-on-03-22.zip` | `b850c8941df6eecbea035aefe481eb1c50fe8d5da4ea9b333717fc7a7230bc4e` | Archivio originale di `MTLH-NB06-ec-250322/`. Non nella repo: contiene `ifu.efi` |
| `inputs/bios/X210AI0724BIOS.rar` | `a1090b7986e6e3cb2485333f73fd5f8d62822f64bedfe7cad5733e88ddd94663` | Solo strumenti, estratti in `inputs/bios/extracted/`. **Nessuna immagine BIOS**. Non nella repo: contiene `Fpt.efi` |
| `inputs/datasheets/IT5571E-128.pdf` | `a4e4afae8a157b7424401cf65c9dbecddce937b8b88a3dc1474124439bfc5753` | Datasheet sintetico, 29 pagine |
| `inputs/datasheets/IT5570_A_V0.3.1_U.pdf` | `01666ebe44ece4a436b5ffaad40c9570c17f0b3480862caf224953585c59102f` | IT5570 V0.3.1, parente stretto dell'IT5571 |

Sezioni del datasheet usate: `refs/DATASHEETS.md`.

I percorsi `inputs/` restano come riferimento agli hash: quasi tutti quei file ora sono in `storico/`.

**Immagine BIOS.** `fb.nsh` chiama `MTLH-NB06_B0.2.bin`, che non è incluso nel pacchetto. In `dumps/bios/` ci sono due letture: 32 MiB, identici (SHA256 `dd6e311622b8c61fe8c51de8fef8f3ff28b625dffc5097836f12f5cd5b884669`), con flash descriptor a `0x10` e volumi `_FVH`. Sono solo in locale, non nella repo, perché contengono dati della macchina, e non sono stati analizzati a fondo.

| File del pacchetto | Ruolo | Note |
|---|---|---|
| `inputs/bios/extracted/uefi-shell/EFI/BOOT/BOOTX64.efi`, `BOOTIA32.efi` | UEFI Shell, build 2013 | Non scrive nulla: è l'ambiente da cui lanciare i tool, da copiare in radice sulla chiavetta |
| `inputs/ec/MTLH-NB06-ec-250322/ifu.efi` | ITE Flash Utility 2.3.1a, build DEBUG | Legge e scrive l'EC. Presente solo nel pacchetto EC. Proprietario, non nella repo ([dove trovarlo](../usb-tools/README.md)) |
| `inputs/bios/extracted/Fpt.efi` + `fb.nsh` | Intel Flash Programming Tool | Legge e scrive il chip SPI del BIOS. Proprietario, non nella repo ([dove trovarlo](../usb-tools/README.md)) |
| `inputs/bios/extracted/fparts.txt` | Lista di 204 flash SPI | Le voci non sono validate, lo dice il file stesso |
| Tutorial `.docx` nel pacchetto BIOS | Guida generica con esempi di un altro modello (R51) | Non tratta backup, alimentazione, errori o recovery |

## 1.2 Architettura e mappa memoria

- CPU **8051**; vettore reset `0x0000` → `LJMP 0x0070` (init: SP=0xC0, FPCFG `0x1001=0x3F`, copia tabelle XRAM, main `0x0400`). Vettori standard `0x03/0x0B/0x13/0x1B/0x23/0x2B`; interrupt estesi ITE: stub `LJMP 0x28xx` → dispatcher `0x2800`; trampoline `0x2B6B-0x2BE0` (`MOV DPTR,#handler; AJMP 0x2800`).
- **4 banchi × 32 KiB**, finestra commutabile `0x8000-0xFFFF` (Bank base xdata `0x1300h`; FLHCTRL2R `0x1032` scritto a `0x251E`). Banco0 `0x0000-0x54D4` (fisso) + firma testuale `0x7F80`; banco1 `0x8000-0xF8A4`; banco2 `0x10000-0x15515`; banco3 `0x18000-0x18132` (stub bank-switch); resto `0xFF`.
- Base registri (datasheet, sezione 3.2): SMFI `0x1000h` (FLHCTRL1R `0x1031`, ECINDAR `0x103B-0x103F`, protect P0BA `0x104F+`), INTC `0x1100h`, EC2I `0x1200h`, **Bank `0x1300h`**, Common `0x1400h`, PMC `0x1500h`, GPIO `0x1600h`, PS/2 `0x1700h`, WUC `0x1B00h`, KBS `0x1D00h`, BRAM `0x2200h`.
- KBC host = xdata `0x004B/0x004C` (porte `0x64/0x60`); PD/UCSI in banco0 `0x3400-0x4300` (USB-C PD, controller esterno Analogix).

## 1.3 Firme e checksum

- **Nessuna firma crittografica trovata**: niente costanti SHA/RSA/MD5, blocco `0x7F80` solo testo e non referenziato, reset `0x0070` non verifica la flash, e il firmware non legge da codice la zona `0x40-0x4F`.
- **16B-signature a `0x40`** (`A5…A4 95 85 12 26 E6 AA 00 55 55`): marcatore di power-on per localizzare la code base (datasheet, sezione 6.4.3.11.1, formato "implicit" → base `0x000000`). **Va preservata nelle patch** (offset validi `0x40-0xF0`).
- **CRC a `0x4A-0x4B`:** è un **CRC-16/CMS** big endian (polinomio `0x8005`, init `0xFFFF`, senza riflessione, senza XOR finale) su tutti i 128 KiB esclusi i 16 byte della firma `0x40-0x4F`. Trovato provando tutti i 65536 polinomi su 12 intervalli: è l'unico risultato e torna esattamente sulle tre build ufficiali (`F9 0C` del 22 marzo, `26 E6` di `EC0416`, `AF 5B` della `V0.4.0`). Va **ricalcolato dopo ogni modifica**: `tools/patch_keyboard.py` lo fa, e `--check` verifica un'immagine.
- **Chi controlla il CRC:** non è noto. Il firmware non lo legge, quindi può essere la boot ROM o nessuno. Datasheet e System76 hanno `5A 5A` fissi, e System76 avvia su IT5570: forse è un valore che salta il controllo, ma non è verificato. Un CRC corretto è comunque la scelta prudente.
- Protezione in scrittura: il firmware non scrive i registri P0BA-P3ZR.

## 1.4 Tastiera, ISO e JIS

- **KBS matrix 18×8** (base `0x1D00h`: KSOL/KSOH1/KSOCTRL/KSOH2/KSI@`0x1D04`/KSOxLSDR `0x1D10-0x1D21`). Driver in banco1 `0x9300-0x9F00`: loop 16 righe KSO, legge KSI, indice `0x4D=(col<<4)|row|0x08`.
- **Tabella matrice `0x2EB9`:** 128 byte, indice `(KSI<<4)|KSO` (`0x8CB2`). Identica in `EC0416` e `V0.4.0`. La tabella `0x2F39` (24 byte, 2 KSO extra) è vuota. Le voci sono codici interni, non scancode (vedi sotto).
- **Codici interni** (`0x8D77`): `<0x80` set 2 diretto; `0x80-0x9B` tabella `0x3060` (`0x82` LWin, `0x84` Menu, `0x88` LShift, `0x89` RShift, `0x8A` LAlt, `0x8B` RAlt, `0x8C` LCtrl, `0x8D` RCtrl, `0x8E` Fn); `0x9C-0xDF` varianti a `0x2FE3`; `≥0xE0` coppie normale/Fn a `0x3046`.
- **Fn:** non è in matrice. È il pin `0x1608` bit 7 (attivo basso, `0xC447`), con debounce nella voce 4 della tabella `0x2795`. Pressione e rilascio chiamano `0x8D77` con `0x8E` (`0xC45E`, `0xC465`), che imposta il bit `0x40` dello stato tastiera in iRAM `0xBC`. Quel pin non viene letto altrove. È GPH7 (piedino 3): `GPCRH7` `0x164F` vale `0x80`, cioè ingresso **senza pull-up interno**. La linea va solo a massa, quindi senza una resistenza sulla scheda resta flottante. Il debounce vale 6 letture uguali.
- **Conversione scancode**: routine `0x0C09` (F0→break marker 0xFF, bit E7→casi speciali `0x83→0x41`/`0x84→0x54`, break `\|0x80`) e tabella **set2→set1 `0x0D03`** (128 B). Qui `0x83` e `0x84` sono byte set 2 già in uscita: F7 e Alt+SysRq. Sequenze multi-byte (Pausa `E1 14 77`): `0x25B2`; comandi PS/2: `0x2636`.
- KBC 8042 (IRQ1/IRQ12, A20G): init `0x0A76`, dispatcher eventi `0x0D9C` (flag bit `0x30-0x3D`).
- Flusso: KBS scan → tabella matrice → scancode set2 → conversione set1 → buffer KBC → porta `0x60` + IRQ1.
- **ISO/JIS:** la tabella `0x0D03` copre tutti i set-2 necessari, ma **la matrice no**: le celle dei tasti ISO e JIS sono a `0x00`, e `0x8D77` scarta quel codice. Da qui il sintomo di `ù` e `<>` che non arrivano all'OS, in tutte le build viste.
- **Confronto con ThinkPad:** la matrice coincide, trasposta, con la X220 di [thinkpad-ec](https://github.com/hamishcoleman/thinkpad-ec/blob/master/docs/table_matrix.txt): 88 celle occupate in comune e 52 tasti di scrittura su 52 con il codice atteso. Lì i codici sono numeri di tasto IBM, quindi quelli "sconosciuti" sono 14 Yen, 131 Muhenkan, 132 Henkan e 133 Kana. Differenze: LWin sta in `KSI2/KSO11` invece di `KSI3/KSO9`, e il firmware originale non ha ThinkVantage, Mic e PgBk/PgFd. La patch `all-keys` aggiunge tutti questi tasti tranne Mic ([2.1](2-modifiche-software.md#21-patch-della-tastiera)).
- **Confronto con X20x JIS:** l'adattatore [bulat-chu](https://github.com/bulat-chu/Thinkpad-X6x-X20x-keyboard-USB-Adapter) documenta la matrice reale di una tastiera X6x/X20x giapponese. Convertita con il suo `pinout.txt` e con `matrix_pins`, dà 49 tasti su 49 uguali al firmware e conferma Yen, Ro, Muhenkan, Henkan, Kana e la cella `KSI6/KSO7`, che lì è `]` e su ISO è `#`. Anche LWin in `KSI2/KSO11` coincide con il suo `table-main.txt`, che ha però L_Shift e R_Shift scambiati rispetto al suo `keymap.c`. La cella ISO `<>` (`KSI5/KSO1`) non esiste su una tastiera JIS: viene solo dalla X220, ma è libera.
- **Rilascio di Fn:** la routine `0x8CFA` riceve l'evento, lo salva in `0x080E` e non lo usa: sceglie la variante Fn guardando Fn al momento del rilascio. Rilasciare Fn prima del tasto, o premerlo dopo, manda il rilascio di un altro tasto: Fn+F2 emette `E0 1F 4B` (Win+L) e poi `F0 06`, lasciando Win e L premuti. Vale per 18 tasti ed è nel firmware originale. La mappa XRAM `0x00E0-0x00EF` letta da `0x8CFA` viene solo azzerata.
- **Tasti rilevati e scartati:** la scansione legge qualsiasi incrocio KSO/KSI, ma un codice `0x00` si ferma in `0x8E41` (`JZ` a `0x8E51`) e non arriva al KBC. Valeva anche per ThinkVantage (`KSI5/KSO10`) e Back/Forward (`KSI6/KSO11`, `KSI7/KSO11`). Dedotto dal codice e confermato con `evtest`: gli stessi tasti arrivano a Linux una volta scritte le celle ([2.4](2-modifiche-software.md#24-scrittura-dellec-con-ifu-rischi)).

## 1.5 Confronto tra V0.4.0 e EC0416

Gli indirizzi di questa sezione e dell'analisi di `ifu` ([2.4](2-modifiche-software.md#24-scrittura-dellec-con-ifu-rischi)) si riferiscono a `EC0416`, salvo dove indicato. Il flash viene eseguito dal firmware **in esecuzione**: quello di `EC0416` è stato fatto dalla `V0.4.0`, il secondo da `EC0416`, i successivi dalle immagini patchate. Il ciclo di flash è identico nelle due build (tabella sotto). `EC0416` è più vecchia di tre mesi: flasharla è un **downgrade**, non un aggiornamento.

| Punto | Esito del confronto statico |
|---|---|
| Ciclo di flash | Banco 1 identico da `0x8000` a `0x884B` |
| Ingresso `0xDC` | Stessa catena e stessi byte, tranne gli indirizzi rilocati (`0xDC94` → `0xDC5E`) |
| Variante PMC2 e uscita `0xFC`/`0xFE` | Uguali salvo rilocazione (`0xD9D3` → `0xD99D`, `0xDAB3` → `0xDA7D`) |
| Protezioni e watchdog | Stessi registri in `0x1000-0x10FF` e `0x1E00-0x1FFF`: nessuna nuova protezione rilevata |
| Pin | Tabella GPIO da 103 voci identica, spostata di `+0x1D` (`0x2660-0x2794` nella `V0.4.0`) |
| Comandi host | Stessi casi nello switch PMC2 (`0xF61E`, ora `0xF5F0`) |
| Spazio EC | Stessi 141 indirizzi in `0x0400-0x05FF` |
| Vettori e avvio | Reset uguale. Differiscono solo tre byte di indirizzo in `0x70-0x3FF` e `0x4A-0x4B` (`AF 5B`, vedi [1.3](#13-firme-e-checksum)) |
| Tastiera | Tabelle `0x0D03` e `0x2EB9` e routine `0x0C09` identiche e agli stessi indirizzi |

**Cosa cambia davvero.** Il confronto istruzione per istruzione, con gli indirizzi mascherati, dà 1542 blocchi diversi: 1181 sono solo rilocazioni, 361 sono strutturali, in parte dovuti al disassemblaggio lineare delle tabelle. Molte variabili XRAM sono spostate, per esempio di `-0x28` da `0x0823`.

- Driver SMBus/I2C `0x1E00-0x2300` riscritto: `EC0416` usa i registri `0x1CB0-0x1CBA` in modo fisso, la `V0.4.0` passa da una tabella per canale (voci da 21 byte).
- Logica cambiata in più punti dei banchi 1 e 2, per esempio contatori `0x001D/0x001E` rimossi, condizione su `0x00B0` sostituita da `0xCE90`, costanti `0x32→0x26` (`0xDD83`) e `0x03→0x04` (`0xED71`).
- **Il significato di queste modifiche non è stato decodificato:** non si sa cosa corregga la `V0.4.0`, né se il downgrade tocca ricarica, USB-C PD, ventola o accensione.

**Conclusione.** Il confronto non mostra incompatibilità di pin o interfaccia e il percorso di `ifu` non cambia. Restano valide tutte le debolezze di [2.4](2-modifiche-software.md#24-scrittura-dellec-con-ifu-rischi) e la recovery non è provata.

Attenzione ai nomi: entrambe le build si dichiarano `V0.3.2`, pur differendo per 46.608 byte. Solo la vecchia contiene `MTLH-NB06`. Per distinguerle usare data o sha256.
