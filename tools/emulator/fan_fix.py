#!/usr/bin/env python3
# Proposed fan fixes, applied in memory to all-keys and tested in the 8051 emulator.
# Usage: fan_fix.py
#
# It writes no file on purpose: this is a design check, not an image to flash.
# See docs/8-ventole-firmware.md, section 8.5.
import sys

from cpu8051 import CPU
from fan_check import (TARGET, DIVIDER, HYSTERESIS, MODE, TEMP, DCR0, IMAGE, RETURN, call, check, ec,
                       failures_count, fresh, loop)
import run_tests

ORIGINAL = run_tests.ORIGINAL
BASE = 0x5660        # free in all-keys, which ends at 0x564D
FAIL_COUNT = 0x047C  # EC offset 0x7C, not used by the firmware: failed temperature reads
TACH = 0x0474        # EC offsets 0x74-0x77, not used by the firmware: raw tachometer counts
FAIL_LIMIT = 5
FAILSAFE_C = 90      # above the last threshold, so the curve goes to 100 %
DOWN_DIVIDER = 0xC0  # ramp down 4 times slower than ramp up
PECI_READ = 0xDF98


def LCALL(address): return [0x12, address >> 8, address & 255]
def LJMP(address): return [0x02, address >> 8, address & 255]
def DPTR(address): return [0x90, address >> 8, address & 255]


def assemble(items):
    # items are byte lists, 'label:' strings or (opcode..., 'label') tuples with a rel8 last
    labels, pc = {}, BASE
    for item in items:
        if isinstance(item, str):
            labels[item[:-1]] = pc
        else:
            pc += len(item)
    code, pc = [], BASE
    for item in items:
        if isinstance(item, str):
            continue
        pc += len(item)
        if isinstance(item, tuple):
            offset = labels[item[-1]] - pc
            assert -128 <= offset <= 127, item
            code += list(item[:-1]) + [offset & 255]
        else:
            code += item
    return bytes(code), labels


def routines():
    read = BASE
    items = [
        'read:',
        [0x2F, 0xF5, 0x82, 0xE4, 0x34, 0x04, 0xF5, 0x83, 0xE0, 0x22],

        # target = max(new, min(old, curve at temperature + hysteresis)), entered from 0xBB36
        # R4, R5, R7 belong to the caller. 0x65 new, 0x67 temperature. 0x66, 0x68, 0x69 are free
        'hysteresis:',
        [0x74, 0x44], LCALL(read), [0xF5, 0x66],        # 0x66 = old target
        [0xC3, 0x95, 0x65],                             # old - new
        (0x40, 'store'), (0x60, 'store'),               # rising or equal: nothing to hold
        [0x74, 0x4A], LCALL(read), [0x25, 0x67],        # A = hysteresis + temperature
        (0x50, 'no_carry'), [0x74, 0xFF],
        'no_carry:',
        [0xF5, 0x68, 0x75, 0x69, 0x6A],                 # 0x68 = shifted temperature, 0x69 = last point
        'scan:',
        [0xE5, 0x69], LCALL(read), [0xFE],              # R6 = threshold
        [0xE5, 0x68, 0xC3, 0x9E],                       # shifted temperature - threshold
        (0x40, 'next'),
        [0xE5, 0x69, 0x24, 0x02], LCALL(read),          # A = duty of this point
        (0x80, 'found'),
        'next:',
        [0xE5, 0x69, 0x24, 0xFC, 0xF5, 0x69],           # previous point
        (0xB4, 0x4A, 'scan'),                           # CJNE A,#0x4A
        [0xE4],                                         # below the table: duty 0
        'found:',
        [0xFE, 0xC3, 0x95, 0x66],                       # R6 = held duty, compare with old
        (0x40, 'lower'), [0xAE, 0x66],                  # R6 = min(old, held)
        'lower:',
        [0xEE, 0xC3, 0x95, 0x65],                       # compare with new
        (0x40, 'store'), [0x8E, 0x65],                  # keep the held duty
        'store:',
        [0x74, 0x44], LCALL(read), [0xE5, 0x65, 0xF0],  # write the target, as 0xBB36 did
        LJMP(0xBB3C),

        # Temperature read that notices failures, called from 0xDEBE
        'guard:',
        LCALL(PECI_READ),
        [0xEF], (0x60, 'failed'),
        DPTR(0x9626), [0xE0, 0x64, 0x80], (0x70, 'good'),                  # MSB is 0x80?
        DPTR(0x9625), [0xE0, 0xC3, 0x94, 0x05], (0x50, 'good'),            # 0x8000-0x8004: PECI error
        'failed:',
        DPTR(FAIL_COUNT), [0xE0], (0xB4, FAIL_LIMIT, 'count'),
        DPTR(0x9550), [0x74, FAILSAFE_C, 0xF0],
        (0x80, 'bad'),
        'count:',
        [0x04, 0xF0],
        'bad:',
        [0x7F, 0x00, 0x22],
        'good:',
        DPTR(FAIL_COUNT), [0xE4, 0xF0, 0x7F, 0x01, 0x22],

        # Fan task: publishes the tachometer and leaves manual mode when the fan is switched off
        'task:',
        LCALL(0xBC14),
        DPTR(0x181E), [0xE0], DPTR(TACH), [0xF0],
        DPTR(0x181F), [0xE0], DPTR(TACH + 1), [0xF0],
        DPTR(0x1820), [0xE0], DPTR(TACH + 2), [0xF0],
        DPTR(0x1821), [0xE0], DPTR(TACH + 3), [0xF0],
        LCALL(0xCE90), [0xEF], (0x70, 'on'),
        DPTR(0x0440), [0xE0, 0x54, 0x7F, 0xF0, 0xA3, 0xE0, 0x54, 0x7F, 0xF0],
        'on:',
        [0x22],

        # EC start: default ramp
        'init:',
        LCALL(0xBC0E),
        DPTR(0x044C), [0x74, DOWN_DIVIDER, 0xF0, 0xA3, 0xF0, 0x22],
    ]
    return assemble(items)


