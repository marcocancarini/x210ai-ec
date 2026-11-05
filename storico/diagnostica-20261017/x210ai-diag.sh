#!/usr/bin/env bash
# x210ai-diag.sh — raccolta informazioni su BIOS / EC / tastiera dell'X210Ai
# SOLO LETTURA: non scrive nulla su flash SPI, EC o variabili UEFI.
# Uso:   sudo bash x210ai-diag.sh
# Alla fine produce un archivio x210ai-diag-<data>.tar.gz da conservare con i risultati.

set -u

if [[ $EUID -ne 0 ]]; then
  echo "Esegui con sudo:  sudo bash $0"
  exit 1
fi

OUT="x210ai-diag-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
LOG="$OUT/riepilogo.txt"
say() { echo -e "$*" | tee -a "$LOG"; }

# --- 0. Strumenti -----------------------------------------------------------
declare -A PKG=( [flashrom]=flashrom [rdmsr]=msr-tools [acpidump]=acpica
                 [dmidecode]=dmidecode [evtest]=evtest )
missing=()
for c in "${!PKG[@]}"; do command -v "$c" >/dev/null || missing+=("${PKG[$c]}"); done
if ((${#missing[@]})); then
  echo "Mancano alcuni pacchetti. Installali con:"
  echo "  sudo pacman -S --needed ${missing[*]}"
  read -rp "Continuo comunque con quello che c'è? [s/N] " a
  [[ ${a:-n} == [sSyY] ]] || exit 1
fi

say "== Diagnostica X210Ai — $(date)"
say "Kernel: $(uname -r)"
say "Kernel lockdown: $(cat /sys/kernel/security/lockdown 2>/dev/null || echo n/d)"
say "(se lockdown è [integrity] o [confidentiality], flashrom e rdmsr verranno bloccati:"
say " disattiva temporaneamente Secure Boot e rilancia)"

# --- 1. DMI -----------------------------------------------------------------
if command -v dmidecode >/dev/null; then
  dmidecode -t bios -t system -t baseboard > "$OUT/dmi.txt" 2>&1
  say "\n== Firmware"
  say "BIOS:   $(dmidecode -s bios-vendor) $(dmidecode -s bios-version) ($(dmidecode -s bios-release-date))"
  say "Scheda: $(dmidecode -s baseboard-manufacturer) $(dmidecode -s baseboard-product-name)"
fi

# --- 2. Boot Guard (MSR 0x13A) ----------------------------------------------
if command -v rdmsr >/dev/null; then
  modprobe msr 2>/dev/null
  say "\n== Boot Guard (interpretazione indicativa, la verifico poi sull'immagine)"
  if v=$(rdmsr -p0 -c 0x13a 2>&1); then
    say "MSR 0x13A = $v"
    (( (v>>32) & 1 )) && say "  - la CPU supporta Boot Guard"
    (( (v>>5)  & 1 )) && say "  - Measured Boot attivo"
    (( (v>>6)  & 1 )) && say "  - VERIFIED BOOT ATTIVO -> la regione BIOS NON va modificata"
    (( (v & 0x7f) == 0 )) && say "  - nessun bit di policy impostato: Boot Guard probabilmente non applicato"
  else
    say "MSR 0x13A non leggibile: $v"
  fi
fi

# --- 3. Tabelle ACPI (per capire come l'EC parla col sistema) ---------------
if command -v acpidump >/dev/null; then
  acpidump > "$OUT/acpi.dat" 2>/dev/null && say "\nTabelle ACPI salvate (acpi.dat)"
fi

# --- 4. Flash SPI: identificazione e backup in sola lettura -----------------
if command -v flashrom >/dev/null; then
  say "\n== Flash SPI (flashrom, sola lettura)"
  flashrom -p internal --flash-name > "$OUT/flashrom-probe.txt" 2>&1
  grep -Ei 'found|FREG|region|chip|warning|error' "$OUT/flashrom-probe.txt" | tee -a "$LOG"

  if flashrom -p internal --ifd -i bios -r "$OUT/bios_region.bin" > "$OUT/flashrom-bios.txt" 2>&1; then
    say "Regione BIOS letta -> bios_region.bin"
  else
    say "Lettura regione BIOS fallita (vedi flashrom-bios.txt)"
  fi

  if flashrom -p internal -r "$OUT/full_dump.bin" > "$OUT/flashrom-full.txt" 2>&1; then
    say "Flash completa letta -> full_dump.bin"
  else
    say "Lettura completa fallita (normale se la regione ME è bloccata in lettura)"
  fi

  if grep -qs 'iomem=relaxed' "$OUT"/flashrom-*.txt; then
    say "!! flashrom chiede il parametro kernel iomem=relaxed: aggiungilo una tantum al boot e rilancia"
  fi
fi

# --- 5. EC ------------------------------------------------------------------
say "\n== Embedded Controller"
if modprobe ec_sys 2>/dev/null && [[ -r /sys/kernel/debug/ec/ec0/io ]]; then
  dd if=/sys/kernel/debug/ec/ec0/io of="$OUT/ec_ram.bin" bs=256 count=1 2>/dev/null \
    && say "RAM dell'EC salvata (ec_ram.bin) — solo lettura, write_support resta disattivato"
else
  say "ec_sys non disponibile: salto la RAM dell'EC"
fi
if command -v superiotool >/dev/null; then
  superiotool > "$OUT/superiotool.txt" 2>&1
  grep -i 'found' "$OUT/superiotool.txt" | tee -a "$LOG"
else
  say "superiotool non installato (facoltativo, dall'AUR): servirebbe a leggere il modello del chip EC"
fi

# --- 6. Tastiera: cosa arriva davvero al sistema ----------------------------
cat /proc/bus/input/devices > "$OUT/input-devices.txt"
KBD=/dev/input/by-path/platform-i8042-serio-0-event-kbd
if [[ -e $KBD ]] && command -v evtest >/dev/null; then
  say "\n== Test tasti"
  echo
  echo "Per 20 secondi registro i tasti. Premi, lentamente, uno alla volta:"
  echo "  1) Fn da solo, 3 volte"
  echo "  2) Ctrl sinistro, 3 volte"
  echo "  3) Fn+F5, Fn+F6 (o un'altra combinazione Fn che usi)"
  echo "  4) se è montata la tastiera ISO: il tasto <> accanto a Shift sinistro,"
  echo "     il tasto subito a sinistra di Invio, e qualsiasi tasto che non risponde"
  read -rp "Invio per iniziare... "
  before=$(dmesg | wc -l)
  timeout 20 evtest "$KBD" > "$OUT/evtest.txt" 2>&1 &
  if command -v libinput >/dev/null; then
    timeout 20 libinput debug-events --show-keycodes > "$OUT/libinput.txt" 2>&1 &
  fi
  wait
  dmesg | tail -n +"$((before + 1))" | grep -iE 'atkbd|unknown key' > "$OUT/dmesg-tasti.txt"
  say "Eventi tastiera registrati: $(grep -c 'EV_KEY' "$OUT/evtest.txt")"
  [[ -s "$OUT/dmesg-tasti.txt" ]] && tee -a "$LOG" < "$OUT/dmesg-tasti.txt"
else
  say "Tastiera i8042 non trovata o evtest mancante: vedi input-devices.txt"
fi

# --- 7. Archivio -------------------------------------------------------------
OWNER="${SUDO_USER:-root}"
tar czf "$OUT.tar.gz" "$OUT"
chown -R "$OWNER": "$OUT" "$OUT.tar.gz"
say "\nFatto. Archivio creato: $OUT.tar.gz"
say "e anche il file MTLH-NB06_B0.2.bin del pacchetto BIOS del produttore."
