#!/usr/bin/env python3
# Runs the real keyboard code of the patched EC images in an 8051 emulator (no external deps)
# Usage: run_tests.py [image ...]    default: all the images in firmware/patched
#
# Peripherals are plain memory and matrix keys enter after the hardware debounce, so a
# pass does not cover the boot ROM, the wiring or the host. See docs/2-modifiche-software.md, section 2.1.
import os
import random
import sys

from cpu8051 import CPU

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
ORIGINAL = os.path.join(ROOT, 'dumps', 'ec', 'EC-V0.4.0-20250723-lettura1.bin')
PATCHED = os.path.join(ROOT, 'firmware', 'patched')
RETURN = 0xDEAD
MATRIX = 0x2EB9
LCTRL = (0, 15)
SCAN_ENTRY = 0x8CB2  # one key event from the 0x07FE/0x07FF mailbox
PIN_PRESS, PIN_RELEASE = 0xC45E, 0xC465
OUTPUT = 0x990A  # queues one set 2 byte
SET1 = 0x0C09
DEBOUNCE = 0xC4C8
FN_ENTRY = 4
BITMAP = range(0xE0, 0xED)
# cell: set 2 press, set 2 release, set 1 press, set 1 release
ISO_JIS = {
    (5, 1): ('61', 'F0 61', '56', 'D6'), (6, 7): ('5D', 'F0 5D', '2B', 'AB'),
    (2, 8): ('6A', 'F0 6A', '7D', 'FD'), (7, 5): ('51', 'F0 51', '73', 'F3'),
    (7, 0): ('67', 'F0 67', '7B', 'FB'), (5, 6): ('64', 'F0 64', '79', 'F9'),
    (7, 6): ('13', 'F0 13', '70', 'F0'),
}
EXTRA = {
    (6, 11): ('E0 38', 'E0 F0 38', 'E0 6A', 'E0 EA'),
    (7, 11): ('E0 30', 'E0 F0 30', 'E0 69', 'E0 E9'),
    (5, 10): ('08', 'F0 08', '64', 'E4'),
}
FEATURES = {
    'EC-V0.4.0-iso-jis.bin': {'iso_jis'},
    'EC-V0.4.0-fn-ctrl-swap.bin': {'swap'},
    'EC-V0.4.0-iso-jis-fn-ctrl-swap.bin': {'iso_jis', 'swap'},
    'EC-V0.4.0-all-keys.bin': {'iso_jis', 'swap', 'extra', 'fn_fix'},
}
# Each of these must make a check fail on all-keys
MUTATIONS = [
    ('Back wrong code', [(0x306E, 0x39)]), ('<> wrong code', [(0x2F0A, 0x1C)]),
    ('Fn press not swapped', [(0xC461, 0x8E)]), ('Fn release not swapped', [(0xC468, 0x8E)]),
    ('Forward wrong type', [(0x307F, 0x00)]), ('existing cell broken', [(MATRIX + 0x31, 0x00)]),
    ('# in the wrong cell', [(0x2F20, 0x00), (0x2F21, 0x5D)]), ('LCtrl not moved', [(0x2EC8, 0x8C)]),
    ('ThinkVantage missing', [(0x2F13, 0x00)]),
    ('fix jump removed', [(0x8CFA, 0x90), (0x8CFB, 0x08), (0x8CFC, 0x0E)]),
    ('fix always saves 0', [(0x5628, 0x80)]), ('fix wrong mask', [(0x5646, 0x02)]),
    ('fix bitmap moved', [(0x561A, 0xD0)]), ('fix ignores release', [(0x5621, 0x00), (0x5622, 0x00)]),
    ('fix wrong index', [(0x5616, 0x00)]),
]


def start(image):
    cpu = CPU(image)
    cpu.sfr[0x81] = 0xC0
    cpu.x[0x27], cpu.x[0x28] = MATRIX >> 8, MATRIX & 0xFF
    cpu.out = []
    cpu.hooks[OUTPUT] = lambda c: c.out.append(c.rget(7))
    return cpu


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


def key(cpu, cell, release):
    cpu.x[0x7FE] = (cell[1] << 4) | cell[0]
    cpu.x[0x7FF] = release
    cpu.out.clear()
    call(cpu, SCAN_ENTRY)
    return cpu.out[:]


def tap(cpu, cell):
    return key(cpu, cell, 0), key(cpu, cell, 1)


def pin(cpu, down):
    cpu.out.clear()
    call(cpu, PIN_PRESS if down else PIN_RELEASE)
    return cpu.out[:]


def fn(cpu, swap, down):
    return key(cpu, LCTRL, 0 if down else 1) if swap else pin(cpu, down)


def ctrl(cpu, swap, down):
    return pin(cpu, down) if swap else key(cpu, LCTRL, 0 if down else 1)