def patched():
    image = bytearray(open(IMAGE, 'rb').read())
    code, labels = routines()
    assert image[BASE:BASE + len(code)] == b'\xff' * len(code)
    image[BASE:BASE + len(code)] = code
    edits = [
        (0xBB31, '5003', [0, 0]),                                     # below the first threshold: always 0
        (0xBB36, '12BC6DE565F0', LJMP(labels['hysteresis']) + [0] * 3),
        (0xDEBE, '12DF98', LCALL(labels['guard'])),
        (0xB60B, '12BC14', LCALL(labels['task'])),
        (0xDC44, '12BC0E', LCALL(labels['init'])),
    ]
    for address, old, new in edits:
        old = bytes.fromhex(old)
        assert image[address:address + len(old)] == old, hex(address)
        image[address:address + len(old)] = bytes(new)
    return bytes(image), labels, len(code)


def target_after(cpu, temperatures, channel=0):
    for temperature in temperatures:
        ec(cpu, TEMP, temperature)
        call(cpu, 0xB9E9, r7=channel)
    return ec(cpu, TARGET + channel)


def fresh_fixed(image):
    cpu = fresh(image)
    ec(cpu, DIVIDER, 0)
    return cpu


def temperature_read(cpu, raw, ok):
    def stub(c):
        c.x[0x9625], c.x[0x9626] = raw & 255, raw >> 8
        c.rset(7, ok)
        high = c.pop()
        c.pc = high << 8 | c.pop()
    cpu.hooks[PECI_READ] = stub
    call(cpu, 0xDEB3)
    return cpu.x[0x9550]


