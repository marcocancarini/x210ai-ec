# 02 — Checksum e firme: cosa esiste davvero

## 1. La "16B-signature" a 0x0040 (NON è una firma crittografica)

Bytes del firmware a `0x0040`:

```
A5 A5 A5 A5 A5 A5 A4 95 85 12 26 E6 AA 00 55 55
```

Corrispondono al pattern documentato nel datasheet IT5570/IT5571 §6.4.3.11.1
("16B-signature and Implicit/Explicit EC Code Base Address"):

- byte 8 (flag) = `0x95` = `10010101b`, esattamente la maschera richiesta (bit7=1, bit4=1, bit2=1, bit0=1);
- byte 9-10 = `85 12` (marker fissi);
- ultimo byte 14 = range confrontata ADDR[17:10] tra e-flash e SPI flash (variabile);
- `55 55` in coda.

**Funzione**: il power-on detection della boot ROM scandisce `0x40,0x50,…,0xF0` rispetto alla
code base per localizzare dove inizia il codice EC (formato "implicit" → code base `0x000000`).
È un **marcatore di posizione**, non un controllo di integrità.

⚠️ Quando si patcha il firmware: **lasciare intatta la 16B-signature a `0x40`** (o riposizionarla
a un offset `0x40/0x50/…/0xF0` valido rispetto alla code base), altrimenti la boot ROM non
trova la code base e l'EC non parte.

## 2. Nessuna firma crittografica interna

Verifiche fatte sul binario:

- nessuna costante SHA-1/SHA-256/MD5/RSA, nessuna tabella CRC32/CRC16;
- nessun campo checksum: somma 16-bit del file = `0x8419` (non nulla, e il complemento non
  compare da nessuna parte); somme per banco non nulle;
- il blocco a `0x7F80` (`ITE Tech. Inc.$`, data, `V0.3.2$`) è **solo testo** e non è
  referenziato dal codice (zero `MOV DPTR,#0x7Fxx`);
- il percorso di reset (`0x0070`) **non verifica la flash**: va dritto a init hardware e main;
- l'unica stringa "checksum" (`0x4000`, `checksum error:`) è del protocollo USB-C PD;
- l'unico CRC è quello di trasporto eSPI (bit CRC enable in config eSPI, datasheet §6.x) —
  a livello di link, non del firmware.

## 3. Dove possono esserci controlli (fuori dal .bin)

- **Boot ROM mascherata del chip**: non leggibile dal file. Se dopo un flash l'EC resta morto,
  è il primo sospetto (recupero via ISP, vedi doc 04).
- **Protezione flash lato host**: registri SMFI `P0BA0R/P0BA1R` (xdata `0x104F/0x1050`,
  datasheet §6.4.4.17/18) definiscono range di read/write protection sulla SPI flash fisica;
  più i классici PRx del flash descriptor. Verificare con `fpt.efi` / `flashrom --wp-list`.
- **Capsula BIOS Lenovo (.fl1/.cap)**: firmata RSA lato host — un EC modificato *dentro la
  capsula* non passa. Ma flashando l'EC direttamente (ifu.efi / ISP / programmatore) non c'è
  alcuna verifica di firma sull'immagine EC.

## 4. Conclusione operativa

| Aspetto | Esito |
|---|---|
| Firma crypto nell'immagine EC | **assente** |
| Checksum interno da correggere dopo una patch | **nessuno trovato** |
| Marcatore richiesto dal boot | **16B-signature @ `0x40`** (preservarla) |
| Vincoli di patch | dimensione 128 KiB (pad `0xFF`), layout 4 banchi × 32 KiB, 16B-signature intatta |
| Verifica lato host (capsula BIOS) | sì, ma solo per update BIOS via capsula Lenovo |
