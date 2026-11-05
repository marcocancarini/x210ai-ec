import sys
p='README.md'; s=open(p,encoding='utf-8').read()
def R(a,b):
    global s
    if s.count(a)!=1: sys.exit('NOMATCH %d: %s'%(s.count(a),a[:70]))
    s=s.replace(a,b)
R("| Firmware EC | Analizzato, patch verificate staticamente (§2-§5) |",
  "| Firmware EC | `EC0416` analizzato, patch verificate staticamente (§2-§5). **Sulla scheda c'è la `V0.4.0`**, più recente: confrontata con `EC0416` (§9) |")
R("| Lettura EC | Più vie individuate, nessuna provata su questa scheda (§6, §7) |",
  "| Lettura EC | **Riuscita con `ifu.efi /S 128 /k /j`**: due letture identiche (§6). Le altre vie non sono provate (§6, §7) |")
R("| Immagine BIOS | **Assente**: il BIOS non è stato analizzato (§1, §8, §10) |",
  "| Immagine BIOS | Due letture identiche da 32 MiB in locale, non analizzate e fuori dalla repo (§1, §8, §10) |")
R("**Nessun tool è stato eseguito su una X210AI.** `ifu.efi`, `Fpt.efi` e i dump sono stati solo disassemblati.",
  "**Eseguito sulla X210AI:** solo `ifu.efi` in lettura (§6). **Nessuna scrittura è stata provata.** `Fpt.efi` e il percorso di scrittura di `ifu` sono stati solo disassemblati.")
R("""1. Dump software con `ifu.efi /S 128`, finché l'EC funziona (§6).
2. Cicalino sui 15 piedini verso il connettore tastiera, iniziando da KSO1 sui contatti 16 e 18 (§7).
3. Cicalino sui contatti 1, 3, 7, 8, 9 e 10 di `EC_SPI1`: massa, EC 119, EC 100 e piedini SMBus (§13).
4. Accesso al connettore tastiera: cavo di una tastiera X201 guasta o spina JAE AA01 a 40 posizioni, codice non ancora trovato (§7).
5. Cablaggio RP2040, poi `isp id` e `isp read` con l'EC sano. Niente scritture prima (§7).
""","""1. Cicalino sui 15 piedini verso il connettore tastiera, iniziando da KSO1 sui contatti 16 e 18 (§7).
2. Cicalino sui contatti 1, 3, 7, 8, 9 e 10 di `EC_SPI1`: massa, EC 119, EC 100 e piedini SMBus (§13).
3. Accesso al connettore tastiera: cavo di una tastiera X201 guasta o spina JAE AA01 a 40 posizioni, codice non ancora trovato (§7).
4. Cablaggio RP2040, poi `isp id` e `isp read` con l'EC sano: il risultato va confrontato con il dump `V0.4.0`. Niente scritture prima (§7).
5. Ricreare le patch tastiera sulla `V0.4.0` (§5).
""")
R("""| `dumps/EC0416.BIN` | `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca` | EC nuova, 131072 B, build `V0.3.2` 2025-04-15 18:20:35, md5 `7392fa5138c906ac17c7049fa69514e7` |
""","""| `dumps/EC-V0.4.0-20250723-lettura1.bin`, `-lettura2.bin` | `9b8334bd5d5986ce97dfc5d8503fa643a97d8abb6c6166ce181c0525ec722311` | **Firmware installato sulla scheda**, letto il 2026-11-04. 131072 B, build `V0.4.0` 2025-07-23 18:11:04. Due letture identiche |
| `dumps/EC0416.BIN` | `acaf8fed4b797f39d983849b916baaf61352832b337950fa9fb3225994cb6dca` | EC di aprile, **più vecchia della build installata**. 131072 B, build `V0.3.2` 2025-04-15 18:20:35, md5 `7392fa5138c906ac17c7049fa69514e7` |
""")
R("""**Immagine BIOS assente.** `fb.nsh` chiama `MTLH-NB06_B0.2.bin`, che non è incluso: nessun file del progetto contiene volumi firmware, regione ME o marcatori BIOS.
""","""**Immagine BIOS.** `fb.nsh` chiama `MTLH-NB06_B0.2.bin`, che non è incluso nel pacchetto. In locale ci sono `Bios dumps/full.bin` e `full2.bin`: 32 MiB, identici (SHA256 `dd6e311622b8c61fe8c51de8fef8f3ff28b625dffc5097836f12f5cd5b884669`), con flash descriptor a `0x10` e volumi `_FVH`. Non sono nella repo e non sono stati analizzati.
""")
R("""**Regole:** dimensione fissa 128 KiB""","""**Vale solo per `EC0416`:** i file `EC0416_*.BIN` sono basati sulla `V0.3.2` e flasharli riporterebbe indietro il firmware installato (§9). Sulla `V0.4.0` i byte `0x0C35`, `0x0D17` e `0x0D5B` stanno agli stessi indirizzi, con gli stessi valori e lo stesso contesto, quindi le patch si possono ricreare sul dump. Non è ancora stato fatto.

**Regole:** dimensione fissa 128 KiB""")
R("""Nessuna via è stata provata sull'IT5571. Partire sempre dalla sola lettura.
""","""La via software è stata provata sulla scheda il 2026-11-04. Le altre no. Partire sempre dalla sola lettura.
""")
R("""| **Software** | `ifu.efi /S 128` | Sì | **Più semplice**: niente hardware. Vedi sotto |""",
  """| **Software** | `ifu.efi /S 128 /k /j` | Sì | **Provata**: due letture identiche. Vedi sotto |""")