def main():
    image, labels, size = patched()
    print(f'routines at 0x{BASE:04X}, {size} bytes')

    for temperature, duty in ((39, 0), (40, 20), (55, 80), (60, 100), (70, 120), (80, 152)):
        check(f'rising to {temperature} C', target_after(fresh_fixed(image), range(30, temperature + 1)), duty)
    check('39 C from cold stays off', target_after(fresh_fixed(image), [30, 39]), 0)
    check('holds at 39 C', target_after(fresh_fixed(image), [41, 39]), 20)
    check('holds at 38 C', target_after(fresh_fixed(image), [41, 38]), 20)
    check('drops at 37 C', target_after(fresh_fixed(image), [41, 37]), 0)
    check('holds at 58 C', target_after(fresh_fixed(image), [60, 58]), 100)
    check('steps at 57 C', target_after(fresh_fixed(image), [60, 57]), 80)
    check('large drop follows the curve', target_after(fresh_fixed(image), [80, 30]), 0)
    check('channel 1 too', target_after(fresh_fixed(image), [60, 58], channel=1), 100)
    cpu = fresh_fixed(image)
    ec(cpu, HYSTERESIS, 0)
    check('hysteresis 0 is the factory curve', target_after(cpu, [60, 59]), 80)
    cpu = fresh_fixed(image)
    ec(cpu, MODE, 0x12)
    ec(cpu, 0x72, 39)
    call(cpu, 0xB9E9, r7=0)
    check('nonzero source gives 0 below the table', ec(cpu, TARGET), 0)

    cpu = fresh_fixed(image)
    ec(cpu, MODE, 0x90)
    ec(cpu, TEMP, 90)
    ec(cpu, TARGET, 30)
    loop(cpu, 100)
    check('manual mode unchanged', (ec(cpu, TARGET), cpu.x[DCR0]), (30, 30))

    cpu = fresh(image)
    check('default divider', (ec(cpu, DIVIDER), ec(cpu, DIVIDER + 1)), (0, 0))
    call(cpu, labels['init'])
    check('divider set at EC start', (ec(cpu, DIVIDER), ec(cpu, DIVIDER + 1)), (DOWN_DIVIDER, DOWN_DIVIDER))

    cpu = CPU(image)
    cpu.sfr[0x81] = 0xC0
    cpu.x[0x9551] = 110
    check('good read', temperature_read(cpu, 0xF600, 1), 70)
    for attempt in range(FAIL_LIMIT):
        temperature_read(cpu, 0xF000, 0)
    check('failures keep the last value', cpu.x[0x9550], 70)
    check('next failure goes to the fail-safe', temperature_read(cpu, 0xF000, 0), FAILSAFE_C)
    check('failure count readable from the EC space', ec(cpu, 0x7C), FAIL_LIMIT)
    check('good read recovers', temperature_read(cpu, 0xF600, 1), 70)
    check('count cleared', ec(cpu, 0x7C), 0)
    check('PECI error does not reach 110 C', temperature_read(cpu, 0x8002, 1), 70)
    check('PECI error is counted', ec(cpu, 0x7C), 1)

    cpu = fresh(image)
    cpu.x[0xB0] = 1
    cpu.x[0x181E], cpu.x[0x181F], cpu.x[0x1820], cpu.x[0x1821] = 0x34, 0x12, 0x78, 0x56
    ec(cpu, MODE, 0x90)
    call(cpu, 0xB60B)
    check('tachometer in the EC space', bytes(cpu.x[TACH:TACH + 4]).hex(), '34127856')
    check('manual kept while on', ec(cpu, MODE), 0x90)
    cpu.x[0xB0] = 0
    call(cpu, 0xB60B)
    check('manual left when off', ec(cpu, MODE), 0x10)

    original = open(ORIGINAL, 'rb').read()
    features = run_tests.FEATURES['EC-V0.4.0-all-keys.bin']
    check('keyboard unchanged', len(run_tests.check_keys(original, image, features)), 0)
    base = open(IMAGE, 'rb').read()
    old, new = run_tests.boot_writes(base), run_tests.boot_writes(image)
    ours = {0x044C, 0x044D, FAIL_COUNT, *range(TACH, TACH + 4)}
    other_old = [write for write in old if write[0] not in ours]
    other_new = [write for write in new if write[0] not in ours]
    same = min(len(other_old), len(other_new))
    check('boot writes match, apart from the new fields', other_old[:same] == other_new[:same], True)
    check('divider written at boot', (0x044C, DOWN_DIVIDER) in new and (0x044D, DOWN_DIVIDER) in new, True)
    print(f'     compared {same} boot writes')

    print('all passed' if not failures_count() else f'{failures_count()} failed')
    return 1 if failures_count() else 0


if __name__ == '__main__':
    sys.exit(main())
