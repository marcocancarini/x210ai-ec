# Model of the hardware around the EC fan pins: PWM output, fan driver, fan, tachometer line,
# ITE tachometer counter and CPU temperature. No external deps.
#
# Everything here is a hypothesis with parameters, not a measurement: the point is to see what
# the firmware and the host would read under each hypothesis, and what a meter would show.
# See docs/8-ventole-firmware.md, section 8.7.
import math
from dataclasses import dataclass, field

DCR0, CTR1, C4CPRS = 0x1802, 0x1841, 0x1827
GPCRA0, GPDRA = 0x1610, 0x1601
TACH_REGS = (0x181E, 0x1820)
PWM_CLOCK = 6_144_000   # group 1 clock, CLK6MSEL (docs 3.1)


@dataclass
class Config:
    driver: str = 'linear'      # 'linear': filtered DC, 'switched': supply chopped at the PWM rate,
                                # 'pwm4': 4-wire fan, constant supply and PWM on its own wire
    pulses: int = 2             # tachometer pulses per turn
    rpm_max: float = 5000       # at 100 %
    start_duty: float = 0.25    # needed to start from rest
    stop_duty: float = 0.12     # below this a spinning fan stops
    tau_up: float = 0.8         # s
    tau_down: float = 2.0       # s
    supply_v: float = 5.0
    pullup_v: float = 3.3
    tach_connected: bool = True
    second_fan: bool = False    # TACH1A: pulled up, nothing connected, unless True
    blocked: bool = False
    filter_us: float = 0.0      # glitch filter on the tachometer input: unknown, the datasheet says nothing
    freq_ec: float = 9_200_000  # datasheet Table 10-2, typical
    timeout_counts: int = 0xFFFF  # without edges for this long the register reads 0 (assumption)
    # Two-node thermal model, loosely matched to the 2026-11-07 run (docs 8.2)
    t_amb: float = 30.0
    c_die: float = 1.5          # J/K
    r_die_sink: float = 0.6     # K/W
    c_sink: float = 80.0        # J/K
    g_still: float = 0.15       # W/K, heatsink to air with the fan stopped
    g_fan: float = 0.85         # W/K added at full speed
    t_throttle: float = 100.0


@dataclass
class Channel:
    rpm: float = 0.0
    phase: float = 0.0          # tachometer pulses, fractional
    raw_low: bool = False       # line level before the filter
    level_low: bool = False     # level after the filter
    pending: tuple = None       # (time, low) waiting for the filter
    last_edge: float = None
    register: int = 0
    history: set = field(default_factory=lambda: {0})
    edges: int = 0


