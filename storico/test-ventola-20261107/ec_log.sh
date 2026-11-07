#!/usr/bin/env bash
# Sola lettura: registra lo spazio EC e coretemp a riposo, sotto carico e in raffreddamento.
# Non abilita write_support. Si ferma da solo se coretemp arriva a 95 °C.
set -u
[[ $EUID -eq 0 ]] || { echo "Serve root"; exit 1; }
OUT=$(dirname "$(readlink -f "$0")")
CSV=$OUT/ec-log.csv
IO=/sys/kernel/debug/ec/ec0/io
HW=$(grep -lx coretemp /sys/class/hwmon/hwmon*/name | head -1 | xargs dirname)
PIDS=()
stop_load() { ((${#PIDS[@]})) && kill "${PIDS[@]}" 2>/dev/null; PIDS=(); }
cleanup() { stop_load; [[ ${LOADED:-0} == 1 ]] && modprobe -r ec_sys; }
trap cleanup EXIT INT TERM
LOADED=0
if ! lsmod | grep -q '^ec_sys'; then modprobe ec_sys || exit 1; LOADED=1; fi
[[ -r $IO ]] || { echo "Manca $IO"; exit 1; }
dd if=$IO of="$OUT/ec-inizio.bin" bs=256 count=1 status=none
echo "t,fase,coretemp,ec70,usata42,obiettivo44,obiettivo45,duty46,duty47,modo40,modo41" > "$CSV"
T=0
sample() {
  local c b
  c=$(($(cat "$HW/temp1_input") / 1000))
  b=($(dd if=$IO bs=1 skip=64 count=52 status=none | od -An -tu1 -v))
  echo "$T,$1,$c,${b[48]},${b[2]},${b[4]},${b[5]},${b[6]},${b[7]},${b[0]},${b[1]}" | tee -a "$CSV"
  T=$((T + 1))
  ((c < 95))
}
for i in $(seq 60); do sample riposo || break; sleep 1; done
for i in $(seq "$(nproc)"); do (while :; do :; done) & PIDS+=($!); done
for i in $(seq 120); do sample carico || { echo "95 °C: carico fermato"; break; }; sleep 1; done
stop_load
for i in $(seq 90); do sample raffreddamento; sleep 1; done
dd if=$IO of="$OUT/ec-fine.bin" bs=256 count=1 status=none
chmod 644 "$CSV" "$OUT"/ec-inizio.bin "$OUT"/ec-fine.bin
chown "${SUDO_UID:-0}:${SUDO_GID:-0}" "$CSV" "$OUT"/ec-inizio.bin "$OUT"/ec-fine.bin
echo "Fatto: $CSV"
