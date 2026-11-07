#!/usr/bin/env bash
# Sola lettura: temperatura EC e duty ogni 5 s, a riposo, con 5 minuti di carico e in raffreddamento.
# Non abilita write_support. Ferma il carico se coretemp resta oltre 100 °C per 10 s di fila.
set -u
[[ $EUID -eq 0 ]] || { echo "Serve root"; exit 1; }
OUT=$(dirname "$(readlink -f "$0")")
CSV=$OUT/ec-log2.csv
IO=/sys/kernel/debug/ec/ec0/io
HW=$(grep -lx coretemp /sys/class/hwmon/hwmon*/name | head -1 | xargs dirname)
PIDS=()
LOADED=0
stop_load() { ((${#PIDS[@]})) && kill "${PIDS[@]}" 2>/dev/null; PIDS=(); }
cleanup() {
  stop_load
  [[ $LOADED == 1 ]] && modprobe -r ec_sys
  [[ -f $CSV ]] && chown "${SUDO_UID:-0}:${SUDO_GID:-0}" "$CSV"
}
trap cleanup EXIT
trap 'exit 1' INT TERM
if ! lsmod | grep -q '^ec_sys'; then modprobe ec_sys || exit 1; LOADED=1; fi
[[ -r $IO ]] || { echo "Manca $IO"; exit 1; }
THROTTLE=/sys/devices/system/cpu/cpu0/thermal_throttle/package_throttle_count
freq() { cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq | awk '{s+=$1} END {printf "%d", s/NR/1000}'; }
echo "s,fase,coretemp,ec70,usata42,obiettivo44,duty46,mhz,throttle" > "$CSV"
HOT=0
T=0
tick() {
  local c b t70
  c=$(($(cat "$HW/temp1_input") / 1000))
  if ((c > 100)); then HOT=$((HOT + 1)); else HOT=0; fi
  if ((T % 5 == 0)); then
    b=($(dd if=$IO bs=1 skip=66 count=5 status=none | od -An -tu1 -v))
    t70=$(dd if=$IO bs=1 skip=112 count=1 status=none | od -An -tu1 -v)
    echo "$T,$1,$c,$((t70)),${b[0]},${b[2]},${b[4]},$(freq),$(cat "$THROTTLE" 2>/dev/null || echo -)" | tee -a "$CSV"
  fi
  T=$((T + 1))
  sleep 1
}
for i in $(seq 60); do tick riposo; done
for i in $(seq "$(nproc)"); do (while :; do :; done) & PIDS+=($!); done
for i in $(seq 300); do
  tick carico
  if ((HOT >= 10)); then echo "Oltre 100 °C per 10 s: carico fermato"; break; fi
done
stop_load
for i in $(seq 180); do tick raffreddamento; done
echo "Fatto: $CSV"
