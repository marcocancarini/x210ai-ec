# Chiavetta USB

Qui c'è solo quello che si può ridistribuire: la UEFI Shell (`EFI/BOOT/BOOTX64.efi`, `BOOTIA32.efi`, build EDK2 del 2013) e lo script `fe.nsh`.

## Strumenti proprietari, non inclusi

`ifu.efi` e `Fpt.efi` sono strumenti proprietari di ITE e Intel: non sono nella repo. Si trovano su internet, di solito nei pacchetti di aggiornamento EC e BIOS dei produttori di mini PC e schede. Dopo averli scaricati, controllare l'hash: i comandi della guida sono stati provati solo con queste versioni.

| File | Cos'è | Dove era | SHA256 |
|---|---|---|---|
| `ifu.efi` | ITE Flash Utility 2.3.1a, build DEBUG. Legge e scrive l'e-flash dell'EC | Pacchetto EC `X210AI-EC-updated-on-03-22.zip`, cartella `MTLH-NB06-ec-250322/` | `16c0827384c6b4509799d02d7560b413642e413582591b49fd6f428896b28176` |
| `Fpt.efi` | Intel Flash Programming Tool. Legge e scrive il chip SPI del BIOS | Pacchetto BIOS `X210AI0724BIOS.rar` | `478b1bd41adbfe68d56391fdc6cd47534ac4c33ccaabd64f50a96f9ea285df69` |

Hash dei pacchetti del produttore: `X210AI-EC-updated-on-03-22.zip` `b850c8941df6eecbea035aefe481eb1c50fe8d5da4ea9b333717fc7a7230bc4e`, `X210AI0724BIOS.rar` `a1090b7986e6e3cb2485333f73fd5f8d62822f64bedfe7cad5733e88ddd94663`.

Una volta scaricati, vanno messi in questa cartella, in radice sulla chiavetta FAT32 accanto a `EFI/`. Restano esclusi da git (`.gitignore`).

## Uso

- Lettura dell'EC: `ifu.efi /S 128 /k /j` ([2.2](../docs/2-modifiche-software.md#22-lettura-dellec))
- Scrittura dell'EC: `ifu.efi <file>.bin 128`, cioè `fe.nsh` ([2.4](../docs/2-modifiche-software.md#24-scrittura-dellec-con-ifu-rischi))
- Lettura del BIOS: `fpt.efi -d full.bin`
- Procedura completa di flash da CachyOS e UEFI Shell: [`firmware/README.md`](../firmware/README.md#flash)
