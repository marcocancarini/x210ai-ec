#!/usr/bin/env python3
# Tachometer read patch, applied in memory to all-keys and tested in the 8051 emulator.
# Usage: tach_read.py
#
# It writes no file on purpose: this is a design check, not an image to flash.
# Same registers and formula as system76/ec (src/app/main/fan/common.c), but the EC
# publishes the raw count and the host does the division. See docs/8-ventole-firmware.md, 8.6.
import sys

from asm8051 import DPTR, LCALL, assemble
from fan_check import IMAGE, call, check, failures_count, fresh
import run_tests

BASE = 0x5660        # free in all-keys, which ends at 0x564D
TACH = 0x0474        # EC offsets 0x74-0x77: fan 1 count, fan 2 count, low byte first
TACH_REGS = (0x181E, 0x1820)  # F1TLRR/F1TMRR, F2TLRR/F2TMRR
TRIES = 3
HOOK = 0xB60B        # LCALL 0xBC14 in the fan task, followed by LJMP 0xED56
FAN_TASK = 0xBC14
FREQ_EC = 9_200_000  # datasheet IT5570, Table 10-2, typical (+-1.7 % from 0 to 70 C)


def rpm(count, pulses=2):
    # Datasheet 7.12.3.2: rpm = 60 / (1/fs * count * P), fs = FreqEC / 128. Count 0 is a stopped fan
    return 0 if count == 0 else 60 * FREQ_EC / 128 / (count * pulses)


def tach_items(prefix='tach'):
    # Copies both 16-bit counts to the EC space. Reads LSB then MSB twice and stores the pair
    # only when the two reads match, so a count that changes between the two bytes is not
    # published. After TRIES mismatches the old value stays. Uses A, R5, R6, R7 and DPTR
    items = []
    for channel, register in enumerate(TACH_REGS):
        p = f'{prefix}{channel}_'
        items += [
            [0x7D, TRIES],                                  # MOV R5,#TRIES
            p + 'retry:',
            DPTR(register), [0xE0, 0xFE, 0xA3, 0xE0, 0xFF],  # R6 = LSB, R7 = MSB
            DPTR(register), [0xE0, 0x6E], (0x70, p + 'again'),  # LSB again, JNZ if different
            [0xA3, 0xE0, 0x6F], (0x70, p + 'again'),        # MSB again
            DPTR(TACH + 2 * channel), [0xEE, 0xF0, 0xA3, 0xEF, 0xF0],
            (0x80, p + 'done'),
            p + 'again:',
            (0xDD, p + 'retry'),                            # DJNZ R5
            p + 'done:',
        ]
    return items


def routines():
    items = [
        'task:',
        LCALL(FAN_TASK),
        *tach_items(),
        [0x22],
    ]
    return assemble(items, BASE)


def patched():
    image = bytearray(open(IMAGE, 'rb').read())
    code, labels = routines()
    assert image[BASE:BASE + len(code)] == b'\xff' * len(code)
    image[BASE:BASE + len(code)] = code
    old = bytes.fromhex('12BC14')
    assert image[HOOK:HOOK + 3] == old
    image[HOOK:HOOK + 3] = bytes(LCALL(labels['task']))
    return bytes(image), labels, len(code)


def set_count(cpu, channel, value):
    register = TACH_REGS[channel]
    cpu.x[register], cpu.x[register + 1] = value & 255, value >> 8


def published(cpu, channel=0):
    return cpu.x[TACH + 2 * channel] | cpu.x[TACH + 2 * channel + 1] << 8


def changing_counter(cpu, values, after_reads):
    # The count register takes the next value from `values` after the given number of reads of it
    reads = {'n': 0}
    plain = cpu.xr

    def xr(address):
        address &= 0xFFFF
        if address in (0x181E, 0x181F):
            reads['n'] += 1
            index = sum(1 for limit in after_reads if reads['n'] > limit)
            value = values[min(index, len(values) - 1)]
            return value & 255 if address == 0x181E else value >> 8
        return plain(address)
    cpu.xr = xr
    return reads


