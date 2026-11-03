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

## 5. Approfondimento: decodifica completa della 16B-signature e registri flash

### 16B-signature @ `0x0040` (datasheet §6.4.3.11.1, Table 6-28)

```
0x40: A5 A5 A5 A5 A5 A5 A4 95 85 12 26 E6 AA 00 55 55
      └─ padding A5 ──┘ │  │  │  │  │  │  │  └─ 55 55 (coda fissa)
                       │  │  │  │  │  │  └─ AA
                       │  │  │  │  │  └─ byte 14 = range ADDR[17:10] confrontata (qui 0x00)
                       │  │  │  │  └─ byte 13 (variante IT5571)
                       │  │  │  └─ 5A 5A attesi nel IT5570 (qui 26 E6: variante)
                       │  │  └─ marker fissi 85 12
                       │  └─ flag 0x95 = 10010101b (bit7,4,2,0 = 1 come da spec)
                       └─ 7° byte A4 (variante rev.2)
```

- La boot ROM scandisce `0x40,0x50,…,0xF0` rispetto alla code base: match → **formato
  "implicit", EC code base = `0x000000`** (coerente con i vettori a `0x0000`).
- Datasheet: "Add 16-bytes signature in F/W (**strongly recommended**)" — se manca, il
  power-on detection non localizza il codice (recupero via ISP, vedi doc 04).
- **Non è un hash/firma**: nessuna trasformazione dei dati, solo pattern fisso.

### Registri flash toccati dal firmware

| Registro | Indirizzo | Uso nel firmware |
|---|---|---|
| FPCFG | `0x1001` | reset scrive `0x3F` (`0x0073`): AFSTBY=0, bit5=1 |
| FLHCTRL2R | `0x1032` | bank select: `ANL A,#0xF7` a `0x251E-0x2524` (funzione bank-switch `0x2500-0x2525`) |
| FLHCTRL3R | `0x1063` | erase/program: init `0x0445-0x0456`; routine bank1 `0x89CB/0x89F1`, `0x80FC` |
| FLHCTRL6R | `0x1081` | `ORL 0x10` a `0xDC22-0xDC28` (handler update) |
| ECINDAR0-3/ECINDDR | `0x103B-0x103F` | 358 riferimenti: accesso indiretto (indirizzo+data) a flash/host — usato dalle routine di program |
| P0BA0R…P3ZR | `0x104F-0x1075` | **mai toccati dal firmware**: protezione impostata solo da boot ROM/host |

Conclusione: il firmware **non si fa self-checksum**; l'unico controllo di "validità" a
power-on è il match della 16B-signature (locator). La protezione in scrittura è affidata
a P0BA (SMFI) e ai PRx del flash descriptor, gestiti lato host/boot ROM.
