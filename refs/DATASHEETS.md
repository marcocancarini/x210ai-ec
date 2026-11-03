# Riferimenti datasheet e file sorgente dell'analisi

## File di riferimento (locali, non versionati — hash per tracciabilità)

| File | SHA256 | Note |
|---|---|---|
| `EC0416.BIN` | `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca` | dump EC 128 KiB (versionato in `dumps/`) |
| `IT5571E-128.pdf` (29 pag.) | `a4e4afae8a157b7424401cf65c9dbecddce937b8b88a3dc1474124439bfc5753` | datasheet sintetico IT5571E-128 (features: 8051, eSPI MAFS, LPC, KBC 8042, PS/2 ×2, KBS 18×8, ISP via KBS/parallel port, 128K eFlash) |
| `IT5570_A_V0.3.1_U.pdf` | `01666ebe44ece4a436b5ffaad40c9570c17f0b3480862caf224953585c59102f` | datasheet IT5570 A-version V0.3.1 (archive.org) — parente stretto di IT5571 (chip ID 0x5571 ≈ IT8571) |
| `X210AI0724BIOS.zip` | `2abe4276145b40d0e998d948e04223742b9efd05e434ef7d65fd56aab45e4d32` | pacchetto BIOS+tool: `Fpt.efi`, `fb.nsh`, UEFI shell, tutorial docx (`ifu.efi xx.bin 128` per EC) |

## Sezioni datasheet usate (IT5570 V0.3.1)

- §3.2 memory map: SMFI `0x1000h`, INTC `0x1100h`, EC2I `0x1200h`, **Bank `0x1300h`**, Common `0x1400h`, double-map `0x8000h`
- §6.4.3.11.1 **16B-signature** (power-on EC code base locator) — pattern `A5…95 85 12 … 55 55` a offset `0x40–0xF0`
- §6.4.4 Table 6-29 EC view SMFI: FLHCTRL1R `0x1031`, FLHCTRL2R `0x1032`, ECINDAR `0x103B-0x103F`, **P0BA0R/P0BA1R `0x104F/0x1050`** (protect range)
- §6.6 KBC: legacy `0x60/0x64`, IRQ1/IRQ12, A20G; Table 6-34 EC view: KBHICR `+00h`, KBIRQR `+02h`, KBHISR `+04h`, KBHIKDOR `+06h`, KBHIMDOR `+08h`, KBHIDIR `+0Ah`
- §7.4 Keyboard Matrix Scan: base **`0x1D00h`** (KSOL/KSOH1/KSOCTRL/KSOH2/KSIR/KSICTRLR/KSIG*/KSOxLSDR), matrice 18×8
- §7.5 GPIO base `0x1600h`; PMC base `0x1500h`
- §7.24.3.1 **ISP via parallel port su connettore KBS** (DB25: KSO0-7=PD0-7, KSO8=ACK#, KSO9=BUSY, KSO10=PE, KSO12=SLCT, KSI0=STB#)
- eSPI MAFS/SAFS: flash condivisa host↔EC, code-fetch switch via FLHCTRL5R