class Plant:
    def __init__(self, cpu, config=None):
        self.cpu = cpu
        self.cfg = config or Config()
        self.t = 0.0
        self.fs = self.cfg.freq_ec / 128
        self.fans = [Channel(), Channel()]
        self.t_die = self.t_sink = 45.0
        self.power = 3.0
        self.meter = None

    # --- what the EC drives ---------------------------------------------------------------
    def duty(self, channel=0):
        x = self.cpu.x
        mode = x[GPCRA0 + channel] >> 6
        if mode == 1:                               # GPIO output
            return 1.0 if x[GPDRA] >> channel & 1 else 0.0
        if mode != 0:
            return 0.0                              # input: the driver sees its own pull-down
        ctr, dcr = x[CTR1], x[DCR0 + channel]
        return 1.0 if dcr >= ctr else dcr / (ctr + 1)

    def pwm_period(self):
        return (self.cpu.x[C4CPRS] + 1) * (self.cpu.x[CTR1] + 1) / PWM_CLOCK

    def fan_drive(self, duty):
        # fraction of full speed the fan is asked for, and whether its Hall sensor has power
        cfg = self.cfg
        if cfg.driver == 'pwm4':
            return duty, True
        if cfg.driver == 'switched':
            return duty, None                       # powered only during the on part of each period
        # in a brushless fan the Hall sensor also drives the motor: if the fan can turn, it has power
        return duty, duty >= cfg.stop_duty

    # --- time ----------------------------------------------------------------------------
    def advance_to(self, t_end, step=0.0005):
        while self.t < t_end - 1e-12:
            dt = min(step, t_end - self.t)
            self._segment(self.t, self.t + dt)
            self.t += dt
        for index in range(2):
            self._settle(index, self.t)

    def _segment(self, a, b):
        cfg = self.cfg
        dt = b - a
        airflow = 0.0
        for index, fan in enumerate(self.fans):
            present = index == 0 or cfg.second_fan
            duty = self.duty(index)
            drive, powered = self.fan_drive(duty)
            if not present or cfg.blocked:
                target = 0.0
            elif fan.rpm < 1:
                target = cfg.rpm_max * drive if drive >= cfg.start_duty else 0.0
            else:
                target = cfg.rpm_max * drive if drive >= cfg.stop_duty else 0.0
            tau = cfg.tau_up if target > fan.rpm else cfg.tau_down
            old = fan.rpm
            fan.rpm += (target - fan.rpm) * (1 - math.exp(-dt / tau))
            if fan.rpm < 1 and target == 0:
                fan.rpm = 0.0
            rate = (old + fan.rpm) / 2 / 60 * cfg.pulses   # pulses per second
            phase_a = fan.phase
            fan.phase += rate * dt
            if index == 0:
                airflow = fan.rpm / cfg.rpm_max
            connected = cfg.tach_connected if index == 0 else cfg.second_fan
            lows = []
            if present and connected:
                lows = _intersect(_hall_lows(phase_a, rate, a, b), self._powered(powered, duty, a, b))
            self._line(index, fan, lows, a, b)
            if self.meter is not None and index == 0:
                self._measure(lows, duty, a, b)
        # thermal: at TjMax - 10 = 100 C the CPU throttles and holds the die there
        g = cfg.g_still + cfg.g_fan * airflow
        flow = (self.t_die - self.t_sink) / cfg.r_die_sink
        power = self.power if self.t_die < cfg.t_throttle else min(self.power, flow)
        self.t_die += (power - flow) / cfg.c_die * dt
        self.t_sink += (flow - (self.t_sink - cfg.t_amb) * g) / cfg.c_sink * dt

    def _powered(self, powered, duty, a, b):
        if powered is True:
            return [(a, b)]
        if powered is False or duty <= 0:
            return []
        if duty >= 1:
            return [(a, b)]
        period = self.pwm_period()
        on = duty * period
        out, n = [], math.floor(a / period)
        while n * period < b:
            s, e = max(a, n * period), min(b, n * period + on)
            if s < e:
                out.append((s, e))
            n += 1
        return out

    # --- tachometer line, filter and counter --------------------------------------------------
    def _line(self, index, fan, lows, a, b):
        eps = 1e-12
        starts_low = bool(lows) and lows[0][0] <= a + eps
        if fan.raw_low and not starts_low:
            self._raw(index, a, False)
        for s, e in lows:
            if not fan.raw_low:
                self._raw(index, s, True)
            if e < b - eps:
                self._raw(index, e, False)

    def _raw(self, index, t, low):
        fan = self.fans[index]
        fan.raw_low = low
        self._settle(index, t)
        if low != fan.level_low:
            fan.pending = (t, low)
        else:
            fan.pending = None
        if self.cfg.filter_us == 0:
            self._settle(index, t)

    def _settle(self, index, now):
        fan = self.fans[index]
        delay = self.cfg.filter_us * 1e-6
        if fan.pending and now - fan.pending[0] >= delay:
            t, low = fan.pending
            fan.pending = None
            fan.level_low = low
            if low:
                self._edge(index, t + delay)
        if fan.last_edge is not None and (now - fan.last_edge) * self.fs > self.cfg.timeout_counts:
            fan.last_edge = None
            self._store(index, 0)

    def _edge(self, index, t):
        fan = self.fans[index]
        fan.edges += 1
        if fan.last_edge is not None:
            count = int((t - fan.last_edge) * self.fs)
            self._store(index, count if count <= 0xFFFF else 0)
        fan.last_edge = t

    def _store(self, index, value):
        fan = self.fans[index]
        fan.register = value
        fan.history.add(value)
        base = TACH_REGS[index]
        self.cpu.x[base], self.cpu.x[base + 1] = value & 255, value >> 8

    # --- a multimeter or a frequency counter on the fan wires -----------------------------------
    def start_meter(self):
        self.meter = {'time': 0.0, 'tach_low': 0.0, 'tach_falls': 0, 'supply_v': 0.0, 'supply_switching': False,
                      'pwm_v': 0.0, 'was_low': False}

    def _measure(self, lows, duty, a, b):
        m, cfg = self.meter, self.cfg
        dt = b - a
        m['time'] += dt
        m['tach_low'] += sum(e - s for s, e in lows)
        for s, _ in lows:
            if not (m['was_low'] and s <= a + 1e-12):
                m['tach_falls'] += 1
        m['was_low'] = bool(lows) and lows[-1][1] >= b - 1e-12
        supply = cfg.supply_v if cfg.driver == 'pwm4' else duty * cfg.supply_v
        m['supply_v'] += supply * dt
        m['supply_switching'] = cfg.driver == 'switched' and 0 < duty < 1
        m['pwm_v'] += duty * cfg.pullup_v * dt

    def read_meter(self):
        m, cfg = self.meter, self.cfg
        time = m['time']
        out = {
            '+V': (m['supply_v'] / time, 1 / self.pwm_period() if m['supply_switching'] else 0.0),
            'TACH': (cfg.pullup_v * (1 - m['tach_low'] / time), m['tach_falls'] / time),
        }
        if cfg.driver == 'pwm4':
            duty = self.duty(0)
            out['PWM'] = (m['pwm_v'] / time, 1 / self.pwm_period() if 0 < duty < 1 else 0.0)
        self.meter = None
        return out


def _hall_lows(phase, rate, a, b):
    # the Hall output pulls the line low for the first half of each pulse
    if rate <= 0:
        return [(a, b)] if phase % 1 < 0.5 else []
    out, k = [], math.floor(phase)
    end_phase = phase + rate * (b - a)
    while k < end_phase:
        s = a + (max(k, phase) - phase) / rate
        e = a + (min(k + 0.5, end_phase) - phase) / rate
        if s < e and k + 0.5 > phase:
            out.append((s, min(e, b)))
        k += 1
    return out


def _intersect(xs, ys):
    out, i, j = [], 0, 0
    while i < len(xs) and j < len(ys):
        s, e = max(xs[i][0], ys[j][0]), min(xs[i][1], ys[j][1])
        if s < e:
            out.append((s, e))
        if xs[i][1] < ys[j][1]:
            i += 1
        else:
            j += 1
    return out
