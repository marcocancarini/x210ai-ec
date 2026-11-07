# Parte 8: Ventole, analisi del firmware EC

Dove il firmware legge e imposta male la ventola, e come si può correggere. La [parte 3](3-curve-ventola.md) descrive la curva, la [parte 4](4-ventola-acpi.md) le vie per cambiarla dall'OS.

**Da dove vengono i dati:** codice della `V0.4.0`, datasheet IT5570 e prove nell'[emulatore](../tools/emulator/README.md). Nessuna prova è stata fatta sulla scheda, e **nessuna immagine con queste correzioni è stata generata**.

**In sintesi:** il firmware tiene al sicuro la CPU soprattutto per prudenza, non per controllo. Non sa se la ventola gira, ignora gli errori di lettura della temperatura e la sua isteresi non funziona. I problemi principali si possono correggere via firmware con circa 200 byte di codice, senza toccare l'hardware. I giri richiedono prima una misura sulla scheda.

## 8.1 La catena completa

| Fase | Dove | Cosa succede | Periodo |
|---|---|---|---|
| Pianificazione | `0xB614` → `0xE639` | Parte solo con canale OOB pronto (`0x3113` bit 0 e 1), `0x9555` e `0x9564` a zero e `0xCE90` = 1 | Task da 100 ms |
| TjMax | `0xDE89` | Se `0x9551` è 0 la chiede alla CPU una volta. Se fallisce usa 110 °C | Una volta |
| Richiesta | `0xDF98`, modello a `0x3409` | Invia sull'eSPI, canale OOB, il messaggio `21 00 08 20 01 05 0F 30 01 02 01`: **PECI GetTemp** verso la CPU `0x30`, tramite il PCH | Circa 1,8 s |
| Risposta | `0xDF65`, `0xE006` | Attende fino a 256 attese da circa 15 µs, poi copia in `0x9620` | Circa 4 ms al massimo per attesa |
| Conversione | `0xDEC4-0xDF2E` | `0x9550 = TjMax - (-grezzo) / 64`, in gradi interi | Dopo ogni risposta |
| Pubblicazione | `0xBC02` | Copia `0x9550` nell'offset EC `0x70` | Circa 1 s |
| Curva e rampa | `0xB9E9` | Vedi [3.1](3-curve-ventola.md#31-il-percorso-nel-firmware) | Circa 100 ms |
| Uscita | `0x1802`, `0x1803` | Duty su PWM0 e PWM1, circa 20 kHz | Circa 100 ms |
| Giri | Nessuna | I piedini sono configurati, i registri non vengono letti | Mai |

I periodi vengono dalla cascata dei contatori ([3.1](3-curve-ventola.md#31-il-percorso-nel-firmware)), con tick da 1 ms ipotizzato. La via `0x31B0-0x31C4` è quella dei registri eSPI OOB del datasheet (sezione 6.1.3.4). Il blocco PECI a `0x3000` è usato altrove, non in questo percorso.

## 8.2 Problemi delle letture

| Sigla | Problema | Prova | Conseguenza | Gravità |
|---|---|---|---|---|
| **L1** | **Errori di lettura ignorati.** Se `0xDF98` fallisce, `0xDEC2` esce e `0x9550` resta com'è. `0x9508` conta i fallimenti ma nessuno lo legge | Solo due accessi a `0x9508`, entrambi di incremento. Emulatore: 55 °C restano 55 °C | Con la CPU che scalda e l'OOB fermo, la ventola resta al vecchio duty senza alcun allarme | **Alta** |
| **L2** | **Tachimetro mai letto.** `0x181E-0x1821` non hanno accessi, diretti o da tabella | Ricerca nell'immagine | Una ventola bloccata non si rileva, e nessuno strumento può mostrare i giri | **Alta** |
| **L3** | **Errori PECI scambiati per temperatura.** La risposta non viene controllata: i codici `0x8000-0x8004` diventano 110 °C | Emulatore, tutti e cinque i codici | L'errore spinge la ventola al massimo. Va nella direzione sicura, ma falsa la lettura | Media |
| **L4** | **Nessun sensore per Linux.** Nessun `fan` in hwmon, `acpitz` fisso a 27,85 °C, nessun `_FST` | [4.1](4-ventola-acpi.md#41-cosa-offre-lacpi-di-fabbrica) | L'OS non può sorvegliare la ventola | Media |
| **L5** | **Nessuna protezione termica nell'EC.** `0x9550` serve solo alla ventola: non c'è confronto con una soglia di spegnimento | Accessi a `0x9550`: solo le due scritture e la copia in `0x0470` | Il firmware non spegne la macchina. Restano le protezioni della CPU | Media |
| **L6** | **Campione lento e non filtrato.** Una lettura ogni 1,8 s circa, in gradi interi | [8.1](#81-la-catena-completa) | Un picco di un istante conta quanto una temperatura stabile | Bassa |
| **L7** | **`0x70` vecchio da spento.** In S3 e S5 la lettura si ferma e l'offset conserva l'ultimo valore, mentre `0x42` e `0x44` vengono azzerati | `0xB98F` non tocca `0x470` | Leggere lo spazio EC da spento può ingannare. Al risveglio la curva parte da lì per circa 2 s | Bassa |
| **L8** | **Tachimetro non affidabile da fuori.** Il datasheet dice che leggere `F1TLRR/F1TMRR` da D2EC/I2EC non è garantito | Datasheet IT5570, 7.12.4.15 | Per i giri dall'host serve una patch, non I2EC | Bassa |

**Il caso dei 100 °C del 17 ottobre.** Si restringe: un codice d'errore PECI darebbe 110 °C, quindi quel valore è una lettura valida. La seconda prova mostra l'EC a 100 °C con duty 152 nei primi secondi di carico: è la stessa situazione del dump, quindi la spiegazione più probabile è un picco reale durante la diagnostica.

### Misure sulla scheda

Script e log sono in `storico/test-ventola-20261107/`: `ec_log.sh` e `ec-log.csv` per la prima prova, `ec_log2.sh` e `ec-log2.csv` per la seconda, `spike.py` per gli spike.

Prima prova del 2026-11-07, con `all-keys` e sola lettura di `ec_sys`, una lettura al secondo per 153 s. Il carico è durato solo 3 s, perché il limite di 95 °C dello script è scattato su uno spike.

| Dato | Valori |
|---|---|
| `coretemp` | 46-95 °C |
| Temperatura EC `0x70` e `0x42` | **54 °C in tutte le letture** |
| Obiettivo `0x44` | 60 in tutte le letture |
| Duty `0x46` | 64 nel dump iniziale, 63 alla prima riga, poi 60 |
| Tabella e modo | Valori di fabbrica, modo `0x10` |

A 46-48 °C la curva avrebbe dovuto dare 40, quindi **in questa prova la temperatura dell'EC non si è aggiornata**, mentre rampa e curva funzionavano. Il duty in discesa all'inizio mostra che il valore era cambiato poco prima.

Seconda prova del 2026-11-07, sempre in sola lettura: 6 byte ogni 5 s, 1 minuto a riposo, 5 minuti di carico su 22 thread, 3 minuti di raffreddamento. **Qui la temperatura EC segue `coretemp`,** quindi il blocco non è costante. La differenza più evidente tra le due prove è il ritmo delle letture, 52 byte al secondo contro 6 ogni 5 s, ma il legame non è ancora provato.

| Fase | Temperatura EC | Obiettivo | Duty | Frequenza media |
|---|---|---|---|---|
| Riposo | 49-57 °C | 40-60 | 44-67, oscilla | Circa 1200 MHz |
| Primi 20 s di carico | Fino a 100 °C | 152 | Sale fino a 152 | Circa 2640 MHz |
| Carico stabile | 74-79 °C | 140, una volta 120 | 140 (92 %) | Circa 1850 MHz |
| Raffreddamento | 47-65 °C | 40-100 | 40-115, oscilla | Circa 1100 MHz |

- **Pendolamento confermato:** a riposo l'obiettivo salta tra 40 e 60 e il duty non si assesta (I1, I2).
- **Rampa confermata:** da 86 a 137 in 5 s, cioè circa 10 conteggi al secondo, coerente con il loop da 100 ms.
- **Limite di potenza:** dopo circa 25 s la frequenza scende da 2640 a 1850 MHz e la temperatura da 100 a 74 °C. La CPU rallenta per il passaggio da PL2 (64 W) a PL1 (28 W), non per merito della ventola. I watt reali non sono stati misurati.
- **Throttling:** `package_throttle_count` sale di circa 650 eventi nei secondi a 100 °C e continua a salire poco anche con gli spike a riposo. La causa degli eventi non è stata letta.
- **Giri:** non misurati. Il valore 3705 nell'output è quel contatore.

**Spike di `coretemp`.** Con 2 s di carico da 46 °C il picco è stato 101 °C con 1 thread, 100 °C con 4 e 90 °C con 22, con ritorno a 47 °C entro un secondo dalla fine, tranne con 1 thread (82 °C). `coretemp` si aggiorna una volta al secondo. È un picco locale del core in turbo: il dissipatore non fa in tempo a riceverlo e la ventola non può intervenire.

## 8.3 Problemi delle impostazioni

| Sigla | Problema | Prova | Conseguenza | Gravità |
|---|---|---|---|---|
| **I1** | **Isteresi senza effetto,** per un errore di registro a `0xBB13-0xBB35` | [3.3](3-curve-ventola.md#33-comportamento-verificato) | Con la temperatura su una soglia la ventola cambia velocità in continuazione | **Alta** |
| **I2** | **Gradini grandi rispetto alla rampa.** In 1,8 s la rampa copre circa 18 conteggi, quasi tutto un gradino da 20 | Calcolo da [8.1](#81-la-catena-completa) | La rampa non assorbe il pendolamento: può arrivare al 12 % a ogni lettura | **Alta** |
| **I3** | **Manuale senza scadenza.** `0x90` non ha timeout, e dopo la sospensione l'obiettivo resta 0 | Emulatore, [4.6](4-ventola-acpi.md#46-rischi) | Ventola ferma con la macchina accesa | **Alta** se si usa il manuale |
| **I4** | **Curva calda da 40 °C.** Oltre il 50 % a 55 °C, 100 % a 80 °C | [3.4](3-curve-ventola.md#34-valutazione) | Rumore con poco carico | Media |
| **I5** | **Discesa veloce come la salita.** Il divisore c'è, ma vale 0 | Emulatore | Peggiora I2 | Media |
| **I6** | **Niente controlli sullo spazio EC.** Tutti i 256 byte sono scrivibili e la tabella non viene verificata | [4.2](4-ventola-acpi.md#42-il-comando-di-scrittura-dellec) | Un errore dell'host può fermare la ventola. `0xFB` a 1 la spegne tramite `0xCE71` | Media |
| **I7** | **Impostazioni non persistenti.** La tabella è in RAM: al reset dell'EC tornano i valori di fabbrica | `0xB841`, solo all'avvio | Serve un servizio nell'OS, o la patch | Media |
| **I8** | **Nessun avvio forzato.** Da ferma la ventola riceve solo 13 % | [3.4](3-curve-ventola.md#34-valutazione) | Se quel duty non basta, resta ferma tra 40 e 45 °C. Da misurare | Da misurare |
| **I9** | **Sorgente 1 bloccata.** Senza `0x7B` a 1, la sorgente 1 diventa 0 e la 3 diventa 2 | Emulatore | Conta solo se si aggiungono sensori | Bassa |
| **I10** | **Sorgente diversa da 0 nella fascia di isteresi.** L'obiettivo diventa il numero della sorgente: 1, 2 o 3 | Codice | Duty quasi nullo. Oggi non capita, perché la sorgente è 0 | Bassa |

## 8.4 Cosa si corregge e come

| Problema | Dall'OS | Patch EC | Hardware |
|---|---|---|---|
| I4 curva, I5 discesa | **Sì,** in RAM | **Sì,** permanente | — |
| I2 pendolamento | In parte, con `0xC0` in `0x4C/0x4D` | **Sì** | — |
| I1 isteresi | No: si può solo simulare con un servizio | **Sì** | — |
| I3 manuale | Con attenzione al risveglio | **Sì** | — |
| I7 persistenza | Serve un servizio | **Sì** | — |
| L1 errori, L3 PECI | No | **Sì** | — |
| L2 giri | No | **Sì,** se il tachimetro è collegato | Misura su EC 47 e 48 |
| L4 sensori Linux | Con una SSDT: `_TMP` da `0x70`, `_FST` | Serve per i giri | — |
| L5 protezione termica | Si può sorvegliare da un servizio | Possibile, da progettare | — |
| I8 avvio forzato | Solo con misura e manuale | Possibile dopo la misura | — |

**Ordine consigliato:**

1. Leggere lo spazio EC e misurare ([4.4](4-ventola-acpi.md#44-prova-in-sola-lettura), [3.5](3-curve-ventola.md#35-cosa-misurare)).
2. Provare da OS curva e divisore ([4.5](4-ventola-acpi.md#45-prova-in-scrittura)).
3. Verificare i piedini del tachimetro ([6.1](6-modifiche-hardware.md#61-misure-mancanti)).
4. Avere pronta una via di recovery ([6.2](6-modifiche-hardware.md#62-modifiche-possibili)).
5. Solo allora generare e flashare una patch, a partire da [8.5](#85-correzioni-proposte-nel-firmware).

## 8.5 Correzioni proposte nel firmware

`tools/emulator/fan_fix.py` applica queste modifiche **solo in memoria** a `all-keys` e le prova. Non scrive alcun file. Aggiunge 215 byte a `0x5660`, nella zona libera dopo il codice di `all-keys`.

| Dove | Prima | Dopo | Risolve |
|---|---|---|---|
| `0xBB31` | `50 03` | `00 00` | I10: sotto la tabella l'obiettivo è sempre 0 |
| `0xBB36` | Scrive l'obiettivo | Salta alla nuova routine di isteresi | I1, I2 |
| `0xDEBE` | `LCALL 0xDF98` | `LCALL` del controllo errori | L1, L3 |
| `0xB60B` | `LCALL 0xBC14` | `LCALL` del task ventola esteso | L2, I3 |
| `0xDC44` | `LCALL 0xBC0E` | `LCALL` di init esteso | I5 |

**Isteresi.** Vale per tutte le soglie, non solo per la prima:

```
obiettivo = max(nuovo, min(vecchio, curva(temperatura + isteresi)))
```

In salita non cambia nulla. In discesa la ventola tiene il gradino finché la temperatura non è scesa di `0x4A` gradi sotto la soglia, 2 °C di default. Se la temperatura crolla, l'obiettivo segue la curva. Con isteresi 0 la curva è quella di fabbrica.

| Sequenza | Fabbrica | Con la correzione |
|---|---|---|
| Da 41 a 39 °C | 0 | 20 |
| Da 41 a 37 °C | 0 | 0 |
| Da 60 a 58 °C | 80 | 100 |
| Da 60 a 57 °C | 80 | 80 |
| Da 80 a 30 °C | 0 | 0 |
| Da 30 a 39 °C | 0 | 0 |

**Errori di temperatura.** La routine avvolge `0xDF98` e considera errore anche una risposta `0x8000-0x8004`. Conta i fallimenti di fila nell'offset `0x7C`, che si legge dall'OS. Dopo 5 errori, il successivo imposta 90 °C e la ventola va al massimo. Una lettura buona azzera il contatore.

**Tachimetro.** Il task copia a ogni giro `0x181E-0x1821` negli offset `0x74-0x77`: `0x74-0x75` ventola 1, `0x76-0x77` ventola 2, byte basso prima. I giri si ricavano dal datasheet (sezione 7.12.3.2):

```
giri/min = 60 × fs / (conteggio × P)        fs = FreqEC / 128 ≈ 71,9 kHz
```

`P` è il numero di impulsi per giro, spesso 2, e conteggio 0 significa ferma. Il valore `FreqEC` di 9,2 MHz è quello dell'esempio nel datasheet.

**Uscita dal manuale.** Quando `0xCE90` restituisce 0, il task toglie il bit 7 dal modo: alla ripresa la curva riparte da sola.

**Discesa.** All'avvio dell'EC `0x4C/0x4D` valgono `0xC0`: discesa 4 volte più lenta della salita.

**Curva.** La proposta non la cambia: i valori dipendono dalle misure. Sono i byte `MOV A,#xx` in `0xB841-0xB98E`, due volte per i due canali.

### Verifiche fatte

| Prova | Risultato |
|---|---|
| Curva in salita, isteresi, canale 1, isteresi 0 | Tutte ok |
| Modo manuale e sorgente host | Invariati |
| Lettura buona, 5 errori, fail-safe, ripresa, errore PECI | Tutte ok |
| Tachimetro in `0x74-0x77`, uscita dal manuale | Ok, con valori simulati |
| Tastiera, 508 casi | Identica a `all-keys` |
| Scritture all'avvio | 186216 confrontate, identiche a parte i campi nuovi |

### Limiti

- I registri sono memoria semplice: l'emulatore non prova che `0x181E` contenga davvero i giri, né che il tachimetro arrivi al piedino.
- Se il canale OOB è fermo, `0xE639` esce prima della lettura: il controllo errori non viene chiamato e il problema L1 resta in quel caso.
- All'avvio le prime letture possono fallire. Con 6 errori di fila la ventola andrebbe al massimo per qualche secondo: da valutare sulla scheda.
- Gli offset `0x74-0x77` e `0x7C` sono liberi secondo la ricerca nel codice e valgono 0 nella RAM del 17 ottobre. Una lettura indiretta non si può escludere del tutto.
- Una patch reale richiede `tools/patch_keyboard.py` esteso, CRC ricalcolato e le regole di [2.1](2-modifiche-software.md#21-patch-della-tastiera). Il flash ha gli stessi rischi di sempre ([2.4](2-modifiche-software.md#24-scrittura-dellec-con-ifu-rischi)).
