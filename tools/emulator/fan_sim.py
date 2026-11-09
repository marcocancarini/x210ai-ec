#!/usr/bin/env python3
# Closed-loop simulation: the real fan task of the EC runs every 100 ms in the 8051 emulator,
# with fan_plant.py modelling PWM, driver, fan, tachometer line, tachometer counter and CPU
# temperature. Compares what the tachometer patch, a plain copy and a host I2EC read would see.
# Usage: fan_sim.py [scenario ...]      without arguments runs all of them
#
# The firmware is real code; the hardware is a set of hypotheses. A pass means "the model
# behaves as described", not "the board does". See docs/8-ventole-firmware.md, section 8.7.
import random
import sys
from dataclasses import replace

from fan_check import IMAGE, MODE, SPACE, TARGET, call, check, failures_count, fresh
from fan_plant import DCR0, TACH_REGS, Config, Plant
import tach_read

TICK = 0.1           # s, fan loop period (docs 3.1)
INSTR = 12 / 9.2e6   # s per instruction: 12 clocks at 9.2 MHz (assumption)
HOST_GAP = 20e-6     # s between the two bytes of a host I2EC read (assumption)
PECI_TEMP = 0x9550
PWM_INIT = 0x3308    # (register high, register low, value) triplets, docs 3.1


def pwm_init(cpu, image):
    # The PWM registers come from a table run at EC start, outside the fan init that fresh() calls
    at = PWM_INIT
    while image[at] == 0x18:
        cpu.x[image[at] << 8 | image[at + 1]] = image[at + 2]
        at += 3


class Board:
    def __init__(self, image, config, power, s0=lambda t: True, seed=1, host=None):
        # host(board, t), if given, runs before each tick: an OS writing to the EC space
        self.host = host
        self.cpu = fresh(image)
        pwm_init(self.cpu, image)
        self.plant = Plant(self.cpu, config)
        self.power = power
        self.s0 = s0
        self.rng = random.Random(seed)
        self.reads = []
        self.call_start = self.count_start = 0
        plain = self.cpu.xr

        def xr(address):
            address &= 0xFFFF
            if TACH_REGS[0] <= address <= TACH_REGS[1] + 1:
                now = self.call_start + (self.cpu.count - self.count_start) * INSTR
                self.plant.advance_to(now)
                self.reads.append((address, self.cpu.x[address]))
            return plain(address)
        self.cpu.xr = xr

    def tick(self):
        cpu, plant = self.cpu, self.plant
        t = plant.t
        plant.power = self.power(t)
        cpu.x[PECI_TEMP] = max(0, min(255, round(plant.t_die)))
        cpu.iram[0x45] = int(t * 20 + 0.5) % 20
        cpu.x[0xB0] = 1 if self.s0(t) else 0
        if self.host:
            self.host(self, round(t, 3))
        self.reads = []
        self.call_start, self.count_start = t, cpu.count
        call(cpu, tach_read.HOOK)
        record = {
            't': t, 'temp': plant.t_die, 'duty': plant.duty(0), 'dcr': cpu.x[DCR0],
            'rpm': plant.fans[0].rpm, 'register': plant.fans[0].register,
            'published': cpu.x[tach_read.TACH] | cpu.x[tach_read.TACH + 1] << 8,
            'published2': cpu.x[tach_read.TACH + 2] | cpu.x[tach_read.TACH + 3] << 8,
            'naive': self.naive(),
            'target': cpu.x[SPACE + TARGET], 'used': cpu.x[SPACE + 0x42], 'timer': cpu.x[SPACE + 0xCA],
        }
        host = t + TICK * self.rng.uniform(0.1, 0.9)
        plant.advance_to(host)
        low = cpu.x[TACH_REGS[0]]
        plant.advance_to(host + HOST_GAP)
        record['i2ec'] = low | cpu.x[TACH_REGS[0] + 1] << 8
        plant.advance_to(t + TICK)
        return record

    def naive(self):
        # what a single LSB-then-MSB copy would have published in this call
        low = next((v for a, v in self.reads if a == TACH_REGS[0]), None)
        high = next((v for a, v in self.reads if a == TACH_REGS[0] + 1), None)
        return None if low is None or high is None else low | high << 8

    def run(self, seconds):
        return [self.tick() for _ in range(round(seconds / TICK))]


def rpm(count, config):
    return 0.0 if count == 0 else 60 * config.freq_ec / 128 / (count * config.pulses)


def steady(records, config, tolerance=0.03, skip=0.5):
    # samples where the fan speed is stable, with the error of the published value
    out = []
    for before, now in zip(records, records[1:]):
        if now['rpm'] > 300 and abs(now['rpm'] - before['rpm']) < now['rpm'] * 0.002 and now['t'] > skip:
            out.append(abs(rpm(now['published'], config) - now['rpm']) / now['rpm'])
    return out


