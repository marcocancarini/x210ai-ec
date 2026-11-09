#!/usr/bin/env python3
# Host fan control patch, applied in memory to all-keys and tested in the 8051 emulator and in
# the closed-loop simulator (fan_sim.py). Includes the tachometer read of tach_read.py.
# Usage: host_ctl.py
#
# It writes no file on purpose: this is a design check, not an image to flash.
# See docs/8-ventole-firmware.md, section 8.8, and firmware/acpi/x210ai-fan.asl.
#
# Protocol, EC offsets written with ACPI command 0x81:
#   0xC9  requested duty, 0-152 (CTR1 = 100 %)
#   0xCA  timer: 0 off, 1-254 tenths of a second left, 255 no expiry
# Write 0xC9 first, then 0xCA. Both are 0 in the EC RAM of 2026-10-17 and named nowhere: no
# access in the code, no constant with that value, no DSDT field. 0x79 is not free: 0xC1C5
# copies a 16-bit value into 0x78-0x79.
# While the timer runs the request replaces the curve, except at
# SAFE_C or above, where the EC uses the higher of the two. Sleep or power-off clears the timer.
import sys

from asm8051 import DPTR, LCALL, LJMP, assemble
from fan_check import HOST_WRITE, IMAGE, TARGET, TEMP, call, check, ec, failures_count, fresh
from fan_plant import Config
import fan_sim
import run_tests
import tach_read

BASE = 0x5660
HOST_DUTY, HOST_TIMER = 0x04C9, 0x04CA
SAFE_C = 85
FOREVER = 0xFF
FULL = 152


def routines():
    items = [
        # Fan task, from 0xB60B: fan code, tachometer, then the timer
        'task:',
        LCALL(tach_read.FAN_TASK),
        *tach_read.tach_items(),
        LCALL(0xCE90), [0xEF], (0x70, 'on'),
        DPTR(HOST_TIMER), [0xE4, 0xF0, 0x22],             # off or asleep: back to the curve
        'on:',
        DPTR(HOST_TIMER), [0xE0], (0x60, 'done'),
        (0xB4, FOREVER, 'tick'), (0x80, 'done'),          # CJNE A,#0xFF
        'tick:',
        [0x14, 0xF0],                                     # one tenth of a second less
        'done:',
        [0x22],

        # Target write, from 0xBB36. R7 channel, 0x65 curve target, 0x67 temperature, R6 free
        'target:',
        DPTR(HOST_TIMER), [0xE0], (0x60, 'write'),
        DPTR(HOST_DUTY), [0xE0, 0xFE],                    # R6 = request
        [0xE5, 0x67, 0xC3, 0x94, SAFE_C], (0x40, 'host'),  # below SAFE_C: the request
        [0xEE, 0xC3, 0x95, 0x65], (0x40, 'write'),        # at SAFE_C or above: the higher one
        'host:',
        [0x8E, 0x65],
        'write:',
        LCALL(0xBC6D), [0xE5, 0x65, 0xF0],                # as 0xBB36 did
        LJMP(0xBB3C),
    ]
    return assemble(items, BASE)


def patched():
    image = bytearray(open(IMAGE, 'rb').read())
    code, labels = routines()
    assert image[BASE:BASE + len(code)] == b'\xff' * len(code)
    image[BASE:BASE + len(code)] = code
    edits = [
        (tach_read.HOOK, '12BC14', LCALL(labels['task'])),
        (0xBB36, '12BC6DE565F0', LJMP(labels['target']) + [0] * 3),
    ]
    for address, old, new in edits:
        old = bytes.fromhex(old)
        assert image[address:address + len(old)] == old, hex(address)
        image[address:address + len(old)] = bytes(new)
    return bytes(image), labels, len(code)


def host_write(cpu, offset, value):
    # the real path of ACPI command 0x81
    call(cpu, HOST_WRITE, r7=offset, r5=value)


def request(cpu, duty, timer):
    host_write(cpu, HOST_DUTY & 255, duty)
    host_write(cpu, HOST_TIMER & 255, timer)


def task_target(image, temperature, duty=None, timer=0, calls=12):
    cpu = fresh(image)
    cpu.x[0xB0] = 1
    cpu.x[0x9550] = temperature
    if duty is not None:
        request(cpu, duty, timer)
    for _ in range(calls):
        call(cpu, tach_read.HOOK)
    return cpu


# --- closed-loop scenarios, with fan_sim.Board ---------------------------------------------------

def sim_quiet(image):
    # The OS asks for 40/152 (26 %) with no expiry, under the PL2/PL1 load
    def host(board, t):
        if t == 0:
            request(board.cpu, 40, FOREVER)
    board = fan_sim.Board(image, Config(), fan_sim.load, host=host)
    records = board.run(60)
    factory = fan_sim.Board(open(IMAGE, 'rb').read(), Config(), fan_sim.load).run(60)
    hot = [r for r in records if r['used'] >= SAFE_C]
    cool = [r for r in records if r['used'] < SAFE_C and r['t'] > 1]
    print(f'     quiet: max temperature {max(r["temp"] for r in records):.0f} C '
          f'(factory {max(r["temp"] for r in factory):.0f} C), seconds at or above {SAFE_C} C: {len(hot) / 10:.1f}')
    check('quiet: below 85 C the target is the request', {r['target'] for r in cool}, {40})
    check('quiet: at 85 C or above the target is the curve, 152', {r['target'] for r in hot}, {FULL})


