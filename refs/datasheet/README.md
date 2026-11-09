# Estratti del datasheet IT5570

Ci sono solo le pagine usate nell'analisi, non il documento intero. Sono prese da `IT5570_A_V0.3.1_U.pdf` (ITE, *IT5570 (For A Version)* V0.3.1, 575 pagine). L'hash del PDF completo è in [`../DATASHEETS.md`](../DATASHEETS.md). Il file prende il nome dal numero di pagina del PDF. Il numero stampato a piè di pagina è più basso di 32.

| Pagina | Contenuto | Usata per |
|---|---|---|
| [38](it5570/p038.png) | §3.2 EC Mapped Memory Space | Mappa dei registri: SMFI `1000h`, INTC `1100h`, EC2I `1200h`, Bank `1300h`, double-map `8000h` |
| [43](it5570/p043.png) | Table 4-1, piedini LQFP-128 in ordine numerico | Piedini del chip sulla scheda |
| [46](it5570/p046.png) | Table 5-5 FSPI, Table 5-6 SSPI | Connettore EC_SPI1 |
| [49](it5570/p049.png) | Table 5-19 porta parallela, Table 5-20 GPIO | ISP dal connettore tastiera, GPG2 |
| [50](it5570/p050.png) | Table 5-21 strap hardware | Ingresso in DBGR/EPP e test mode |
| [65](it5570/p065.png) | eSPI, Master Attached Flash Sharing | Flash condivisa host↔EC |
| [150](it5570/p150.png) | §6.4.3.11.1 16B-signature | Firma all'inizio del firmware |
| [151](it5570/p151.png) | §6.4.3.11.2 sequenza di rilevamento | Firma all'inizio del firmware |
| [152](it5570/p152.png) | §6.4.4 Table 6-29, registri SMFI lato EC | FLHCTRL1R/2R, ECINDAR, P0BA0R/P0BA1R |
| [155](it5570/p155.png) | §6.4.4.5-6 FLHCTRL1R, FLHCTRL2R | Scrittura della flash |
| [158](it5570/p158.png) | §6.4.4.17-18 P0BA0R, P0BA1R | Zone protette della flash |
| [159](it5570/p159.png) | P0ZR, dimensione della zona protetta | Zone protette della flash |
| [172](it5570/p172.png) | §6.4.4.51-52 FLHCTRL5R/6R | Sorgente del code fetch |
| [189](it5570/p189.png) | §6.6 KBC | Porte `60h/64h`, IRQ1/IRQ12 |
| [192](it5570/p192.png) | Table 6-34, registri KBC lato EC | KBHICR, KBHISR, KBHIKDOR |
| [263](it5570/p263.png) | §7.4 Keyboard Matrix Scan | Matrice 18×8 |
| [264](it5570/p264.png) | Registri KBS, base `1D00h` | KSOL, KSIR, KSICTRLR |
| [266](it5570/p266.png) | §7.4.4.6 KSICTRLR | Bit OVRPPK, disattiva DBGR/EPP |
| [278](it5570/p278.png) | §7.5 GPIO | Base `1600h` |
| [295](it5570/p295.png) | §7.5.3.28 GPCRn | Modo dei piedini GPIO |
| [357](it5570/p357.png) | §7.7.4.26 SLVISELR | Bit OVRSMDBG, disattiva DBGR/SMB |
| [512](it5570/p512.png) | §7.21.5 registri SSPI | Base `2600h` |
| [530](it5570/p530.png) | §7.23 DBGR, §7.23.3.2 DBGR/SMB | ISP e debug |
| [532](it5570/p532.png) | §7.24.3.1 KBS e porta parallela | Collegamento DB25 per l'ISP |
| [569](it5570/p569.png) | Dimensioni LQFP-128 | Corpo 14×14 mm, passo 0,40 mm |
