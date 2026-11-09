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

`tools/emulator/fan_fix.py` applica queste modifiche **solo in memoria** a `all-keys` e le prova. Non scrive alcun file. Aggiunge 251 byte a `0x5660`, nella zona libera dopo il codice di `all-keys`.

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

**Tachimetro.** Il task pubblica i conteggi negli offset `0x74-0x77` con la stessa routine della patch a sé ([8.6](#86-patch-del-tachimetro)).

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

## 8.6 Patch del tachimetro

`tools/emulator/tach_read.py` prova da sola la lettura dei giri, **solo in memoria** su `all-keys`, senza le altre correzioni. È la patch più piccola che rende leggibili i giri dall'OS, e serve anche a rispondere alla domanda sul terzo filo ([5.5](5-hardware.md#pwm-e-tachimetro-con-3-fili)). `fan_fix.py` usa la stessa routine.

**Perché una patch e non I2EC.** Il datasheet dice che leggere `F1TLRR/F1TMRR` da D2EC/I2EC non dà valori garantiti (L8). Dentro l'EC la lettura è quella prevista.

**Riferimento: system76/ec.** Il firmware aperto di System76 gira sullo stesso chip e legge il tachimetro così (`src/app/main/fan/common.c`, `src/ec/ite/pwm.c`):

| | system76/ec | Questa patch |
|---|---|---|
| Registri | `F1TLRR/F1TMRR` `0x181E-0x181F`, `F2TLRR/F2TMRR` `0x1820-0x1821` | Gli stessi |
| Scelta del piedino | Scrive `TSWCTLR` `0x1848` = 0: TACH0A e TACH1A | Non lo scrive: 0 è già il valore di reset (datasheet 7.12.4.32), e il firmware non tocca mai `0x1848` |
| Abilitazione PWM | `ZTIER` = `0x02`, `PWMLCCR` = `0xFF` | Già così nella tabella di init a `0x3308` |
| Lettura | `(F1TMRR << 8) \| F1TLRR`, una sola volta | Byte basso e alto, due volte. Pubblica solo se le due letture coincidono, fino a 3 tentativi, altrimenti tiene il valore precedente |
| Conversione | Giri/min nell'EC, divisione a 32 bit, `P = 2`, clock 9,2 MHz | Conteggio grezzo: la divisione la fa l'OS, che può scegliere `P` |
| Dove | Offset ACPI `0xD0-0xD3` | Offset `0x74-0x77`, liberi in questo firmware |
| Quando | A ogni passo della ventola | A ogni chiamata del task ventola, `0xB60B` |

Il datasheet chiede di leggere i due byte "in coppia", ma non dice se la lettura del primo blocca il secondo. La doppia lettura funziona in tutti e due i casi. Il conteggio grezzo evita di aggiungere una divisione a 32 bit in 8051.

**Modifica.** 72 byte a `0x5660` e una sola chiamata cambiata:

| Dove | Prima | Dopo |
|---|---|---|
| `0xB60B` | `LCALL 0xBC14` | `LCALL` della routine, che chiama `0xBC14` e poi legge i due tachimetri |

Dopo `0xB60B` il codice salta a `0xED56`, che non usa i registri lasciati da `0xBC14`: la routine può usare `A`, `R5-R7` e `DPTR`.

**Dall'OS.** `0x74-0x75` ventola 1, `0x76-0x77` ventola 2, byte basso prima. I giri si ricavano dal datasheet (sezione 7.12.3.2):

```
giri/min = 60 × fs / (conteggio × P)        fs = FreqEC / 128 ≈ 71,9 kHz
```

`P` è il numero di impulsi per giro, di solito 2. Conteggio 0 significa ferma. `FreqEC` vale 9,2 MHz tipici (Table 10-2), con una tolleranza dell'1,7 % tra 0 e 70 °C. Con `P = 2`: 539 = 4000 giri/min, 1078 = 2000.

### Verifiche fatte

| Prova | Risultato |
|---|---|
| Conteggi stabili sui due canali, byte basso prima | Ok |
| Ventola ferma, conteggio 0 | Ok |
| Conteggio che cambia tra i due byte, da `0x00FF` a `0x0100` | Pubblica `0x0100`. Una copia semplice darebbe `0x01FF`, cioè giri dimezzati |
| Conteggio che cambia tra le due letture | Pubblica il valore nuovo |
| Conteggio che cambia a ogni lettura | Tiene il valore precedente, al massimo 12 letture |
| Task ventola con 3 temperature, ventola accesa e spenta, modo automatico e manuale, 30 chiamate | Memoria identica all'originale, a parte `0x74-0x77` |
| Tastiera, scritture all'avvio | Identiche a `all-keys` |
| Costo | 45 istruzioni a chiamata, 2 byte di stack in più |

### Limiti

- L'emulatore prova la logica, non l'hardware: non sa se il tachimetro arriva a EC 47, né come si comporta il contatore senza impulsi.
- Se il driver commuta l'alimentazione a 20 kHz, il conteggio può essere sporco ([5.5](5-hardware.md#pwm-e-tachimetro-con-3-fili)). Lo dirà solo il confronto con la misura.
- Valgono gli stessi limiti della 8.5 per gli offset `0x74-0x77` e per il flash.

## 8.7 Simulatore dell'hardware della ventola

`tools/emulator/fan_sim.py` fa girare il **task ventola reale** (`0xB60B`, ogni 100 ms) con la patch del tachimetro, dentro un modello dell'hardware intorno all'EC (`tools/emulator/fan_plant.py`). Il firmware è il codice vero. L'hardware è un insieme di ipotesi con parametri: una prova superata dice come si comporta il modello, non la scheda.

| Parte | Modello | Da dove vengono i valori |
|---|---|---|
| PWM | Duty da `DCR0/CTR1`, periodo dai registri della tabella a `0x3308`, piedino GPIO alto o basso da `GPCRA0/GPDRA` | Firmware: circa 20 kHz |
| Driver | `linear`: tensione continua proporzionale al duty. `switched`: alimentazione commutata al ritmo del PWM. `pwm4`: ventola a 4 fili, per confronto | Ipotesi ([5.5](5-hardware.md#pwm-e-tachimetro-con-3-fili)) |
| Ventola | 5000 giri/min al 100 %, avvio dal 25 %, arresto sotto il 12 %, costanti di tempo 0,8 s in salita e 2 s in discesa, 2 impulsi per giro | Ipotesi |
| Linea del tachimetro | Bassa nella prima metà di ogni impulso, solo se la ventola è alimentata. Pull-up a 3,3 V | Open collector, come d'uso |
| Contatore ITE | A ogni fronte di discesa scrive i tick a `fs = 9,2 MHz / 128` dal fronte precedente. Senza fronti per `0xFFFF` tick (0,9 s) scrive 0. Filtro anti-disturbo regolabile, di default assente | Datasheet 7.12.3.2 per la formula. Timeout e filtro sono ipotesi |
| Temperatura | Due nodi, die e dissipatore, con limite a 100 °C. Carico: riposo, PL2 64 W per 25 s, PL1 28 W, riposo | Tarato a grandi linee sulla prova del 2026-11-07 (8.2) |
| Tempi | Un'istruzione 8051 = 12 clock a 9,2 MHz. L'host legge via I2EC i due byte a 20 µs di distanza | Ipotesi |

Il tempo del modello avanza anche durante il codice dell'EC. Quindi un conteggio può cambiare tra la lettura di un byte e quella dell'altro, come sulla scheda.

```fish
python3 tools/emulator/fan_sim.py              # tutti gli scenari, circa 10 s
python3 tools/emulator/fan_sim.py switched     # uno solo
```

### Cosa prevede il modello

| Scenario | Cosa legge l'OS da `0x74-0x75` | Conseguenza |
|---|---|---|
| `linear`: driver lineare | Giri giusti entro il 3 % quando la velocità è stabile. Duty identico al firmware senza patch | La patch funziona |
| `pwm4`: ventola a 4 fili | Uguale | — |
| `switched`: alimentazione commutata, nessun filtro | Sotto il 100 % valori assurdi, fino a oltre un milione di giri/min, perché ogni periodo PWM dentro un impulso conta come un fronte. Giusti solo al 100 % | Con questo driver il tachimetro non serve senza un filtro, nel chip o nel firmware |
| `filter`: commutata, filtro da 30 µs | Giusti sopra il 60 % di duty, 0 sotto. Quando il duty scende, l'ultimo valore resta per circa 0,9 s | Il risultato dipende da un filtro che il datasheet non descrive |
| `no-tach`: tachimetro non collegato | Sempre 0, con la ventola che gira | — |
| `blocked`: ventola bloccata | Sempre 0, **identico** al tachimetro scollegato | Dal software non si distinguono: serve la misura |
| `no-start`: ventola che non parte al 13 % | A 42 °C la curva chiede 20/153 = 13 %. Duty sopra 0, giri 0, letto 0 | La patch rende visibile il difetto I8 |
| `sleep`: S3 dopo 15 s | Piedini bassi, ventola ferma, letto 0 | — |

**Letture spezzate.** In 600 letture per scenario né la patch né una copia semplice hanno mai pubblicato un valore che il registro non abbia avuto. La lettura I2EC dall'host lo ha fatto una volta, nel caso `switched`. Con impulsi da qualche millisecondo il rischio è basso. La doppia lettura costa poco e copre i casi rapidi.

### Cosa leggerebbe uno strumento sul connettore

Ventola stabile in modo manuale, finestra di 1 s. Tensione media e frequenza dei fronti, cioè quello che mostra un multimetro con la funzione Hz o un analizzatore logico:

| Ipotesi | Duty | Filo +V | Filo TACH | Filo PWM |
|---|---|---|---|---|
| `linear` | 50 % | 2,48 V, 0 Hz | 1,65 V, 84 Hz | — |
| `linear` | 100 % | 5,00 V, 0 Hz | 1,65 V, 167 Hz | — |
| `switched` | 50 % | 2,48 V, **20 kHz** | 2,48 V, raffiche a 20 kHz | — |
| `switched` | 100 % | 5,00 V, 0 Hz | 1,65 V, 167 Hz | — |
| `pwm4` | 50 % | 5,00 V, 0 Hz | 1,65 V, 84 Hz | 1,64 V, 20 kHz |
| `pwm4` | 100 % | 5,00 V, 0 Hz | 1,65 V, 167 Hz | 3,30 V, 0 Hz |

Il riconoscimento si fa sotto il 100 %. Al 100 % le tre ipotesi danno la stessa lettura sul tachimetro.
- **Frequenza sul filo +V:** 20 kHz vuol dire alimentazione commutata.
- **Tensione media sul filo +V:** se cambia col carico ma la frequenza resta 0, il driver è lineare.
- **Filo TACH:** la frequenza segue i giri, a 2 impulsi per giro. Le raffiche a 20 kHz confermano la commutazione.

### Limiti

- La ventola è lineare e senza inerzia del sensore. Una ventola vera ha una curva giri-duty diversa e una soglia di avvio da misurare (3.5).
- Il contatore ITE è modellato dalla formula del datasheet. Timeout, filtro e comportamento senza impulsi sono ipotesi.
- Il modello termico serve solo a muovere la curva come nella prova reale, non a prevedere le temperature.
- La lettura I2EC "non garantita" è modellata solo come ritardo tra i due byte. Altri effetti del chip non sono noti.

## 8.8 Patch per il controllo dall'host

`tools/emulator/host_ctl.py` prova, **solo in memoria** su `all-keys`, una patch che permette all'OS di chiedere un duty senza i difetti del modo manuale di fabbrica ([4.6](4-ventola-acpi.md#46-rischi)). Comprende il tachimetro della 8.6. Dall'ACPI la usa la SSDT di [4.7](4-ventola-acpi.md#47-ssdt-ventola-acpi-40).

**Protocollo.** L'host scrive con il comando `0x81`, prima la richiesta e poi il timer:

| Offset | Contenuto |
|---|---|
| `0xC9` | Duty richiesto, 0-152 (152 = 100 %) |
| `0xCA` | Timer: 0 spento, 1-254 decimi di secondo, 255 senza scadenza |

**Regole nell'EC:**

| Caso | Obiettivo |
|---|---|
| Timer a 0 | La curva, identica a quella di fabbrica |
| Timer attivo, temperatura sotto 85 °C | La richiesta, sia sotto sia sopra la curva |
| Timer attivo, 85 °C o più | Il più alto tra richiesta e curva: oltre gli 80 °C la curva vale 152 |
| Il timer arriva a 0 | Di nuovo la curva: se l'OS si blocca, l'EC riprende la ventola |
| Sospensione o spegnimento | Timer azzerato: al risveglio vale la curva finché l'host non riscrive |

Il firmware resta nel suo modo a curva (`0x10`): la patch cambia solo l'obiettivo che la curva scrive, prima della rampa. Il modo manuale `0x90` di fabbrica resta com'era.

**Modifica.** 132 byte a `0x5660`, tachimetro compreso, e due punti cambiati:

| Dove | Prima | Dopo |
|---|---|---|
| `0xB60B` | `LCALL 0xBC14` | Task ventola, tachimetro, poi il timer: azzerato se `0xCE90` dice spento, altrimenti meno uno a ogni giro da 100 ms, tranne che a 255 |
| `0xBB36` | `LCALL 0xBC6D`, scrittura di `0x65` | Salta alla routine che sceglie tra richiesta e curva, scrive l'obiettivo e torna a `0xBB3C` |

`0xCE90` e `0xCE71` leggono soltanto, quindi chiamarle una seconda volta non cambia nulla.

**Scelta degli offset.** Su tutti i 256 offset, solo 11 sono a 0 nella RAM del 17 ottobre e non compaiono né come accesso diretto, né come costante nel codice, né come campo del DSDT. `0xC9-0xCA` è una delle due coppie contigue. `0x79` sembrava libero ma non lo è: `0xC1C5` copia in `0x78-0x79` un valore a 16 bit da `0x0504`. I criteri delle costanti danno anche falsi positivi, per questo il tachimetro resta in `0x74-0x77`, dove nessuno scrive.

### Verifiche fatte

| Prova | Risultato |
|---|---|
| Senza richiesta, 8 temperature da 30 a 95 °C | Obiettivo identico al firmware di fabbrica |
| Richiesta 30 a 70 °C, 140 a 30 °C | 30 e 140: l'host può abbassare e alzare |
| Richiesta 30 a 84 e 85 °C | 30, poi 152 |
| Secondo canale | Segue la richiesta |
| Timer da 5 decimi | Scende, poi l'obiettivo torna alla curva (120 a 70 °C) |
| Timer 255, 300 giri | Non scade |
| Sospensione | Timer azzerato, al risveglio la curva |
| Timer scritto a 0 dall'host | Torna la curva |
| Scritture via `0xD90E`, il percorso reale del comando `0x81` | Arrivano a `0xC9` e `0xCA` |
| Tachimetro, tastiera, scritture all'avvio | Come in 8.6 |

**Nel simulatore 8.7**, con il carico della prova del 7 novembre:

| Scenario | Risultato |
|---|---|
| L'OS chiede il 26 % senza scadenza | Sotto 85 °C l'obiettivo è 40. Per 21 s sopra 85 °C passa a 152. Massimo 97 °C, contro 96 °C con la curva di fabbrica |
| L'OS rinnova un timer da 3 s chiedendo 20, poi si blocca a 20 s | Dopo 3 s l'obiettivo torna alla curva, 100-120 |
| Richiesta 60 senza scadenza, sospensione da 10 a 15 s | Dopo il risveglio, curva |
| Stessa sospensione con il modo manuale di fabbrica | Obiettivo 0 e ventola ferma dopo il risveglio, con la CPU a 70 °C: è il difetto che la patch evita |
| L'OS chiede il 100 % a riposo | Duty 100 %, tachimetro a 5000 giri/min |

### Limiti

- Con 255 un blocco dell'OS lascia la richiesta attiva fino alla sospensione. Protegge solo la soglia degli 85 °C. Per un servizio che rinnova il timer conviene un valore a tempo.
- Il driver `acpi-fan` di Linux chiama `_FSL` solo quando cambia stato, quindi non rinnova un timer: per questo la SSDT usa 255.
- La soglia di 85 °C è una costante nel codice (`SAFE_C`). La temperatura è quella che usa la curva, aggiornata circa una volta al secondo. Con un errore PECI vale 110 °C (L3), quindi la ventola va al massimo.
- Hook a `0xB60B` e `0xBB36` anche in `fan_fix.py`: una patch finale deve unire le due, con l'isteresi prima della scelta tra richiesta e curva.
- Valgono i limiti delle 8.5 e 8.6 per il flash.