def sim_hang(image):
    # The OS refreshes a 3 s timer every second asking for 20, then hangs at 20 s
    def host(board, t):
        if t < 20 and round(t * 10) % 10 == 0:
            request(board.cpu, 20, 30)
    board = fan_sim.Board(image, Config(), lambda t: 28.0, host=host)
    records = board.run(30)
    before = [r for r in records if 5 < r['t'] < 20]
    after = [r for r in records if r['t'] > 23.5]
    print(f'     hang: target before {sorted({r["target"] for r in before})}, '
          f'after {sorted({r["target"] for r in after})}')
    check('hang: request in use while the OS refreshes', {r['target'] for r in before if r['used'] < SAFE_C}, {20})
    check('hang: back to the curve 3 s after the last refresh', min(r['target'] for r in after) >= 100, True)


def sim_sleep(image):
    # Persistent request 60, sleep from 10 to 15 s, then the OS does not rewrite it
    def host(board, t):
        if t == 0:
            request(board.cpu, 60, FOREVER)
    s0 = lambda t: not 10 <= t < 15
    records = fan_sim.Board(image, Config(), lambda t: 28.0, s0=s0, host=host).run(30)
    after = [r for r in records if r['t'] > 20]
    check('sleep: timer cleared, after resume the target is the curve',
          ({r['timer'] for r in after}, min(r['target'] for r in after) > 60), ({0}, True))

    # The factory manual mode in the same situation
    def manual(board, t):
        if t == 0:
            board.cpu.x[0x0444] = 60
            host_write(board.cpu, 0x40, 0x90)
    factory = fan_sim.Board(open(IMAGE, 'rb').read(), Config(), lambda t: 28.0, s0=s0, host=manual).run(30)
    late = [r for r in factory if r['t'] > 25]
    print(f'     sleep, factory manual mode: after resume target {sorted({r["target"] for r in late})}, '
          f'rpm {late[-1]["rpm"]:.0f}, temperature {late[-1]["temp"]:.0f} C')
    check('sleep, factory manual mode: fan stays stopped after resume (the bug the patch avoids)',
          ({r['target'] for r in late}, {r['duty'] for r in late}, late[-1]['rpm'] < 50), ({0}, {0.0}, True))


def sim_raise(image):
    def host(board, t):
        if t == 0:
            request(board.cpu, FULL, FOREVER)
    records = fan_sim.Board(image, Config(), lambda t: 3.0, host=host).run(25)
    check('raise: the OS can run the fan at 100 % when cool', (records[-1]['target'], records[-1]['duty']), (FULL, 1.0))
    check('raise: the tachometer reads it', abs(fan_sim.rpm(records[-1]['published'], Config()) - 5000) < 100, True)


def main():
    image, labels, size = patched()
    print(f'routines at 0x{BASE:04X}, {size} bytes')

    base = open(IMAGE, 'rb').read()
    for temperature in (30, 39, 40, 52, 66, 79, 80, 95):
        check(f'no request: same target as the factory at {temperature} C',
              ec(task_target(image, temperature), TARGET), ec(task_target(base, temperature), TARGET))
    check('request below 85 C replaces the curve', ec(task_target(image, 70, 30, FOREVER), TARGET), 30)
    check('request above the curve raises it', ec(task_target(image, 30, 140, FOREVER), TARGET), 140)
    check('at 85 C the higher one: curve 152', ec(task_target(image, SAFE_C, 30, FOREVER), TARGET), FULL)
    check('84 C still the request', ec(task_target(image, SAFE_C - 1, 30, FOREVER), TARGET), 30)
    check('channel 2 follows too', task_target(image, 70, 30, FOREVER).x[0x0445], 30)

    cpu = task_target(image, 70, 30, 5, calls=3)
    check('timer counts down in tenths', (ec(cpu, HOST_TIMER & 255), ec(cpu, TARGET)), (2, 30))
    for _ in range(3):
        call(cpu, tach_read.HOOK)
    check('timer expired: back to the curve', (ec(cpu, HOST_TIMER & 255), ec(cpu, TARGET)), (0, 120))
    cpu = task_target(image, 70, 30, FOREVER, calls=300)
    check('255 does not expire', (ec(cpu, HOST_TIMER & 255), ec(cpu, TARGET)), (FOREVER, 30))
    cpu.x[0xB0] = 0
    call(cpu, tach_read.HOOK)
    check('sleep clears the timer', ec(cpu, HOST_TIMER & 255), 0)
    cpu.x[0xB0] = 1
    for _ in range(3):
        call(cpu, tach_read.HOOK)
    check('after resume: the curve', ec(cpu, TARGET), 120)
    cpu = task_target(image, 70, 30, FOREVER)
    request(cpu, 0, 0)
    call(cpu, tach_read.HOOK)
    check('writing 0 to the timer gives the fan back', ec(cpu, TARGET), 120)

    cpu = fresh(image)
    cpu.x[0xB0] = 1
    cpu.x[0x181E], cpu.x[0x181F] = 0x1B, 0x02
    call(cpu, tach_read.HOOK)
    check('tachometer still published', (ec(cpu, 0x74), ec(cpu, 0x75)), (0x1B, 0x02))

    original = open(run_tests.ORIGINAL, 'rb').read()
    features = run_tests.FEATURES['EC-V0.4.0-all-keys.bin']
    check('keyboard unchanged', len(run_tests.check_keys(original, image, features)), 0)
    check('boot writes unchanged', run_tests.boot_writes(base) == run_tests.boot_writes(image), True)

    for scenario in (sim_quiet, sim_hang, sim_sleep, sim_raise):
        print(f'== {scenario.__name__}')
        scenario(image)

    print('all passed' if not failures_count() else f'{failures_count()} failed')
    return 1 if failures_count() else 0


if __name__ == '__main__':
    sys.exit(main())
