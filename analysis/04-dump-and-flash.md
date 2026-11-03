# 04 — Dump e flash dell'EC IT5571

Chip: **IT5571E/VG-128** → eFlash **embedded da 128 KiB** dentro il chip (datasheet: "128K-byte
embedded flash"). La flash è interna; l'interfaccia FSPI (FSCK/FSCE#/FMOSI/FMISO, alim. VFSPI)
serve per flash esterna opzionale / condivisa (MAFS/SAFS via eSPI).

File di lavoro: `dumps/EC0416.BIN` — MD5 `7392fa5138c906ac17c7049fa69514e7`,
SHA256 `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca`.

## A. Dump/flash via software interno (a macchina accesa)

### A1. UEFI Shell + tool ITE/Intel (dal pacchetto X210AI0724BIOS)

Il pacchetto `X210AI0724BIOS.zip` contiene il kit completo:
- `UEFI环境/EFI/BOOT/BOOTX64.efi` (e BOOTIA32) → chiavetta USB avviabile in UEFI Shell (F12);
- `Fpt.efi` — Intel Flash Programming Tool (flash BIOS): `fpt.efi -f <bios>.bin`
  (vedi `fb.nsh`: `fpt.efi -f MTLH-NB06_B0.2.bin`); dump completo con `fpt.efi -d dump.bin`;
- tutorial docx: per l'**EC** si usa **`ifu.efi <EC>.bin 128`** (128 = dimensione EC in KiB;
  per EC da 64 KiB: `ifu.efi <EC>.bin` senza parametro).

Esempio (da tutorial):
```
fs0:
cd <cartella con EC>
ifu.efi EC0416.BIN 128
```

### A2. Da Linux (host, via LPC/eSPI)

```
sudo flashrom -p internal -r ec-dump.bin        # dump della flash accessibile dal host
sudo flashrom -p internal -w EC0416_patched.BIN  # write (se la regione EC non è lockata)
flashrom --wp-list                                # stato dei write-protect
```

### A3. Verifica del dump

Confrontare sempre hash con il dump di riferimento:

```
md5sum ec-dump.bin      # atteso: 7392fa5138c906ac17c7049fa69514e7
sha256sum ec-dump.bin   # atteso: acaf8fed...994cb6dca
```

## B. ISP via connettore tastiera (boot ROM ITE, "esterno" ma senza smontare)

Datasheet §7.24.3.1: adattatore **porta parallela DB25 femmina sul connettore KBS**
(pinout: KSO0–KSO7 = PD0–PD7, KSO8=ACK#, KSO9=BUSY, KSO10=PE, KSO12=SLCT, KSI0=STB#…).
Mette l'EC in modalità ISP: dump/flash con il tool ITE, a macchina spenta (alimentazione
standby presente). È il metodo di recovery ufficiale quando l'EC non parte.

## C. Programmatore esterno (chip flash / pin FSPI)

- Se la scheda usa flash SPI esterna condivisa (MAFS/SAFS): clip SOIC-8 sul chip flash
  (CH341A / TinyPirate…) e dump/flash della regione EC. Attenzione ai blocchi di
  protezione (descriptor PRx + SMFI P0BA0R/P0BA1R @ xdata `0x104F/0x1050`).
- L'eFlash embedded del IT5571 non è su zoccolo: l'accesso "fisico" è via FSPI (se il board
  la espone) o via ISP su KBS (punto B). In pratica VFBGA-128 non si dissalda.

## D. Procedura consigliata per flashare un EC modificato

1. **Dump di backup** (A1/A2) e verifica hash.
2. Patch del binario rispettando: dimensione 128 KiB (pad `0xFF`), layout 4 banchi × 32 KiB,
   **16B-signature intatta a `0x40`** (vedi doc 02), tabelle non spostate (indirizzi assoluti).
3. Nessun checksum interno da aggiornare (nessuno trovato — vedi doc 02).
4. Flash con `ifu.efi EC_mod.BIN 128` da UEFI Shell (oppure `flashrom -w` se la regione è
   sbloccata, oppure ISP via KBS).
5. Verifica post-flash: ri-dump e confronto hash; boot test.
6. **Recovery**: se l'EC non parte, riflashare il backup via ISP (KBS + adattatore parallelo)
   o programmatore esterno.

## E. Checklist protezione prima di flashare da esterno

```
flashrom --wp-list            # o: fpt.efi -d dump.bin e ispezione descriptor
```
Se la regione EC risulta protetta (PRx / P0BA), sbloccarla via host (fpt) prima del
programmatore esterno, altrimenti il write fallisce o produce un brick.