def set1(cpu, stream):
    out, release = [], 0
    for byte in stream:
        call(cpu, SET1, byte, release)
        result = cpu.rget(7)
        if result == 0xFF:
            release = 1
        else:
            out.append(result)
            release = 0
    return out


def text(stream):
    return ' '.join(f'{byte:02X}' for byte in stream)


def expected(features):
    return {**(ISO_JIS if 'iso_jis' in features else {}), **(EXTRA if 'extra' in features else {})}


def cells(image):
    return [(s, d) for s in range(8) for d in range(16)]


def held(cpu, mode, swap, shift):
    if mode == 'shift':
        key(cpu, shift, 0)
    elif mode == 'fn':
        fn(cpu, swap, True)
    elif mode == 'ctrl':
        ctrl(cpu, swap, True)


def check_keys(original, image, features):
    # every cell, alone and with a modifier held
    errors = []
    swap = 'swap' in features
    new = expected(features)
    shift = next(c for c in cells(original) if original[MATRIX + (c[0] << 4) + c[1]] == 0x88)
    for mode in (None, 'shift', 'fn', 'ctrl'):
        for cell in cells(original):
            if cell == LCTRL and swap:
                continue
            old = start(original)
            held(old, mode, False, shift)
            before = tap(old, cell)
            cpu = start(image)
            held(cpu, mode, swap, shift)
            after = tap(cpu, cell)
            if cell in new:
                got = (text(after[0]), text(after[1]), text(set1(cpu, after[0])), text(set1(cpu, after[1])))
                if before != ([], []) or got != new[cell]:
                    errors.append(f'{mode} {cell}: {got}')
            elif before != after:
                errors.append(f'{mode} {cell}: {before} -> {after}')
    return errors


def check_swap(image, features):
    # the two physical keys
    swap = 'swap' in features
    cpu = start(image)
    pressed, released = pin(cpu, True), pin(cpu, False)
    other = start(image)
    make = key(other, LCTRL, 0)
    state = other.iram[0x29] & 0x40
    key(other, LCTRL, 1)
    if swap:
        good = (pressed, released, make, state, other.iram[0x29] & 0x40) == ([0x14], [0xF0, 0x14], [], 0x40, 0)
    else:
        good = pressed == [] and released == [] and make == [0x14] and state == 0
    return [] if good else [f'pin {pressed} {released}, LCtrl {make} state {state}']


def poll(cpu, low):
    cpu.x[0x1608] = (cpu.x[0x1608] & 0x7F) | (0 if low else 0x80)
    cpu.rset(7, FN_ENTRY)
    call(cpu, DEBOUNCE)


def check_debounce(image):
    # Fn pin through the real debounce: 6 equal reads, and a glitch is ignored
    cpu = start(image)
    events = []
    cpu.hooks[PIN_PRESS] = lambda c: events.append('press')
    cpu.hooks[PIN_RELEASE] = lambda c: events.append('release')
    poll(cpu, True)
    for _ in range(8):
        poll(cpu, False)
    events.clear()
    for _ in range(3):
        poll(cpu, True)
    for _ in range(8):
        poll(cpu, False)
    glitch = events[:]
    for _ in range(5):
        poll(cpu, True)
    early = events[:]
    poll(cpu, True)
    pressed = events[:]
    for _ in range(6):
        poll(cpu, False)
    return [] if (glitch, early, pressed, events) == ([], [], ['press'], ['press', 'release']) else [str(events)]


def order(image, swap, cell, sequence):
    cpu = start(image)
    log = []
    for step in sequence:
        if step in 'fF':
            fn(cpu, swap, step == 'f')
        else:
            log.append(key(cpu, cell, 0 if step == 'k' else 1))
    return log


def bad_releases(image, features, reference=None):
    # f/F Fn down/up, k/K key down/up. Fn up first must act like Fn up last
    swap = 'swap' in features
    ref = reference or image
    bad = 0
    for cell in cells(image):
        if cell == LCTRL:
            continue
        bad += order(image, swap, cell, 'fkFK') != order(ref, swap, cell, 'fkKF')
        bad += order(image, swap, cell, 'kfKF') != order(ref, swap, cell, 'kK')
    return bad


def fn_cells(image, features):
    swap = 'swap' in features
    return [c for c in cells(image) if c != LCTRL
            and order(image, swap, c, 'fkKF') != order(image, swap, c, 'kK')]


