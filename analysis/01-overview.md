# 01 — Panoramica del firmware EC0416.BIN

## Identificazione

| Campo | Valore |
|---|---|
| File | `EC0416.BIN`, 131072 byte (128 KiB) = eFlash embedded IT5571E/VG-128 |
| MD5 | `7392fa5138c906ac17c7049fa69514e7` |
| SHA256 | `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca` |
| Architettura | Intel 8051 (opcode LJMP/MOVX/MOVC/DPTR verificati) |
| Versione core | stringa `ITE EC-V14.6` @ `0x50` |
| Build | blocco firma @ `0x7F80`: `ITE Tech. Inc. $` / `2025/04/15$` / `18:20:35$` / `V0.3.2$` |
| Compressione | no (entropia ~6 bit/byte nelle zone codice) |
| 16B-signature | presente @ `0x40` (vedi doc 02) |

## Entry point e vettori

- Reset `0x0000`: `LJMP 0x0070` → init (`SP=0xC0`, write `0x3F` su xdata `0x1001`, copia tabelle XRAM, `LJMP 0x00D2` → main init `0x0400`).
- Vettori 8051 standard: `0x03→0x057F`, `0x0B→0x0580`, `0x13→0x05AD`, `0x1B→0x05ED`, `0x23→0x0615`, `0x2B→0x0616`.
- Interrupt estesi ITE: stub `LJMP 0x28xx` → caricano `DPTR=0xF44D+n`, saltano al dispatcher `0x2800` (indice in R0, bit in `0x90-0x92`).
- Trampoline a "interrupt software": `0x2B6B–0x2BE0` (`MOV DPTR,#handler; AJMP 0x2800`) → handler nel banco commutabile.

## Mappa memoria (banchi)

La periferica **Bank** ha base xdata `0x1300h` (datasheet §3.2 memory map: SMFI `0x1000h`, INTC `0x1100h`, EC2I `0x1200h`, Bank `0x1300h`, Common `0x1400h`, double-map a `0x8000h`).

| Fisico | Contenuto |
|---|---|
| `0x0000–0x54D4` | banco 0 (fisso `0x0000-0x7FFF`): vettori, reset, modulo PD/UCSI (`0x3400–0x4300`), tastiera (`0x0A00–0x0Fxx`), tabelle scancode |
| `0x0040` | **16B-signature** (power-on, vedi doc 02) |
| `0x7F80–0x7FAE` | blocco firma testuale (non referenziato dal codice) |
| `0x8000–0xF8A4` | banco 1 (finestra `0x8000-0xFFFF`): header 9 byte + init che legge il selettore banco (xdata `0x0083/0x0084`) |
| `0x10000–0x15515` | banco 2 |
| `0x18000–0x18132` | banco 3: stub bank-switch (~0x133 byte) |
| resto | `0xFF` (flash cancellata) |

## Moduli principali (dal codice)

- **USB-C PD + UCSI**: stringhe `Code\Oem\UCSI.C`, comandi PD3/UCSI, PDO/RDO, DisplayPort Alt Mode con controller esterno Analogix (`GtAnalogix(MCU)`, `anx_vbus_status`), VDM.
- **KBC/tastiera PS/2**: vedi doc 03.
- **PMC/ACPI**: base `0x1500h` (PMSTS).

## Periferiche (istogramma DPTR/SFR dal codice)

- xdata: `0x103B-0x103F` = SMFI ECINDAR0-3/ECINDDR (accesso indiretto), `0x1300-0x1308` = modulo Bank, `0x1500/0x1501/0x1504` = PMC, `0x160A` = GPIO (base `0x1600h`), `0x0820-0x0842` = buffer XRAM, `0x004B/0x004C` = KBC status/data (porte host `0x64`/`0x60`).
- SFR: `0x82/0x83` DPL/DPH, `0xE0` ACC, `0xF0` B, `0x81` SP, `0x90` P1, bit IE `0xA8-0xAF`.