R("""```
ifu.efi /S 128
```

Salva 128 KiB in `ITEFW.bin` nella cartella corrente. La routine `0x422C` usa solo la lettura veloce `0x0B`, senza cancellazioni né scritture, quindi **non può causare il brick descritto in §9**.

- Usa lo stesso ingresso `0xDC`: l'EC si ferma durante la lettura e alla fine viene riavviato con `0xFE`. Aspettarsi uno spegnimento brusco.
""","""```
ifu.efi /S 128 /k /j
```

Maiuscole e minuscole contano. Salva 128 KiB in `ITEFW.bin` nella cartella corrente. La routine `0x422C` usa solo la lettura veloce `0x0B`, senza cancellazioni né scritture, quindi **non può causare il brick descritto in §9**.

**`/k /j` sono obbligatori.** Con il solo `/S 128` si ottiene un file da 0 byte, anche su volumi diversi (provato su chiavetta e partizione EFI). `ifu` crea il file (`0x519B`), legge (`0x526F`), invia `0xFE` (`0x5294`) e solo alla fine chiude il file (`0x5AFE` → `0x9F4C`): se il reset spegne la macchina, i dati non arrivano mai al disco.

- `/j` invia `0xFC` invece di `0xFE`: l'EC salta a `0x0400` senza reset (`0x80C4`).
- `/k` salta l'`0xAE` finale (`0x52A9`), inutile perché `/S` non invia `0xAD`, e la sua attesa senza timeout.
- Il comportamento della macchina a fine dump non è stato annotato. L'EC riparte senza un vero reset: spegnere subito con `reset -s`.
- Usa lo stesso ingresso `0xDC`: l'EC si ferma durante la lettura.
""")
R("""- Non funziona su un EC brickato.

""","""- Non funziona su un EC brickato.
- La partizione EFI è leggibile solo da root: da Linux copiare il dump con `sudo install -o $USER -g $USER -m 644`.

""")
R("""oggi non esiste un'immagine da usare per la recovery.
""","""le due letture in `Bios dumps/` (§1) vanno verificate prima di considerarle un'immagine di recovery.
""")
R("""Attenzione ai nomi: entrambe le build si dichiarano `V0.3.2`, pur differendo per 46.608 byte. Solo la vecchia contiene `MTLH-NB06`. Per distinguerle usare data o sha256.
""","""Attenzione ai nomi: entrambe le build si dichiarano `V0.3.2`, pur differendo per 46.608 byte. Solo la vecchia contiene `MTLH-NB06`. Per distinguerle usare data o sha256.

### Confronto tra V0.4.0 e EC0416

Gli indirizzi di questa sezione e dei paragrafi precedenti si riferiscono a `EC0416`, salvo dove indicato. Il flash viene eseguito dal firmware **in esecuzione**, quindi per `ifu` conta la `V0.4.0`. `EC0416` entra in gioco solo dopo il reset. `EC0416` è più vecchia di tre mesi: flasharla è un **downgrade**, non un aggiornamento.

| Punto | Esito del confronto statico |
|---|---|
| Ciclo di flash | Banco 1 identico da `0x8000` a `0x884B` |
| Ingresso `0xDC` | Stessa catena e stessi byte, tranne gli indirizzi rilocati (`0xDC94` → `0xDC5E`) |
| Variante PMC2 e uscita `0xFC`/`0xFE` | Uguali salvo rilocazione (`0xD9D3` → `0xD99D`, `0xDAB3` → `0xDA7D`) |
| Protezioni e watchdog | Stessi registri in `0x1000-0x10FF` e `0x1E00-0x1FFF`: nessuna nuova protezione rilevata |
| Pin | Tabella GPIO da 103 voci identica, spostata di `+0x1D` (`0x2660-0x2794` nella `V0.4.0`) |
| Comandi host | Stessi casi nella tabella di dispatch (`0xF61E`, ora `0xF5F0`) |
| Spazio EC | Stessi 141 indirizzi in `0x0400-0x05FF` |
| Vettori e avvio | Reset uguale. Differiscono solo tre byte di indirizzo in `0x70-0x3FF` e `0x4A-0x4B` (`AF 5B`, vedi §3) |
| Tastiera | Tabella `0x0D03` e routine `0x0C09` agli stessi indirizzi |

**Cosa cambia davvero.** Il confronto istruzione per istruzione, con gli indirizzi mascherati, dà 1542 blocchi diversi: 1181 sono solo rilocazioni, 361 sono strutturali, in parte dovuti alla disassemblaggio lineare delle tabelle. Quasi tutta la XRAM da `0x0823` è spostata di `-0x28`.

- Driver SMBus/I2C `0x1E00-0x2300` riscritto: `EC0416` usa i registri `0x1CB0-0x1CBA` in modo fisso, la `V0.4.0` passa da una tabella per canale (voci da 21 byte).
- Logica cambiata in più punti dei banchi 1 e 2, per esempio contatori `0x001D/0x001E` rimossi, condizione su `0x00B0` sostituita da `0xCE90`, costanti `0x32→0x26` (`0xDD83`) e `0x03→0x04` (`0xED71`).
- **Il significato di queste modifiche non è stato decodificato:** non si sa cosa corregga la `V0.4.0`, né se il downgrade tocca ricarica, USB-C PD, ventola o accensione.

**Conclusione.** Il confronto non mostra incompatibilità di pin o interfaccia e il percorso di `ifu` non cambia, ma non rende sicuro il flash. Restano valide tutte le debolezze sopra, la scrittura non è mai stata provata su questa scheda e la recovery ISP nemmeno. La lettura `/S` conferma solo ingresso `0xDC`, lettura e uscita `0xFC`.
""")
R("""2. Salva il firmware attuale con `ifu.efi /S 128` (§6) e verifica il dump.
""","""2. Salva il firmware attuale con `ifu.efi /S 128 /k /j` (§6) e verifica il dump. Poi spegni: il flash va fatto da un avvio pulito.
""")
R("""- Immagine BIOS (§8).
- Tabelle ACPI""","""- Analisi delle immagini in `Bios dumps/` (§1, §8).
- Tabelle ACPI""")
R("""| **EC** (eFlash nel chip) | ISP dal connettore tastiera (§7) + `EC0416.BIN` | Metodo da datasheet, collegamenti da ricavare |
| **BIOS** (chip SPI esterno) | Programmatore sul chip (§8) | Serve un dump fatto **prima**: oggi non ne abbiamo uno |""",
"""| **EC** (eFlash nel chip) | ISP dal connettore tastiera (§7) + `dumps/EC-V0.4.0-20250723-lettura1.bin` | Metodo da datasheet, collegamenti da ricavare |
| **BIOS** (chip SPI esterno) | Programmatore sul chip (§8) | Serve un dump verificato: quelli in `Bios dumps/` non sono ancora stati analizzati |""")
open(p,'w',encoding='utf-8').write(s)
p='TODO.md'; s=open(p,encoding='utf-8').read()
R("""Stato: analisi statica completa (vedi README.md). Nessun tool eseguito su hardware reale.
""","""Stato: analisi statica completa (vedi README.md). Eseguito su hardware solo `ifu` in lettura; nessuna scrittura provata.
""")
R("""- [ ] Dump EC software: `ifu.efi /S 128` (opzione nascosta, sola lettura) → confrontare con `dumps/EC0416.BIN` (size 131072, signature @0x40, 2 letture identiche)
- [ ] Dump BIOS prima di qualsiasi flash: `fpt.efi -d full.bin` o `flashrom -p internal -r full.bin` (oggi nessuna immagine di recovery esiste)
""","""- [x] Dump EC software: `ifu.efi /S 128 /k /j` (sola lettura, `/S 128` da solo dà 0 byte). Risultato: firmware installato `V0.4.0` 2025-07-23, più recente di `EC0416` (`dumps/EC-V0.4.0-20250723-lettura*.bin`)
- [ ] Verificare e analizzare `Bios dumps/full.bin` (32 MiB, 2 letture identiche) prima di considerarlo immagine di recovery
- [ ] Annotare come si comporta la macchina a fine dump con `/j`: ritorno al prompt, tastiera, `reset -s`
- [ ] Ricreare le patch tastiera sulla `V0.4.0`; non flashare `EC0416` né `EC0416_*.BIN` senza decidere il downgrade (README §9)
- [ ] Decodificare cosa cambia tra `EC0416` e `V0.4.0` (driver SMBus, logica banchi 1 e 2)
""")
open(p,'w',encoding='utf-8').write(s)