def torn(records, history, key):
    return sum(1 for r in records if r[key] is not None and r[key] not in history)


def load(t):
    # idle, PL2 for about 25 s, PL1, idle: like the 2026-11-07 run (docs 8.2)
    return 3.0 if t < 5 else 64.0 if t < 30 else 28.0 if t < 45 else 3.0


def summary(name, records, config, plant):
    history = plant.fans[0].history
    published = [rpm(r['published'], config) for r in records]
    print(f'     {name}: max temperature {max(r["temp"] for r in records):.0f} C, '
          f'max duty {max(r["duty"] for r in records) * 100:.0f} %, '
          f'max true rpm {max(r["rpm"] for r in records):.0f}, '
          f'published rpm {min(published):.0f}-{max(published):.0f}')
    print(f'     torn values: patch {torn(records, history, "published")}, '
          f'plain copy {torn(records, history, "naive")}, host I2EC {torn(records, history, "i2ec")} '
          f'out of {len(records)}')


# --- scenarios ------------------------------------------------------------------------------

def scenario_linear(image):
    config = Config(driver='linear')
    board = Board(image, config, load)
    records = board.run(60)
    summary('linear', records, config, board.plant)
    errors = steady(records, config)
    check('linear: stable samples found', len(errors) > 20, True)
    check('linear: published rpm within 3 % when stable', max(errors) < 0.03, True)
    check('linear: patch never publishes a torn value', torn(records, board.plant.fans[0].history, 'published'), 0)
    check('linear: fan 2 absent reads 0', {r['published2'] for r in records}, {0})
    check('linear: the curve reaches 100 % under PL2', max(r['duty'] for r in records), 1.0)

    original = Board(open(IMAGE, 'rb').read(), config, load).run(60)
    check('linear: same duty sequence as the unpatched firmware',
          [r['dcr'] for r in original] == [r['dcr'] for r in records], True)


def scenario_pwm4(image):
    config = Config(driver='pwm4')
    board = Board(image, config, load)
    records = board.run(60)
    summary('pwm4', records, config, board.plant)
    errors = steady(records, config)
    check('4 wires: published rpm within 3 % when stable', len(errors) > 20 and max(errors) < 0.03, True)


def scenario_switched(image, filter_us):
    config = Config(driver='switched', filter_us=filter_us)
    board = Board(image, config, load)
    records = board.run(60)
    name = f'switched, filter {filter_us:g} us'
    summary(name, records, config, board.plant)
    partial = [r for r in records if 0 < r['duty'] < 1 and r['rpm'] > 1000 and r['t'] > 1]
    full = [r for r in records if r['duty'] == 1 and r['rpm'] > 1000]
    bad = sum(1 for r in partial if abs(rpm(r['published'], config) - r['rpm']) > 0.1 * r['rpm'])
    good_full = sum(1 for r in full if abs(rpm(r['published'], config) - r['rpm']) < 0.1 * r['rpm'])
    print(f'     {name}: wrong by more than 10 %: {bad} of {len(partial)} samples below 100 %, '
          f'right at 100 %: {good_full} of {len(full)}')
    return config, records, partial, full, bad, good_full


def scenario_switched_raw(image):
    config, records, partial, full, bad, good_full = scenario_switched(image, 0)
    check('switched, no filter: wrong below 100 %', bad > 0.9 * len(partial), True)
    check('switched, no filter: absurd values, over 10x the maximum',
          max(rpm(r['published'], config) for r in partial) > 10 * config.rpm_max, True)
    check('switched, no filter: right at 100 %', len(full) > 0 and good_full > 0.8 * len(full), True)


def scenario_switched_filter(image):
    # 30 us filter, PWM period 50 us: a low pulse counts only if it lasts 30 us, so above 60 % duty.
    # There the off time is under 20 us and the filter hides it: the reading is right
    config, records, partial, full, bad, good_full = scenario_switched(image, 30)
    high = [r for r in partial if r['duty'] > 0.65]
    low = [r for r in partial if r['duty'] < 0.55]
    right = lambda r: abs(rpm(r['published'], config) - r['rpm']) < 0.1 * r['rpm']
    settled = lambda rs: [r for prev, r in zip(rs, rs[1:]) if prev['duty'] > 0.65]
    check('switched, 30 us filter: right above 65 % duty', len(high) > 0 and all(map(right, settled(high))), True)
    # the register keeps the last count until the timeout, about 0.9 s: skip 1 s after a high duty
    last_high = [max([p['t'] for p in records if p['t'] <= r['t'] and p['duty'] > 0.6], default=-9) for r in low]
    low = [r for r, t in zip(low, last_high) if r['t'] - t > 1 and r['t'] > 6]
    check('switched, 30 us filter: 0 below 55 % duty with the fan spinning',
          len(low) > 0 and {r['published'] for r in low} == {0}, True)


