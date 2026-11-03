# X210AI — ITE IT5571 EC firmware analysis

Analisi del firmware EC di una scheda X210AI equipaggiata con **ITE IT5571 (rev. 2)**,
versione **IT5571E/VG-128** (eFlash embedded da 128 KiB), core **8051**.

## Layout della cartella

I prodotti del lavoro (analysis, tools, dumps, refs) rispecchiano il contenuto dei repo
remoti privati (`marcocancarini/x210ai-ec` su GitHub e Codeberg). I materiali originali
(datasheet, pacchetto BIOS) stanno in `inputs/`.

```
x210ai-EC/
├── README.md                  # questo file
├── analysis/                  # documenti dell'analisi
│   ├── 01-overview.md         #   identificazione, architettura, mappa memoria
│   ├── 02-signature-checksum.md  # firme/checksum (16B-signature, nessuna firma crypto)
│   ├── 03-keyboard-ps2.md     #   tastiera PS/2: KBS, KBC, conversione set2→set1
│   ├── 04-dump-and-flash.md   #   procedure dump/flash (UEFI/ifu.efi/fpt.efi/flashrom/ISP/SPI)
│   ├── 05-patch-guide.md      #   guida patch rimappatura tasti (demo Fn/Ctrl) + ISO/JIS
│   ├── 06-version-compare.md  #   confronto EC vecchio E03-250322 vs EC0416 (ISO/JIS identici)
│   ├── 07-iso-keys-old-vs-new.md # perché i tasti ISO non passavano nella vecchia EC
│   └── 08-fn-ctrl-swap.md     # swap Fn↔Ctrl: non è del BIOS, va patchato l'EC (pin Fn/matrice)
├── tools/
│   ├── i8051.py               # disassembler 8051 minimale (nessuna dipendenza)
│   └── output/                # artefatti generati
│       ├── strings.txt        #   dump stringhe con offset
│       └── key-regions.asm    #   disassembly delle regioni chiave
├── dumps/
│   ├── EC0416.BIN             # dump EC 128 KiB (originale)
│   └── EC0416_ctrl-caps-swap.BIN  # demo patch: swap L-Ctrl↔CapsLock (2 byte a 0x0D17/0x0D5B)
├── refs/
│   └── DATASHEETS.md          # sezioni datasheet usate + hash dei materiali
└── inputs/                    # materiali originali (non prodotti da noi)
    ├── bios/
    │   ├── X210AI0724BIOS.zip
    │   └── extracted/         # Fpt.efi, fb.nsh, fparts.txt, UEFI环境/, tutorial docx
    └── datasheets/
        ├── IT5571E-128.pdf
        └── IT5570_A_V0.3.1_U.pdf
```

## Hash del dump EC (`dumps/EC0416.BIN`)

- MD5:    `7392fa5138c906ac17c7049fa69514e7`
- SHA256: `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca`

## Sommario

Firmware EC ITE, build `V0.3.2` del 2025-04-15 18:20:35, core `ITE EC-V14.6`.
Nessuna firma crittografica interna: l'unico "signature" è la **16B-signature di power-on**
a `0x0040` (datasheet §6.4.3.11.1), un marcatore di code base, non un controllo di integrità.
Patchare il binario è possibile mantenendo dimensione (128 KiB), la 16B-signature e il
layout a banchi da 32 KiB.

## Uso rapido del disassembler

```
python3 tools/i8051.py dumps/EC0416.BIN 0 <start_hex> <end_hex>
```
