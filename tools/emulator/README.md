# Emulatore 8051

Esegue il **codice macchina reale** del firmware EC su Python, istruzione per istruzione, senza toccare la scheda. Serve a provare una routine, o una patch, prima di flasharla. Non ha dipendenze esterne.

| File | Cosa fa |
|---|---|
| `cpu8051.py` | La CPU: registri, memorie, banchi e tutte le istruzioni |
| `selftest.py` | 23 programmi minimi che controllano le istruzioni della CPU emulata |
| `run_tests.py` | Prove della tastiera sulle immagini in `firmware/patched/` |
| `fan_check.py` | Prove della ventola sul firmware così com'è |
| `fan_fix.py` | Correzioni proposte alla ventola, applicate solo in memoria |
| `tach_read.py` | Patch del solo tachimetro, applicata solo in memoria ([8.6](../../docs/8-ventole-firmware.md#86-patch-del-tachimetro)) |
| `asm8051.py` | Assembler minimo con etichette, usato dalle patch |
| `fan_plant.py` | Modello dell'hardware della ventola: PWM, driver, ventola, linea e contatore del tachimetro, temperatura |
| `host_ctl.py` | Patch per il controllo dall'host con timer e soglia a 85 °C, provata anche nel simulatore ([8.8](../../docs/8-ventole-firmware.md#88-patch-per-il-controllo-dallhost)) |
| `fan_sim.py` | Task ventola reale ogni 100 ms dentro `fan_plant.py`, con gli scenari di [8.7](../../docs/8-ventole-firmware.md#87-simulatore-dellhardware-della-ventola) |

```fish
python3 tools/emulator/selftest.py
python3 tools/emulator/run_tests.py      # circa un minuto
python3 tools/emulator/fan_check.py
python3 tools/emulator/fan_fix.py
python3 tools/emulator/tach_read.py
python3 tools/emulator/fan_sim.py       # circa 10 s
python3 tools/emulator/host_ctl.py
```

## Come funziona la CPU

La classe `CPU` riceve l'immagine da 128 KiB e tiene lo stato del chip in pochi array:

| Campo | Cosa rappresenta |
|---|---|
| `rom` | L'immagine del firmware, di sola lettura |
| `iram` | 256 byte di RAM interna, compreso lo stack |
| `sfr` | Registri speciali da `0x80` a `0xFF`: `A`, `B`, `PSW`, `SP`, `DPTR`, `P1` |
| `x` | 64 KiB di XRAM, cioè RAM esterna **e registri delle periferiche** |
| `pc` | Prossima istruzione da eseguire |
| `hooks` | Funzioni Python da chiamare quando `pc` raggiunge un certo indirizzo |
| `xw` | Funzione facoltativa chiamata a ogni scrittura in XRAM |

**Il ciclo.** `step()` fa sempre le stesse cose:

1. Se `pc` ha un hook, lo esegue.
2. Legge un byte da `rom`: è il codice dell'istruzione.
3. Legge gli eventuali operandi.
4. Aggiorna registri, memoria e flag, come farebbe il chip.

Per esempio `74 28` è `MOV A,#0x28`: l'emulatore legge `0x74`, poi `0x28`, e scrive `0x28` in `sfr[0xE0]`, che è `A`. Con `F0`, cioè `MOVX @DPTR,A`, scrive `A` in `x[DPTR]`.

**I banchi.** Un 8051 vede solo 64 KiB, ma qui l'immagine è da 128 KiB. `code()` fa la stessa traduzione della scheda:

| Indirizzo | Si legge da |
|---|---|
| `0x0000-0x7FFF` | Stessa posizione del file: zona fissa |
| `0x8000-0xFFFF`, banco 0 | Offset `0x8000-0xFFFF` del file |
| `0x8000-0xFFFF`, banco 1 | Offset `0x10000-0x17FFF` |
| `0x8000-0xFFFF`, banco 2 | Offset `0x18000-0x1FFFF` |

Qui il banco è il valore di `P1`, quindi il "banco 0" è quello che [1.2](../../docs/1-dump-firmware.md#12-architettura-e-mappa-memoria) chiama banco 1, dove la zona fissa è il banco 0. Il banco sta nei bit 0-2 di `P1` (`sfr[0x90]`). Lo imposta il firmware, nelle routine a `0x2800`, quindi le chiamate fra banchi funzionano senza codice dedicato.

## Come si prova una routine

L'emulatore non fa girare il firmware intero. In genere una prova chiama una sola routine:

```python
def call(cpu, address, r7=None, r5=None):
    cpu.push(RETURN & 0xFF)          # finto indirizzo di ritorno, 0xDEAD
    cpu.push(RETURN >> 8)
    cpu.pc = address
    ...                              # argomenti in R7 e R5
    for _ in range(200000):
        if cpu.pc == RETURN:         # il RET della routine ci porta qui
            return
        cpu.step()
    raise RuntimeError('no return')
```

Si prepara la memoria come se il resto del firmware fosse già partito, si chiama la routine e si guarda cosa ha scritto. Così `fan_check.py` prova la curva:

```python
cpu = fresh(image)          # esegue il vero 0xB841, che carica la tabella
ec(cpu, TEMP, 55)           # offset EC 0x70 = 55 °C
call(cpu, 0xB9E9, r7=0)     # esegue la vera routine della curva, canale 0
print(ec(cpu, TARGET))      # stampa 80
```

Il limite di 200000 istruzioni ferma le prove che non tornano, per esempio un'attesa su un registro che nessuno cambia.

**Hook.** Sostituiscono una parte che non si può eseguire. La lettura PECI, per esempio, aspetterebbe una risposta dal PCH. Allora `fan_fix.py` mette un hook su `0xDF98`: scrive una risposta finta in `0x9625-0x9626`, imposta l'esito in `R7` e fa ritornare subito la routine. Tutto il resto del percorso, conversione compresa, è il codice vero.

**Osservare le scritture.** Con `cpu.xw` si registrano tutte le scritture in XRAM. `boot_writes()` parte da `pc = 0`, esegue 3 milioni di istruzioni dell'avvio e confronta le scritture di due immagini: una differenza inattesa si vede subito.

## Prove della tastiera

`run_tests.py` confronta ogni immagine patchata con il dump originale:

| Prova | Come funziona |
|---|---|
| Tutte le celle | Simula pressione e rilascio di ogni tasto, anche con Shift, Fn e Ctrl tenuti, e confronta gli scancode in uscita |
| Scambio Fn↔Ctrl | Controlla i due tasti fisici |
| Debounce di Fn | Passa dalla vera routine a `0xC4C8`, con lettura del piedino ripetuta |
| Ordine di rilascio | Lascia Fn prima o dopo il tasto, che deve dare lo stesso risultato |
| Sequenze casuali | 100 sequenze da 600 eventi, alla fine nessun tasto deve restare premuto |
| Scritture all'avvio | Diverse da quelle originali solo dove previsto |
| Errori inseriti | Rompe apposta `all-keys` in 15 modi: ogni errore deve essere trovato |

L'ultima prova controlla i test stessi: se un errore passasse, significherebbe che i test non lo vedono.

## Perché ci si può fidare

- `selftest.py` prova aritmetica, flag, salti, stack e banchi con risultati calcolati a parte.
- Il codice reale ha girato per milioni di istruzioni senza opcode sconosciuti.
- I risultati della tastiera sono stati poi confermati sulla scheda con `evtest`.

## Cosa non fa

| Manca | Conseguenza |
|---|---|
| **Periferiche** | I registri sono memoria semplice: un registro legge l'ultimo valore scritto. Nessun PWM, tachimetro, GPIO, eSPI o host. Vanno preparati a mano o con un hook |
| **Interrupt** | Nessuna routine di interrupt parte da sola. Il flusso degli eventi va chiamato dalla prova |
| **Timer e tempi** | Nessun cronometro: si contano le chiamate, non i secondi. I 100 ms della ventola sono dedotti, non misurati |
| **Boot ROM** | Parte da `pc = 0`, senza la ROM del chip. Non dice se il CRC viene controllato |
| **Scheda** | Niente cablaggio, alimentazione o ventola reale |

Quindi una prova superata dice che **la logica del firmware fa quello che ci aspettiamo con quegli ingressi**, non che la scheda si comporterà così. Una prova di `fan_check.py` dimostra che il duty arriva in `0x1802`, ma non che la ventola giri.

## Aggiungere una prova

1. Trovare la routine con `tools/i8051.py` e capire cosa legge e cosa scrive.
2. Preparare la memoria. Se la routine aspetta una periferica, mettere un hook.
3. Chiamarla con `call()`.
4. Controllare il risultato con `check()`, come in `fan_check.py`.
5. Se è una patch, rompere la patch apposta e controllare che la prova fallisca.