def check_release(image, features, reference=None):
    # with the fix: no wrong release, two Fn keys side by side, no writes outside the bitmap
    errors = []
    bad = bad_releases(image, features, reference)
    if bad:
        errors.append(f'{bad} wrong releases')
    ref = reference or image
    group = fn_cells(ref, features)

    def pair(source, first, second):
        cpu = start(source)
        log = []
        fn(cpu, True, True)
        log.append(key(cpu, first, 0))
        fn(cpu, True, False)
        log += [key(cpu, second, 0), key(cpu, first, 1), key(cpu, second, 1)]
        return log
    for first in group:
        for second in group:
            if first != second and pair(image, first, second) != pair(ref, first, second):
                errors.append(f'pair {first} {second}')
    cpu = start(image)
    writes = set()
    plain = cpu.xwr

    def spy(address, value):
        if 0x5600 <= cpu.pc < 0x5660:
            writes.add(address)
        plain(address, value)
    cpu.xwr = spy
    key(cpu, LCTRL, 0)
    for cell in group:
        key(cpu, cell, 0)
    for cell in group:
        key(cpu, cell, 1)
    outside = sorted(a for a in writes if a not in BITMAP and a != 0x80E)
    if outside:
        errors.append('writes outside the bitmap: ' + ' '.join(hex(a) for a in outside))
    return errors


def tokens(stream):
    out, prefix, release = [], 0, 0
    for byte in stream:
        if byte == 0xE0:
            prefix = 1
        elif byte == 0xF0:
            release = 1
        else:
            out.append(((prefix << 8) | byte, release))
            prefix = release = 0
    return out


def fuzz(image, swap, seed, steps=600):
    # random presses with up to 4 keys and Fn, returns keys left down at the end
    rng = random.Random(seed)
    # Pause carries its own break, fake shifts E0 12 and E0 59 are ignored by Linux
    usable = []
    for cell in cells(image):
        if cell == LCTRL or not image[MATRIX + (cell[0] << 4) + cell[1]]:
            continue
        if 0xE1 not in tap(start(image), cell)[0]:
            usable.append(cell)
    cpu = start(image)
    down, active, fn_on = set(), set(), False

    def feed(stream):
        for code, release in tokens(stream):
            (active.discard if release else active.add)(code)
    for _ in range(steps):
        roll = rng.random()
        if roll < .3:
            fn_on = not fn_on
            feed(fn(cpu, swap, fn_on))
        elif down and roll < .65:
            cell = rng.choice(sorted(down))
            down.discard(cell)
            feed(key(cpu, cell, 1))
        elif len(down) < 4:
            cell = rng.choice(usable)
            if cell not in down:
                down.add(cell)
                feed(key(cpu, cell, 0))
    for cell in sorted(down):
        feed(key(cpu, cell, 1))
    if fn_on:
        feed(fn(cpu, swap, False))
    return active - {0x112, 0x159}


def boot_writes(image, steps=3000000):
    cpu = CPU(image)
    writes = []
    cpu.xw = lambda address, value: writes.append((address, value))
    for _ in range(steps):
        cpu.step()
    return writes


def check_image(path, original, features):
    image = open(path, 'rb').read()
    results = []

    def report(name, errors):
        results.append(not errors)
        print(f"  {'ok  ' if not errors else 'FAIL'} {name}" + (f': {errors[:3]}' if errors else ''))
    report('all the cells, alone and with Shift, Fn or Ctrl held', check_keys(original, image, features))
    report('physical Fn and LCtrl', check_swap(image, features))
    report('Fn pin through the debounce', check_debounce(image))
    swap = 'swap' in features
    if 'fn_fix' in features:
        report('Fn up before the key, Fn down after the key', check_release(image, features))
        stuck = [s for s in range(100) if fuzz(image, swap, s)]
        report('random sequences, no key left down', stuck)
    else:
        print(f"  info Fn order bug still present: {bad_releases(image, features)} wrong releases")
    want = [(0x164F, 0x84)] if 'fn_fix' in features else []
    old, new = boot_writes(original), boot_writes(image)
    diff = [(n[0], n[1]) for o, n in zip(old, new) if o != n]
    report('boot writes, compared with the original', [] if diff == want and len(old) == len(new) else [str(diff)])
    return all(results), image


def check_mutations(image, original, features):
    missed = []
    for name, changes in MUTATIONS:
        mutant = bytearray(image)
        for offset, value in changes:
            mutant[offset] = value
        mutant = bytes(mutant)
        found = (check_keys(original, mutant, features) or check_swap(mutant, features)
                 or check_release(mutant, features, image))
        if not found:
            missed.append(name)
    print(f"  {'ok  ' if not missed else 'FAIL'} injected errors found: "
          f'{len(MUTATIONS) - len(missed)}/{len(MUTATIONS)}' + (f', missed {missed}' if missed else ''))
    return not missed


def main():
    paths = sys.argv[1:] or [os.path.join(PATCHED, name) for name in FEATURES]
    original = open(ORIGINAL, 'rb').read()
    passed = True
    for path in paths:
        name = os.path.basename(path)
        print(name)
        features = FEATURES[name]
        good, image = check_image(path, original, features)
        passed = passed and good
        if 'fn_fix' in features:
            passed = check_mutations(image, original, features) and passed
    print('PASS' if passed else 'FAIL')
    sys.exit(not passed)


if __name__ == '__main__':
    main()
