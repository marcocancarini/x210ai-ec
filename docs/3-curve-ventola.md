# Parte 3: Curve della ventola

**La curva della ventola è nell'EC, non nel BIOS.** Il firmware EC legge la temperatura della CPU, la confronta con una tabella a 8 punti e pilota direttamente le uscite PWM. Nel firmware `V0.4.0` la tabella è scritta come costanti e ricopiata in RAM all'avvio dell'EC.

**Da dove vengono i dati:** codice di `dumps/ec/EC-V0.4.0-20250723-lettura1.bin`, RAM EC del 2026-10-17 e prove sul codice reale nell'emulatore. In `all-keys` queste routine sono identiche. **Niente è stato misurato sulla ventola:** niente giri, rumore o temperature sotto carico. Come cambiarla: [parte 4](4-ventola-acpi.md).

## 3.1 Il percorso nel firmware

| Passo | Dove | Cosa fa |
|---|---|---|
| Temperatura | `0xDEB3-0xDF2F` | Calcola la temperatura della CPU come TjMax meno uno scostamento in 1/64 °C, nello stile di PECI GetTemp, e la salva in xdata `0x9550`. TjMax vale 110 °C (`0x6E`) di default, oppure il valore letto in `0x9628`. Il dato arriva da PECI GetTemp su eSPI OOB ([8.1](8-ventole-firmware.md#81-la-catena-completa)), circa ogni 1,8 s. **Se la lettura fallisce, `0x9550` conserva il valore precedente** |
| Copia nello spazio ACPI | `0xBC02` | Copia `0x9550` in `0x0470`, cioè l'offset `0x70` dello spazio EC visto da `0x62/0x66`. Succede circa una volta al secondo |
| Curva | `0xB9E9-0xBB3B` | Per ciascuno dei due canali sceglie la sorgente (offset `0x70-0x73`), cerca la soglia più alta non superata e salva il duty obiettivo |
| Rampa e uscita | `0xBB3C-0xBC01` | Porta il duty attuale verso l'obiettivo a passi di 1, lo limita a CTR1 e lo scrive in DCR0 (`0x1802`) o DCR1 (`0x1803`) |
| Accensione e spegnimento | `0xBC14`, `0xB98F`, `0xB9BB` | Se `0xCE90` restituisce 0 azzera obiettivo e temperatura e mette i piedini PWM0/PWM1 (GPA0/GPA1, `GPCRA0/1` a `0x1610/0x1611`) come GPIO bassi. Altrimenti li riporta alla funzione PWM |
| Valori iniziali | `0xB841`, da `0xBC0E` | Scrive modo, isteresi e tabella in `0x0440-0x046D`. Una sola chiamata, nell'inizializzazione `0xDBE5` eseguita all'avvio dell'EC (`0x04A8`) |

**`0xCE90`** restituisce 1 solo se XRAM `0x00B0` vale 1, probabilmente lo stato S0, e `0xCE71` restituisce 0. `0xCE71` tiene ferma la ventola se `0x04FB` (offset EC `0xFB`) vale 1 o se il contatore `0x00C2` non è a zero. A cosa servano quei due campi non è decodificato.

**Tempi.** Il loop è chiamato da `0x0F1B`, in una cascata di contatori a `0x0EBC`: 5 tick, poi 10 (`0x44`), 20 (`0x45`) e 60 (`0x47`). Se il tick è da 1 ms, come suggerisce l'ultimo stadio da 60, i gradini sono 5 ms, 50 ms, 1 s e 1 min. Il loop gira ogni 100 tick, **circa 100 ms**. Il periodo del tick non è stato letto dalla configurazione del timer, ma la rampa misurata sulla scheda, circa 10 conteggi al secondo, lo conferma.

**Registri PWM** (tabella di init a `0x3308`):

| Registro | Valore | Significato |
|---|---|---|
| `CTR1` `0x1841` | `0x98` = 152 | Periodo. Il duty è `DCR/(CTR+1)` e con `DCR = CTR` l'uscita resta alta (datasheet IT5570, sezione 7.12), quindi `0x98` vale 100 % |
| `PCSSGL` `0x180C` | `0x05` | Canali 0 e 1 sul gruppo 1, con prescaler C4 e CTR1 |
| `CLK6MSEL` `0x1840`, `PCFSR` `0x180B` | `0x0E`, `0x00` | Clock del gruppo 1 = 6,14 MHz |
| `C4CPRS` `0x1827` | `0x01` | Divisore 2 |

La frequenza PWM è quindi 6,14 MHz / (2 × 153) ≈ **20 kHz**, ricavata dai registri e dal datasheet IT5570, non misurata.

Non c'è nessun accesso diretto ai registri del tachimetro (`0x181E-0x1821`): i piedini sono configurati come tachimetro ([5.5](5-hardware.md#55-ventola)), ma il firmware non legge i giri.

## 3.2 Struttura nello spazio EC

I due canali sono intercalati: canale 0 agli offset pari, canale 1 a quelli dispari. Offset relativi all'inizio dello spazio EC (xdata `0x0400`):

| Offset | Campo | Valore di fabbrica |
|---|---|---|
| `0x40/0x41` | Modo, vedi [3.3](#33-comportamento-verificato) | `0x10` |
| `0x42/0x43` | Temperatura usata | — |
| `0x44/0x45` | Duty obiettivo | — |
| `0x46/0x47` | Duty attuale | — |
| `0x4A/0x4B` | Isteresi sotto la prima soglia, senza effetto ([3.3](#33-comportamento-verificato)) | 2 |
| `0x4C/0x4D` | Divisori della rampa: nibble basso salita, nibble alto discesa | 0 |
| `0x4E-0x6D` | 8 coppie soglia/duty | Tabella sotto |
| `0x70` | Temperatura CPU | Aggiornata dall'EC |
| `0x71` | Sorgente 1: il firmware la legge e non la scrive | 0 |
| `0x72/0x73` | Sorgenti 2 e 3: il firmware le azzera soltanto (`0xC6BF`) | 0 |
| `0x7B` | Se vale 0, il bit 0 della sorgente viene tolto: 1 diventa 0, 3 diventa 2 | 0 |

| Temperatura CPU | 40 °C | 45 °C | 50 °C | 55 °C | 60 °C | 70 °C | 75 °C | 80 °C |
|---|---|---|---|---|---|---|---|---|
| Duty (su 152) | 20 | 40 | 60 | 80 | 100 | 120 | 140 | 152 |
| Duty in % | 13 | 26 | 39 | 52 | 65 | 78 | 92 | 100 |

Sotto i 40 °C l'obiettivo è 0, cioè ventola ferma. Entrambi i canali usano la stessa sorgente e la stessa tabella. Quante ventole siano davvero collegate non si sa: lo chassis X200/X201 ne ha una.

**RAM EC del 2026-10-17** (`storico/diagnostica-20261017/ec_ram.bin`): la tabella è identica ai valori di fabbrica su entrambi i canali, ma `0x70` vale `0x64` (100 °C) e il duty attuale è `0x98` (100 %) su entrambi. Le ipotesi sono tre: la CPU era davvero a 100 °C durante la diagnostica, la temperatura arrivava sbagliata, oppure era un valore vecchio rimasto dopo una lettura fallita. Si controlla con la prova di [4.4](4-ventola-acpi.md#44-prova-in-sola-lettura).

## 3.3 Comportamento verificato

Queste prove eseguono le routine reali con l'emulatore: `python3 tools/emulator/fan_check.py`. Provano la logica del firmware, non quello che fa la ventola.

**Modo** (`0x40/0x41`):

| Bit | Effetto |
|---|---|
| 0-3 | Sorgente della temperatura: `0x70+n` |
| 4-6 = 1 | PWM con rampa verso l'obiettivo. **È il valore di fabbrica** |
| 4-6 = 0 | Il piedino diventa GPIO alto: ventola al massimo, qualunque sia il duty |
| 4-6 = altro | PWM, ma il duty resta fermo dov'è |
| 7 | La curva non viene calcolata: l'obiettivo resta quello scritto in `0x44/0x45` |

| Valore | Risultato | Provato |
|---|---|---|
| `0x10` | Curva con rampa | Sì |
| `0x90` | **Manuale:** obiettivo scritto a mano, rampa attiva | Sì, 30 su 30 |
| `0x12` | Curva, con la temperatura scritta dall'host in `0x72` | Sì, 50 °C → 60 |
| `0x00`, `0x80` | Massimo, tramite GPIO | Dal codice: l'emulatore mostra solo il duty fermo |
| `0x20` | Duty fermo | Sì |

**Rampa.** Un passo per chiamata: 152 chiamate da 0 a 100 %, circa 15 s, e altrettante in discesa. Ogni direzione ha un divisore a 2 bit nei bit 2-3 del proprio nibble: `0x04`, `0x08` e `0x0C` rallentano la salita di 2, 3 e 4 volte, `0x40`, `0x80` e `0xC0` la discesa. I bit 0-1 sono il contatore e l'EC li riscrive.

**Isteresi senza effetto.** Il codice a `0xBB13-0xBB35` vuole tenere la ventola accesa fino a `soglia - isteresi`, ma nel ramo che dovrebbe conservare il valore non legge il duty precedente: resta in `0x65` il numero della sorgente, cioè 0. Con la sorgente di fabbrica il risultato è 0 in entrambi i casi. Nell'emulatore l'obiettivo a 39 °C vale 0 anche partendo da 45 °C, con isteresi 2 e con isteresi 10.

**Spegnimento.** `0xB98F` azzera l'obiettivo quando `0xCE90` restituisce 0. In modo curva l'obiettivo viene ricalcolato al rientro; in modo manuale resta 0 e la ventola non riparte ([4.6](4-ventola-acpi.md#46-rischi)).

## 3.4 Valutazione

Una valutazione ricavata dalla logica. Ogni punto andrà confermato con le misure di [3.5](#35-cosa-misurare).

| Punto | Cosa succede | Conseguenza |
|---|---|---|
| **Gradini** | Niente interpolazione: l'obiettivo salta di 20 conteggi (13 %) a ogni soglia, e la rampa lo distribuisce in circa 2 s | Cambi di velocità percepibili |
| **Nessuna isteresi** | Con la temperatura a cavallo di una soglia l'obiettivo oscilla a ogni lettura, circa ogni 1,8 s | Probabile pendolamento, soprattutto a 40 °C tra fermo e 13 %. La rampa lo attenua poco: in quel tempo copre quasi un gradino |
| **Uso leggero** | Misurato a riposo: temperatura EC 49-57 °C, obiettivo 40-60, duty intorno al 39 % ([8.2](8-ventole-firmware.md#82-problemi-delle-letture)) | La ventola non si ferma mai, e oscilla tra il 26 e il 44 % circa |
| **Massimo a 80 °C** | Il 100 % arriva 30 °C sotto TjMax (110 °C). Misurato: con il carico stabile a PL1 la temperatura resta a 74-79 °C e il duty al 92 % | Prudente e rumorosa: con carico lungo la ventola sta quasi al massimo |
| **Buco a 65 °C** | Tra 60 e 70 °C il passo è di 10 °C, altrove di 5 °C | Innocuo: zona piatta al 65 % |
| **Rampa simmetrica** | Salita e discesa uguali | Il divisore di discesa è già nel firmware, ma non usato. Basterebbe `0xC0` in `0x4C/0x4D` per ridurre il pendolamento |
| **Nessun avvio forzato** | Da fermo sale di un conteggio alla volta e si ferma al 13 % se la temperatura resta bassa | Se la ventola non parte al 13 %, tra 40 e 45 °C resta ferma. Dipende dal modello |
| **Una sola sorgente** | Solo la CPU: VRM, SSD e scocca non contano | Limite noto, nessun rimedio senza nuove sorgenti |
| **Nessun tachimetro** | Una ventola bloccata non viene rilevata | Nessun allarme |
| **Duty 20 kHz** | Sopra la soglia dell'udibile | Va bene per una ventola PWM. Va verificato se la ventola sia a 3 o 4 fili ([5.5](5-hardware.md#55-ventola)) |

**Sintesi.** La curva è prudente: protegge la CPU e fa rumore prima del necessario. I difetti reali sono l'isteresi inattiva e il duty alto già con carichi leggeri. Entrambi sono rimediabili senza hardware: dall'OS ([parte 4](4-ventola-acpi.md)) o nel firmware ([parte 8](8-ventole-firmware.md)).

**Punto di partenza per una curva più silenziosa.** Non è una raccomandazione: i numeri vanno adattati alla soglia di avvio e alle temperature misurate.

| Temperatura CPU | 50 °C | 55 °C | 60 °C | 65 °C | 70 °C | 75 °C | 80 °C | 85 °C |
|---|---|---|---|---|---|---|---|---|
| Duty (su 152) | 20 | 30 | 40 | 55 | 75 | 100 | 125 | 152 |

## 3.5 Cosa misurare

| Misura | Come | Serve per |
|---|---|---|
| Temperatura EC contro `coretemp`, a riposo e sotto carico | [4.4](4-ventola-acpi.md#44-prova-in-sola-lettura), sola lettura | Sapere quale punto della curva è in uso e chiudere il caso dei 100 °C |
| Duty attuale a riposo | Offset `0x46/0x47`, sola lettura | Confermare la stima sull'uso leggero |
| Regime stabile con carico fisso | Offset `0x42`, `0x46` e `coretemp`, ogni secondo per 10 minuti | Vedere se pendola e dove si assesta |
| Duty minimo di avvio e di tenuta | Scrittura dello spazio EC, [4.5](4-ventola-acpi.md#45-prova-in-scrittura) | Primo punto utile della curva |
| Giri rispetto al duty | Tachimetro o oscilloscopio, [6.1](6-modifiche-hardware.md#61-misure-mancanti) | Curva reale |
| Rumore rispetto al duty | Fonometro o app del telefono, stessa posizione | Scegliere i punti della nuova curva |
