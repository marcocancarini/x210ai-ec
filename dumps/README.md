# Dump della X210AI

Letture fatte dalla scheda. I file da flashare stanno in [`firmware/`](../firmware/README.md). Gli hash completi sono in [`SHA256SUMS`](SHA256SUMS): dalla cartella `dumps/` si controllano con `sha256sum -c SHA256SUMS`.

## EC

| File | Letto il | Contenuto | Strumento | SHA256 |
|---|---|---|---|---|
| `ec/EC-V0.4.0-20250723-lettura1.bin` | 2026-11-04 | Firmware originale `V0.4.0`, build 2025-07-23 18:11:04 | `ifu.efi /S 128 /k /j` | `9b8334bd5d59` |
| `ec/EC-V0.4.0-20250723-lettura2.bin` | 2026-11-04 | Seconda lettura, identica | `ifu.efi /S 128 /k /j` | `9b8334bd5d59` |

Dimensione 131072 byte, due letture identiche, firma e CRC corretti. È la base di tutte le patch e il file di ritorno all'originale.

## BIOS

| File | Letto il | Contenuto | SHA256 |
|---|---|---|---|
| `bios/BIOS-X210AI-20261104-lettura1.bin` | 2026-11-04 | Chip SPI del BIOS, 32 MiB | `dd6e311622b8` |
| `bios/BIOS-X210AI-20261104-lettura2.bin` | 2026-11-04 | Seconda lettura, identica | `dd6e311622b8` |

Dimensione 33554432 byte, con flash descriptor a `0x10`, SHA256 `dd6e311622b8c61fe8c51de8fef8f3ff28b625dffc5097836f12f5cd5b884669`. **Non sono nella repo:** contengono dati della macchina, come NVRAM, voci di avvio e regione ME, quindi la cartella `bios/` resta solo in locale ed è ignorata da Git. Non sono ancora un'immagine di recovery verificata.

## Nomi

- EC: `ec/EC-<build>-<data build>-letturaN.bin`, per esempio `ec/EC-V0.4.0-all-keys-20261105-lettura1.bin` per un firmware patchato, con la data della lettura.
- BIOS: `bios/BIOS-X210AI-<data lettura>-letturaN.bin`.
- Ogni dump va letto due volte. Dopo averlo aggiunto, aggiornare questa tabella e, per l'EC, `SHA256SUMS`. I dump BIOS non si committano.

**Manca:** il dump di `all-keys` dopo il flash. L'hash deve iniziare con `d96e1b3e6a4f` (`firmware/README.md`, sezione Conferma).
