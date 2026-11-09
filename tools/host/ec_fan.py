#!/usr/bin/env python3
# Fan state of the X210AI EC, from the running OS. No external deps. Needs root.
#
#   ec_fan.py status [--ec-file FILE]        EC space via ec_sys, or a saved 256-byte dump
#   ec_fan.py log [--interval S] [--duration S] [--out FILE.csv]
#   ec_fan.py i2ec [--samples N] [--interval S]
#   ec_fan.py request PERCENT [--timer S | --forever]     needs the EC patch (docs 8.8)
#   ec_fan.py auto                                         gives the fan back to the curve
#
# status, log and i2ec only read. i2ec writes the Super I/O index and address registers on
# ports 0x2E/0x2F to read EC memory, after checking the chip ID: see docs 4.8.
# request and auto write two EC bytes and need: modprobe ec_sys write_support=1
import argparse
import csv
import glob
import os
import sys
import time

EC_IO = '/sys/kernel/debug/ec/ec0/io'
CTR = 152                       # 100 % duty
FS = 9_200_000 / 128            # tachometer sample rate, datasheet IT5570 7.12.3.2
PULSES = 2
HOST_DUTY, HOST_TIMER = 0xC9, 0xCA
SIO = 0x2E                      # D2ADR index; 0x2F is D2DAT
TACH = 0x181E


def rpm(count, pulses=PULSES):
    return 0 if count == 0 else round(60 * FS / (count * pulses))


def read_ec(path):
    with open(path, 'rb') as f:
        data = f.read(256)
    if len(data) < 256:
        sys.exit(f'{path}: {len(data)} bytes, expected 256')
    return data


def decode(ec):
    tach1 = ec[0x74] | ec[0x75] << 8
    tach2 = ec[0x76] | ec[0x77] << 8
    return {
        'mode1': ec[0x40], 'mode2': ec[0x41], 'temp_used': ec[0x42], 'temp_ec': ec[0x70],
        'target1': ec[0x44], 'duty1': ec[0x46], 'target2': ec[0x45], 'duty2': ec[0x47],
        'duty1_pct': round(ec[0x46] * 100 / CTR), 'hysteresis': ec[0x4A], 'divider': ec[0x4C],
        'tach1': tach1, 'rpm1': rpm(tach1), 'tach2': tach2, 'rpm2': rpm(tach2),
        'host_duty': ec[HOST_DUTY], 'host_timer': ec[HOST_TIMER], 'fan_hold_fb': ec[0xFB],
        'table': [(ec[0x4E + 4 * i], ec[0x50 + 4 * i]) for i in range(8)],
    }


def coretemp():
    for hwmon in glob.glob('/sys/class/hwmon/hwmon*'):
        try:
            if open(f'{hwmon}/name').read().strip() == 'coretemp':
                return int(open(f'{hwmon}/temp1_input').read()) / 1000
        except OSError:
            pass
    return None


def status(args):
    s = decode(read_ec(args.ec_file or EC_IO))
    mode = 'manual' if s['mode1'] & 0x80 else 'curve'
    print(f"mode        0x{s['mode1']:02X} 0x{s['mode2']:02X}  ({mode})")
    print(f"temperature EC {s['temp_ec']} C, used by the curve {s['temp_used']} C, coretemp {coretemp()}")
    print(f"fan 1       target {s['target1']}, duty {s['duty1']} ({s['duty1_pct']} %)")
    print(f"fan 2       target {s['target2']}, duty {s['duty2']}")
    print(f"curve       " + ' '.join(f'{t}C:{d}' for t, d in s['table']))
    print(f"hysteresis  {s['hysteresis']}, ramp divider 0x{s['divider']:02X}, offset 0xFB {s['fan_hold_fb']}")
    print(f"tachometer  fan 1 {s['tach1']} = {s['rpm1']} rpm, fan 2 {s['tach2']} = {s['rpm2']} rpm"
          f"   (0 without the patch of docs 8.6)")
    print(f"host        request {s['host_duty']}, timer {s['host_timer']}   (docs 8.8)")


