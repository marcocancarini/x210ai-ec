# 12 — Verifica della patch Fn→Ctrl su EC0416 (efficacia, dimensione, logica)

File patchato: `dumps/EC0416_fn-ctrl-swap.BIN` (patch: 1 byte a `0x0C35`).

## 1. Dimensione e integrità strutturale

| Check | Esito |
|---|---|
| Size | 131072 byte = identica all'originale ✓ (nessun problema di dimensione) |
| Byte modificati | **1 solo**, offset `0x0C35` (`0x54→0x1D`) ✓ |
| 16B-signature `0x40` | intatta ✓ (`a5…95 85 12 26 e6 aa 00 55 55`) |
| Tabella vettori `0x0000-0x003F` | intatta ✓ |
| sha256 patchato | `970431688f10aa160973d3f276c453e5cc86427a28a01ee34ef43ea17dfabee8` |

## 2. Logica (emulazione della routine di conversione `0x0C09`)

La patch cambia solo l'operando di `MOV R7,#imm` nel caso speciale `0x84`:
l'instruction stream resta allineato (opcode `0x7F` a `0x0C34` intatto, lunghezza invariata).

| Scancode | orig make/break | patch make/break | cambia? |
|---|---|---|---|
| `0x84` (Fn/custom) | `0x54` / `0xD4` | **`0x1D` / `0x9D`** | **sì → emette LCtrl (set-1 `0x1D`)** |
| `0x14` (L-Ctrl) | `0x1D` / `0x9D` | `0x1D` / `0x9D` | no (Fn ora = Ctrl, come voluto) |
| `0x83` (F7) | `0x41` / `0xC1` | identico | no |
| `0x58` Caps, `0x76` ESC, `0x5A` Enter, `0x29` Space, `0x61` ISO | identici | identici | no |

Conclusione: la patch è **efficace** (Fn → Left-Ctrl make/break corretti) e **non altera**
nessun altro tasto né dimensione né firma; il resto del firmware è byte-identico.

## 3. Database XGecu T48 (verificato su `SupportLists/T48_List.txt` V13.16, mirror Kreeblah/XGecu_Software)

- Sezione `[ ITE [Testing] ]` → **"IC Support: 0 PCS"**: nessun chip ITE nel database.
- Nessuna entry `IT55xx / IT85xx / IT8xxx` in tutta la lista (37103 dispositivi).
- Quindi il **T48 NON supporta IT5571/IT5570**: niente programmazione diretta della eFlash
  EC via BGA sul T48. Il T48 resta valido solo per la flash BIOS SPI (W25Q/MX25/N25Q/…
  tutte presenti nella lista).
- Per la eFlash dell'EC restano: ISP via KBS (doc 11) oppure host LPC/eSPI
  (`fpt.efi`/`flashrom -p internal`/`ifu.efi`, doc 04).
