# Riferimenti datasheet e file sorgente dell'analisi

## File di riferimento (hash per tracciabilità)

| File | SHA256 | Note |
|---|---|---|
| `firmware/vendor/EC0416.BIN` | `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca` | dump EC 128 KiB (nella repo) |
| `inputs/datasheets/IT5571E-128.pdf` (29 pag.) | `a4e4afae8a157b7424401cf65c9dbecddce937b8b88a3dc1474124439bfc5753` | datasheet sintetico IT5571E-128 (features: 8051, eSPI MAFS, LPC, KBC 8042, PS/2 ×2, KBS 18×8, ISP via KBS/parallel port, 128K eFlash) |
| `inputs/datasheets/IT5570_A_V0.3.1_U.pdf` | `01666ebe44ece4a436b5ffaad40c9570c17f0b3480862caf224953585c59102f` | datasheet IT5570 A-version V0.3.1 (archive.org) — parente stretto di IT5571 (chip ID 0x5571 ≈ IT8571) |
| `inputs/bios/X210AI0724BIOS.rar` | `a1090b7986e6e3cb2485333f73fd5f8d62822f64bedfe7cad5733e88ddd94663` | pacchetto strumenti, estratto in `inputs/bios/extracted/`: `Fpt.efi`, `fparts.txt`, `fb.nsh`, `uefi-shell/`, tutorial docx (`ifu.efi xx.bin 128` per EC). Nessuna immagine BIOS |

## Sezioni datasheet usate (IT5570 V0.3.1)

Le pagine citate sono in [`datasheet/`](datasheet/README.md) come immagini. Il PDF completo non è nella repo.

- §3.2 memory map: SMFI `0x1000h`, INTC `0x1100h`, EC2I `0x1200h`, **Bank `0x1300h`**, Common `0x1400h`, double-map `0x8000h`
- §6.4.3.11.1 **16B-signature** (power-on EC code base locator) — pattern `A5…95 85 12 … 55 55` a offset `0x40–0xF0`
- §6.4.4 Table 6-29 EC view SMFI: FLHCTRL1R `0x1031`, FLHCTRL2R `0x1032`, ECINDAR `0x103B-0x103F`, **P0BA0R/P0BA1R `0x104F/0x1050`** (protect range)
- §6.6 KBC: legacy `0x60/0x64`, IRQ1/IRQ12, A20G; Table 6-34 EC view: KBHICR `+00h`, KBIRQR `+02h`, KBHISR `+04h`, KBHIKDOR `+06h`, KBHIMDOR `+08h`, KBHIDIR `+0Ah`
- §7.4 Keyboard Matrix Scan: base **`0x1D00h`** (KSOL/KSOH1/KSOCTRL/KSOH2/KSIR/KSICTRLR/KSIG*/KSOxLSDR), matrice 18×8
- §7.5 GPIO base `0x1600h`; PMC base `0x1500h`
- §7.24.3.1 **ISP via parallel port su connettore KBS** (DB25: KSO0-7=PD0-7, KSO8=ACK#, KSO9=BUSY, KSO10=PE, KSO12=SLCT, KSI0=STB#)
- Table 5-19 piedini Parallel Port: PD[7:0] 36-43, ACK# 44, BUSY 45, PE 46, ERR# 51, SLCT 52, STB# 58, AFD# 59, INIT# 60, SLIN# 61; KSI4/KSI5 62/63
- eSPI MAFS/SAFS: flash condivisa host↔EC, code-fetch switch via FLHCTRL5R
- §7.23 **DBGR**: ISP e debug via DBGR/EPP o DBGR/SMB; §7.23.3.2 DBGR/SMB attivabile a caldo, uscita solo con reset
- §7.4.4.6 **KSICTRLR** `0x1D05`: bit 4 OVRPPK disabilita DBGR/EPP; §7.7.4.26 **SLVISELR** `0x1C34`: bit 4 OVRSMDBG disabilita DBGR/SMB
- Table 5-21 strap: `KSI[5,4,2,1]=0011b` = ingresso DBGR/EPP; `FSCK, GPG6, FMISO, FMOSI, FSCE#, GPG2` = ingresso test mode
- Table 5-20 GPG2 (pull-up se FSPI è in uso); §6.4.4.51-52 FLHCTRL5R/6R (sorgente del fetch)
- Table 5-5 FSPI, Table 5-6 SSPI, Table 4-1 piedini LQFP-128, §7.21.5 SSPI base `0x2600h`, §7.5.3.28 GPCRn (`GPMD`: 00 alternate, 01 output, 10 input)
- LQFP 128 Outline Dimensions: corpo 14×14 mm, passo 0,40 mm, ingombro 16×16 mm

## Immagini della scheda (`refs/img/`)

- `ec-connettore-tastiera.png`: EC e connettore tastiera BTB a 40 contatti (foto ridotta, 2000×1506)
- `it5571-pinout-lqfp128.png`: pagina 9 di `IT5571E-128.pdf`, piedini LQFP-128 vista dall'alto (il documento è intestato IT5570E)
- `ec-spi1-pinout.png`: pinout parziale annotato, ricavato da `refs/photos/PXL_20261104_101131198.MP.jpg`
- `refs/photos/PXL_20261104_101131198.MP.jpg`, `refs/photos/PXL_20261104_101145837.jpg`: foto originali di connettore EC_SPI1 ed EC, usate per passo e piste
- `refs/photos/PXL_20261104_104321709.MP_preview.jpeg`: misura col calibro della fila di terminali, 5,08 mm (display capovolto)
- `ec-spi1-connettore.png`: connettore EC_SPI1 sopra il chip ITE LQFP
- `scheda-porte-debug.png`: schema porte del produttore (debug port 10, 12, 20)
- `ec-spi1-assemblato.png`: connettore su scheda assemblata nel telaio
- `ec-spi1-contatti.png`: ingrandimento dei terminali usato per stimare numero di contatti e passo

## Riferimenti esterni

- Tastiera ThinkPad X201: https://github.com/bulat-chu/Thinkpad-X6x-X20x-keyboard-USB-Adapter (`Scheme-PCB/Green/Thinkpad_X201_kbd_USB-C-Scheme.pdf`, connettore J6 `AA01B-S040VA1`)
