# 10 — Guida dump/flash hardware: XGecu T48 e CH341A (± mod 3.3V)

## Cosa c'è sulla scheda

- **Flash BIOS**: chip SPI SOIC-8 separato (dump di riferimento `bios_backup.rom` =
  12 MiB). Chip supportati (da `inputs/bios/extracted/fparts.txt`): W25Q128/W25Q64,
  MX25L12873, N25Q128, EN25QH128, IS25LP128, GD25B128… — **leggere il marking sul chip**
  e scegliere il profilo giusto. Alimentazione 3.3V.
- **EC IT5571E/VG-128**: eFlash **embedded da 128 KiB dentro il chip** — non c'è un chip
  flash dell'EC da clip▒▒are. Il dump dell'EC si fa via software interno
  (`fpt.efi -d` / `flashrom -p internal` / `ifu.efi`, vedi doc 04) oppure via ISP sul
  connettore KBS (adattatore parallelo, datasheet §7.24.3.1). Un programmatore esterno
  serve solo per la flash BIOS (o se la scheda espone i pin FSPI dell'EC su test-point).

## Regola d'oro sulla tensione

Le flash sono **3.3V**. Il CH341A (PCB nero) di default esce a **5V** sui segnali:
senza mod rischia di bruciare il chip. Il T48 (XGecu) seleziona la tensione via software
(3.3V/5V/1.8V) → **nessuna mod necessaria**.

### CH341A senza mod 3.3V

- Usalo **solo** con chip 5V-tolerant (rari) o tramite adattatore/livello 3.3V
  (es. bus-pirate/level shifter sulle linee dati). Su flash 3.3V standard è a rischio.
- Comandi (flashrom): `sudo flashrom -p ch341a_spi -r bios_dump.bin` (lettura),
  `sudo flashrom -p ch341a_spi -w bios.bin` (scrittura), `-v` verifica,
  `sudo flashrom -p ch341a_spi` (rileva chip, legge RDID).

### CH341A con mod 3.3V

- Mod classica: aprire il case, **tagliare la pista / dissaldare il regolatore 5V**
  (78L05) e alimentare VCC con i **3.3V** del proprio pin 3.3V (presente sulla scheda
  dopo la mod) — dopo la mod VCC, MOSI, MISO, SCK, CS sono tutti a 3.3V.
- Dopo la mod è sicuro su tutte le flash 3.3V di fparts.txt. Stessi comandi flashrom sopra.

### XGecu T48

- Software: app XGecu/MiniPro (selezionare chip, VCC=3.3V) oppure flashrom se il build lo
  supporta: `flashrom -L | grep -i t48` → es. `sudo flashrom -p xgecu-t48-spi -r bios_dump.bin`.
- Vantaggi: selezione tensione per chip, test ID, verify integrato. Nessuna mod.

## Procedura operativa (BIOS flash)

1. **Backup**: dump 2 volte (`bios_dump1.bin`, `bios_dump2.bin`), confrontare
   (`cmp` / sha256) — devono essere identici.
2. Verifica chip: `flashrom -p <prog>` mostra nome e size; annota il marking reale.
3. Se protetta (WP#/status register): sbloccare prima (`flashrom --wp-disable` /
   `wp-list`), altrimenti write fallisce.
4. Scrittura: `flashrom -p <prog> -w nuovo.bin` poi `-v` (verify). Non interrompere.
5. Dump di verifica post-write e confronto hash.

## Dump dell'EC (128 KiB embedded)

- **Software interno** (consigliato): UEFI Shell → `fpt.efi -d full.bin` (tutta la SPI)
  oppure `flashrom -p internal -r full.bin` da Linux; l'EC si legge via il suo canale
  (`ifu.efi` per read/write EC, vedi doc 04). Hash atteso EC0416: sha256 `acaf8fed…`.
- **ISP via KBS** (a macchina spenta): adattatore parallelo DB25 sul connettore tastiera
  (pinout datasheet §7.24.3.1: KSO0-7=PD0-7, KSO8=ACK#, KSO9=BUSY, KSO10=PE, KSO12=SLCT,
  KSI0=STB#) + tool ITE → dump/flash eFlash EC. Utile per recovery se l'EC non parte.
- **Programmatore esterno sull'EC**: possibile solo se la scheda espone FSPI
  (FSCK/FSCE#/FMOSI/FMISO + VFSPI) su connettore/test-point; altrimenti l'eFlash
  embedded non è raggiungibile con clip.

## Sicurezza

- Solo 3.3V (T48 in sw, o CH341A moddata). Mai 5V su flash 3.3V.
- Macchina spenta e scollegata; clip anti-static; non muovere i cavi durante read/write.
- Tenere sempre il dump originale (es. `bios_backup.rom`, `EC0416.BIN`) per il rollback.
- Prima di scrivere: dump di backup + verifica che il file .bin abbia la size giusta
  (EC = 131072 byte) e la 16B-signature a `0x40` intatta (doc 02).