def scenario_no_tach(image):
    config = Config(tach_connected=False)
    records = Board(image, config, load).run(20)
    check('tachometer not connected: always 0 with the fan spinning',
          ({r['published'] for r in records}, max(r['rpm'] for r in records) > 3000), ({0}, True))


def scenario_blocked(image):
    config = Config(blocked=True)
    records = Board(image, config, load).run(20)
    unplugged = Board(image, Config(tach_connected=False), load).run(20)
    check('blocked fan: always 0', {r['published'] for r in records}, {0})
    check('blocked and unplugged look the same from software',
          [r['published'] for r in records] == [r['published'] for r in unplugged], True)


def scenario_no_start(image):
    # 1.7 W with the fan stopped keeps the CPU at about 42 C: the curve asks for 20/153 = 13 %
    config = Config(start_duty=0.25)
    board = Board(image, config, lambda t: 1.7)
    board.plant.t_die = board.plant.t_sink = 42.0
    records = board.run(20)
    last = records[-1]
    print(f'     no start: temperature {last["temp"]:.1f} C, duty {last["duty"] * 100:.0f} %, rpm {last["rpm"]:.0f}')
    check('fan that does not start at 13 %: duty above 0, published 0',
          (last['duty'] > 0, last['rpm'], last['published']), (True, 0.0, 0))
    board = Board(image, replace(config, start_duty=0.10), lambda t: 1.7)
    board.plant.t_die = board.plant.t_sink = 42.0
    last = board.run(20)[-1]
    check('same at 13 % with a fan that starts at 10 %: published > 0', last['published'] > 0, True)


def scenario_sleep(image):
    config = Config()
    board = Board(image, config, lambda t: 28.0, s0=lambda t: t < 15)
    records = board.run(30)
    awake = [r for r in records if 10 < r['t'] < 15]
    asleep = [r for r in records if r['t'] > 25]
    check('sleep: published > 0 before', all(r['published'] > 0 for r in awake), True)
    check('sleep: pins low, fan stopped, published 0 after', (
        {r['duty'] for r in asleep}, {r['published'] for r in asleep}), ({0.0}, {0}))


def scenario_meter(image):
    # What a meter on the fan connector would read, at fixed duty in manual mode
    print('     meter on the fan connector, steady fan, 1 s window:')
    print('     hypothesis          duty   +V wire            TACH wire           PWM wire')
    rows = {}
    for driver in ('linear', 'switched', 'pwm4'):
        for duty in (76, 152):
            config = Config(driver=driver)
            board = Board(image, config, lambda t: 3.0)
            board.cpu.x[SPACE + MODE] = 0x90
            board.cpu.x[SPACE + TARGET] = duty
            board.run(20)
            board.plant.start_meter()
            board.run(1)
            meter = board.plant.read_meter()
            rows[driver, duty] = meter
            cells = [f'{meter[w][0]:4.2f} V {meter[w][1]:8.0f} Hz' if w in meter else '-' for w in ('+V', 'TACH', 'PWM')]
            print(f'     {driver:18s} {board.plant.duty(0) * 100:4.0f} %   ' + '   '.join(f'{c:17s}' for c in cells))
    linear, switched, pwm4 = rows['linear', 76], rows['switched', 76], rows['pwm4', 76]
    check('meter: TACH frequency follows the speed, about 2 per turn', 50 < linear['TACH'][1] < 150, True)
    check('meter: +V switching at about 20 kHz only with the switched driver',
          (round(switched['+V'][1] / 1000), linear['+V'][1], pwm4['+V'][1]), (20, 0.0, 0.0))
    check('meter: switched driver puts PWM bursts on TACH below 100 %', switched['TACH'][1] > 1000, True)
    check('meter: at 100 % the three hypotheses read the same TACH',
          len({round(rows[d, 152]['TACH'][1] / 10) for d in ('linear', 'switched', 'pwm4')}), 1)


SCENARIOS = {
    'linear': scenario_linear,
    'pwm4': scenario_pwm4,
    'switched': scenario_switched_raw,
    'filter': scenario_switched_filter,
    'no-tach': scenario_no_tach,
    'blocked': scenario_blocked,
    'no-start': scenario_no_start,
    'sleep': scenario_sleep,
    'meter': scenario_meter,
}


def main():
    image, _, _ = tach_read.patched()
    names = sys.argv[1:] or list(SCENARIOS)
    for name in names:
        print(f'== {name}')
        SCENARIOS[name](image)
    print('all passed' if not failures_count() else f'{failures_count()} failed')
    return 1 if failures_count() else 0


if __name__ == '__main__':
    sys.exit(main())
