#!/usr/bin/env python3
# Runs the real fan code of the EC firmware in the 8051 emulator (no external deps)
# Usage: fan_check.py [image]    default: firmware/patched/EC-V0.4.0-all-keys.bin
#
# Registers are plain memory: a pass covers the firmware logic, not the fan or the pins.
# See docs/3-curve-ventola.md section 3.3.
import os
import sys

from cpu8051 import CPU

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
IMAGE = os.path.join(ROOT, 'firmware', 'patched', 'EC-V0.4.0-all-keys.bin')
RETURN = 0xDEAD
SPACE = 0x0400  # EC space as seen from ports 0x62/0x66
INIT, CURVE, OFF, HOST_WRITE = 0xB841, 0xB9E9, 0xB98F, 0xD90E
CTR1, DCR0 = 0x1841, 0x1802
MODE, TEMP_USED, TARGET, HYSTERESIS, DIVIDER, TEMP = 0x40, 0x42, 0x44, 0x4A, 0x4C, 0x70
FACTORY = [(40, 20), (45, 40), (50, 60), (55, 80), (60, 100), (70, 120), (75, 140), (80, 152)]
failures = 0


def check(label, got, expected):
    global failures
    ok = got == expected
    failures += not ok
    print(f"{'ok ' if ok else 'BAD'} {label}: {got}" + ('' if ok else f', expected {expected}'))


def failures_count():
    return failures


def call(cpu, address, r7=None, r5=None):
    cpu.push(RETURN & 0xFF)
    cpu.push(RETURN >> 8)
    cpu.pc = address
    if r7 is not None:
        cpu.rset(7, r7)
    if r5 is not None:
        cpu.rset(5, r5)
    for _ in range(200000):
        if cpu.pc == RETURN:
            return
        cpu.step()
    raise RuntimeError(f'no return, pc 0x{cpu.pc:04X}')


def fresh(image):
    cpu = CPU(image)
    cpu.sfr[0x81] = 0xC0
    call(cpu, INIT)
    cpu.x[CTR1] = 0x98
    return cpu


def ec(cpu, offset, value=None):
    if value is not None:
        cpu.x[SPACE + offset] = value
    return cpu.x[SPACE + offset]


def loop(cpu, times=1):
    for _ in range(times):
        call(cpu, CURVE, r7=0)


def target_at(cpu, temperature):
    ec(cpu, TEMP, temperature)
    loop(cpu)
    return ec(cpu, TARGET)


def calls_until(cpu, limit, condition):
    count = 0
    while not condition() and count < limit:
        loop(cpu)
        count += 1
    return count


def main():
    image = open(sys.argv[1] if len(sys.argv) > 1 else IMAGE, 'rb').read()

    cpu = fresh(image)
    check('factory table', [(ec(cpu, 0x4E + i * 4), ec(cpu, 0x50 + i * 4)) for i in range(8)], FACTORY)
    for temperature, duty in FACTORY:
        check(f'target at {temperature} C', target_at(cpu, temperature), duty)
    check('target below the first threshold', target_at(cpu, 39), 0)

    for value in (2, 10):
        cpu = fresh(image)
        ec(cpu, HYSTERESIS, value)
        target_at(cpu, 45)
        check(f'hysteresis {value} has no effect at 39 C', target_at(cpu, 39), 0)

    cpu = fresh(image)
    ec(cpu, TEMP, 90)
    check('ramp up, calls for 0 to 152', calls_until(cpu, 1000, lambda: cpu.x[DCR0] == 152), 152)
    ec(cpu, TEMP, 20)
    check('ramp down, calls for 152 to 0', calls_until(cpu, 1000, lambda: cpu.x[DCR0] == 0), 152)

    for value, up, down in ((0x04, 19, 10), (0x0C, 37, 10), (0x40, 10, 19), (0xC0, 10, 37)):
        cpu = fresh(image)
        ec(cpu, DIVIDER, value)
        ec(cpu, TEMP, 90)
        check(f'divider 0x{value:02X}, calls for 10 up', calls_until(cpu, 2000, lambda: cpu.x[DCR0] == 10), up)
        cpu = fresh(image)
        cpu.x[DCR0] = 152
        ec(cpu, DIVIDER, value)
        ec(cpu, TEMP, 20)
        check(f'divider 0x{value:02X}, calls for 10 down', calls_until(cpu, 2000, lambda: cpu.x[DCR0] == 142), down)

    cpu = fresh(image)
    ec(cpu, MODE, 0x90)
    ec(cpu, TEMP, 90)
    ec(cpu, TARGET, 30)
    loop(cpu, 100)
    check('manual mode follows the written target', (ec(cpu, TARGET), cpu.x[DCR0]), (30, 30))

    cpu = fresh(image)
    ec(cpu, MODE, 0x12)
    ec(cpu, TEMP, 90)
    ec(cpu, 0x72, 50)
    loop(cpu, 100)
    check('source 2 uses the host temperature', (ec(cpu, TEMP_USED), cpu.x[DCR0]), (50, 60))

    cpu = fresh(image)
    ec(cpu, MODE, 0x20)
    ec(cpu, TEMP, 90)
    loop(cpu, 100)
    check('mode 0x20 keeps the duty still', cpu.x[DCR0], 0)

    for mode, flag, used in ((0x11, 0, 45), (0x11, 1, 55), (0x13, 0, 65), (0x13, 1, 75)):
        cpu = fresh(image)
        ec(cpu, MODE, mode)
        ec(cpu, 0x7B, flag)
        for offset, value in ((0x70, 45), (0x71, 55), (0x72, 65), (0x73, 75)):
            ec(cpu, offset, value)
        loop(cpu)
        check(f'mode 0x{mode:02X} with 0x7B={flag} uses', ec(cpu, TEMP_USED), used)

    cpu = fresh(image)
    for offset, value in ((0x40, 0x90), (0x4E, 0x30), (0x6D, 0x07), (0xFB, 0x01)):
        call(cpu, HOST_WRITE, r7=offset, r5=value)
        check(f'host write reaches offset 0x{offset:02X}', ec(cpu, offset), value)

    cpu = fresh(image)
    ec(cpu, MODE, 0x90)
    ec(cpu, TARGET, 100)
    loop(cpu, 120)
    check('manual duty before sleep', cpu.x[DCR0], 100)
    call(cpu, OFF, r7=0)
    loop(cpu, 120)
    check('manual target after sleep stays 0', (ec(cpu, TARGET), cpu.x[DCR0]), (0, 0))

    print('all passed' if not failures else f'{failures} failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
