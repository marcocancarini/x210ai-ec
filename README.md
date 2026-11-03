# X210AI — ITE IT5571 EC firmware analysis

Analisi del firmware EC di una scheda X210AI equipaggiata con **ITE IT5571 (rev. 2)**,
versione **IT5571E/VG-128** (eFlash embedded da 128 KiB), core **8051**.

## Contenuti

- `dumps/EC0416.BIN` — dump EC da 128 KiB (131072 byte)
- `analysis/01-overview.md` — identificazione, architettura, mappa memoria
- `analysis/02-signature-checksum.md` — verifica firme/checksum (16B-signature, assenza di firma crypto)
- `analysis/03-keyboard-ps2.md` — sottosistema tastiera PS/2 (KBS matrix, KBC, conversione scancode)
- `analysis/04-dump-and-flash.md` — procedure di dump/flash: software interno (UEFI/ifu.efi/fpt.efi/flashrom/ISP) ed esterno (SPI/ISP via KBS)
- `tools/i8051.py` — disassembler 8051 minimale (nessuna dipendenza)
- `tools/strings.txt` — dump stringhe con offset
- `refs/DATASHEETS.md` — riferimenti datasheet e hash dei file di riferimento

## Hash del dump EC

- MD5:    `7392fa5138c906ac17c7049fa69514e7`
- SHA256: `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca`

## Sommario executable

Firmware EC ITE, build `V0.3.2` del 2025-04-15 18:20:35, core `ITE EC-V14.6`.
Nessuna firma crittografica interna: l'unico "signature" è la **16B-signature di power-on**
a `0x0040` (IT5570/IT5571 datasheet §6.4.3.11.1), un marcatore per localizzare la code base,
non un controllo di integrità. Patchare il binario è possibile mantenendo dimensione (128 KiB),
la 16B-signature e il layout a banchi da 32 KiB.