def log(args):
    out = open(args.out, 'w', newline='') if args.out else sys.stdout
    fields = ['time', 'coretemp', 'temp_ec', 'temp_used', 'target1', 'duty1', 'duty1_pct', 'tach1', 'rpm1',
              'host_duty', 'host_timer']
    writer = csv.DictWriter(out, fields, extrasaction='ignore')
    writer.writeheader()
    start = time.monotonic()
    while time.monotonic() - start < args.duration:
        row = decode(read_ec(EC_IO))
        row['time'] = round(time.monotonic() - start, 1)
        row['coretemp'] = coretemp()
        writer.writerow(row)
        out.flush()
        time.sleep(args.interval)


class SuperIo:
    def __init__(self):
        self.port = os.open('/dev/port', os.O_RDWR)

    def outb(self, port, value):
        os.pwrite(self.port, bytes([value]), port)

    def inb(self, port):
        return os.pread(self.port, 1, port)[0]

    def read(self, index):
        self.outb(SIO, index)
        return self.inb(SIO + 1)

    def d2_write(self, register, value):
        self.outb(SIO, 0x2E)            # D2ADR
        self.outb(SIO + 1, register)
        self.outb(SIO, 0x2F)            # D2DAT
        self.outb(SIO + 1, value)

    def d2_read(self, register):
        self.outb(SIO, 0x2E)
        self.outb(SIO + 1, register)
        self.outb(SIO, 0x2F)
        return self.inb(SIO + 1)

    def ec_read(self, address):
        # I2EC, datasheet IT5570 6.3.2.9 and Figure 7-41: address high, address low, data
        self.d2_write(0x11, address >> 8)
        self.d2_write(0x10, address & 255)
        return self.d2_read(0x12)


def i2ec(args):
    sio = SuperIo()
    chip = sio.read(0x20) << 8 | sio.read(0x21)
    print(f'Super I/O chip ID at 0x{SIO:02X}: 0x{chip:04X}')
    if chip not in (0x5570, 0x5571):
        sys.exit('not an IT5570/IT5571: stopping without further access')
    print('GPCRD6 0x162E (TACH0A must be 0x00): 0x%02X' % sio.ec_read(0x162E))
    print('# time  F1 count  rpm  F2 count  rpm  TSWCTLR  ZINTSCR   (datasheet: I2EC read not guaranteed)')
    start = time.monotonic()
    for _ in range(args.samples):
        low1, high1 = sio.ec_read(TACH), sio.ec_read(TACH + 1)
        low2, high2 = sio.ec_read(TACH + 2), sio.ec_read(TACH + 3)
        f1, f2 = low1 | high1 << 8, low2 | high2 << 8
        print(f'{time.monotonic() - start:6.1f}  {f1:8d}  {rpm(f1):5d}  {f2:8d}  {rpm(f2):5d}'
              f'     0x{sio.ec_read(0x1848):02X}     0x{sio.ec_read(0x1822):02X}')
        time.sleep(args.interval)


def write_ec(offset, value):
    with open(EC_IO, 'r+b') as f:
        f.seek(offset)
        f.write(bytes([value]))


def request(args):
    if not 0 <= args.percent <= 100:
        sys.exit('percent must be 0-100')
    timer = 0xFF if args.forever else max(1, min(254, round(args.timer * 10)))
    write_ec(HOST_DUTY, round(args.percent * CTR / 100))
    write_ec(HOST_TIMER, timer)
    print(f'request {args.percent} %, timer {"no expiry" if timer == 0xFF else f"{timer / 10} s"}. '
          f'At 85 C or above the EC uses the curve if it is higher')


def auto(args):
    write_ec(HOST_TIMER, 0)
    print('back to the curve')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('status')
    p.add_argument('--ec-file')
    p.set_defaults(run=status)
    p = sub.add_parser('log')
    p.add_argument('--interval', type=float, default=1.0)
    p.add_argument('--duration', type=float, default=600)
    p.add_argument('--out')
    p.set_defaults(run=log)
    p = sub.add_parser('i2ec')
    p.add_argument('--samples', type=int, default=20)
    p.add_argument('--interval', type=float, default=0.5)
    p.set_defaults(run=i2ec)
    p = sub.add_parser('request')
    p.add_argument('percent', type=float)
    group = p.add_mutually_exclusive_group()
    group.add_argument('--timer', type=float, default=10.0, help='seconds, 0.1-25.4')
    group.add_argument('--forever', action='store_true')
    p.set_defaults(run=request)
    p = sub.add_parser('auto')
    p.set_defaults(run=auto)
    args = parser.parse_args()
    args.run(args)


if __name__ == '__main__':
    main()