def naive_read(values, after_reads):
    # LSB then MSB once, as a plain copy does
    reads, out = 0, []
    for address in (0x181E, 0x181F):
        reads += 1
        index = sum(1 for limit in after_reads if reads > limit)
        value = values[min(index, len(values) - 1)]
        out.append(value & 255 if address == 0x181E else value >> 8)
    return out[0] | out[1] << 8


def task_state(image, temperature, fan_on, mode, calls):
    cpu = fresh(image)
    cpu.x[0xB0] = fan_on
    cpu.x[0x0440] = mode
    cpu.x[0x0470] = temperature
    set_count(cpu, 0, 539)
    for _ in range(calls):
        call(cpu, HOOK)
    memory = bytearray(cpu.x)
    memory[TACH:TACH + 4] = b'\0' * 4
    return bytes(memory)


def main():
    image, labels, size = patched()
    print(f'routine at 0x{BASE:04X}, {size} bytes, hook at 0x{HOOK:04X}')

    cpu = fresh(image)
    set_count(cpu, 0, 539)
    set_count(cpu, 1, 0x5678)
    call(cpu, HOOK)
    check('fan 1 count in 0x74-0x75', published(cpu, 0), 539)
    check('fan 2 count in 0x76-0x77', published(cpu, 1), 0x5678)
    check('low byte first', bytes(cpu.x[TACH:TACH + 2]).hex(), '1b02')

    set_count(cpu, 0, 0)
    call(cpu, HOOK)
    check('stopped fan reads 0', published(cpu, 0), 0)

    # The count goes from 0x00FF to 0x0100 between the LSB and the MSB read
    values, after = [0x00FF, 0x0100], [1]
    check('a plain copy would publish', hex(naive_read(values, after)), '0x1ff')
    cpu = fresh(image)
    reads = changing_counter(cpu, values, after)
    call(cpu, HOOK)
    check('change during the read: new value published', hex(published(cpu)), '0x100')
    check('reads used: 3 in the torn pass, 4 in the good one', reads['n'], 7)

    # Same, but the change lands between the two passes
    cpu = fresh(image)
    changing_counter(cpu, [0x01FF, 0x0200], [2])
    call(cpu, HOOK)
    check('change between the passes', hex(published(cpu)), '0x200')

    # A count that changes at every read never settles: the old value stays and the loop ends
    cpu = fresh(image)
    cpu.x[TACH], cpu.x[TACH + 1] = 0x34, 0x12
    reads = changing_counter(cpu, list(range(0x300, 0x340)), list(range(1, 0x40)))
    call(cpu, HOOK)
    check('never stable: old value kept', hex(published(cpu)), '0x1234')
    check(f'never stable: at most {TRIES * 4} reads', reads['n'] <= TRIES * 4, True)

    cpu = fresh(image)
    start = cpu.count
    set_count(cpu, 0, 539)
    call(cpu, labels['task'] + 3)  # only the tachometer part, without the fan task
    print(f'     tachometer part: {cpu.count - start} instructions per call, stack +2 bytes')

    base = open(IMAGE, 'rb').read()
    same = all(task_state(base, temperature, fan_on, mode, 30) == task_state(image, temperature, fan_on, mode, 30)
               for temperature in (30, 55, 90) for fan_on in (0, 1) for mode in (0x10, 0x90))
    check('fan task leaves the same memory, apart from 0x74-0x77', same, True)

    original = open(run_tests.ORIGINAL, 'rb').read()
    features = run_tests.FEATURES['EC-V0.4.0-all-keys.bin']
    check('keyboard unchanged', len(run_tests.check_keys(original, image, features)), 0)
    check('boot writes unchanged', run_tests.boot_writes(base) == run_tests.boot_writes(image), True)

    for count in (0, 270, 539, 1078, 2156):
        print(f'     count {count:5d} -> {rpm(count):6.0f} rpm with 2 pulses per turn')

    print('all passed' if not failures_count() else f'{failures_count()} failed')
    return 1 if failures_count() else 0


if __name__ == '__main__':
    sys.exit(main())
