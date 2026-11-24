"""Simulate the folding unit: VFD + motor + encoder, run the PLC program,
check that it reciprocates between the operator's end points.

Run:  python3 tools/test_folder.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from il_sim import PLC, f2i

HERE = os.path.dirname(__file__)
PROG = os.path.join(HERE, '..', 'plc', 'encoder_fx3g_list.txt')

SCAN_MS = 5
PPR = 1000            # 1x counting -> 1000 counts/rev
MM_PER_REV = 100.0    # 0.1 mm per count
FAST_RPM = 600        # VFD high speed  (1000 mm/s)
SLOW_RPM = 60         # VFD low speed   (100 mm/s)
ACCEL_RPM_PER_S = 6000   # VFD accel/decel: 0 -> 600 rpm in 0.1 s


class Machine:
    def __init__(self, invert_encoder=False):
        self.plc = PLC(PROG)
        self.rpm = 0.0
        self.counts = 0.0        # true shaft position in counts
        self.invert = invert_encoder
        self.encoder_dead = False
        self.inputs = {'X003': False, 'X004': True, 'X005': True, 'X006': True, 'X007': True}
        self.fwd_limit_mm = 450.0
        self.rev_limit_mm = -450.0
        self.since_irq = 0
        p = self.plc
        p.d['D200'] = PPR
        p.d['D204'] = f2i(MM_PER_REV)

    def pos_mm(self):
        return self.counts / PPR * MM_PER_REV

    def step(self):
        p = self.plc
        mm = self.pos_mm()
        self.inputs['X006'] = mm < self.fwd_limit_mm
        self.inputs['X007'] = mm > self.rev_limit_mm
        p.bits.update(self.inputs)
        p.scan(SCAN_MS)
        p.tick_timers(SCAN_MS)
        y0, y1 = p.bits.get('Y000'), p.bits.get('Y001')
        assert not (y0 and y1), 'Y000 and Y001 both ON'
        speed = FAST_RPM if p.bits.get('Y002') else SLOW_RPM if p.bits.get('Y003') else 0
        target = speed if y0 else -speed if y1 else 0
        dv = ACCEL_RPM_PER_S * SCAN_MS / 1000
        self.rpm += max(-dv, min(dv, target - self.rpm))
        self.counts += self.rpm / 60 * PPR * SCAN_MS / 1000
        if not self.encoder_dead:
            p.counter = int(round(-self.counts if self.invert else self.counts))
        self.since_irq += SCAN_MS
        if self.since_irq >= 50:
            self.since_irq = 0
            p.interrupt('I650')

    def run_ms(self, ms):
        for _ in range(ms // SCAN_MS):
            self.step()

    def press(self, bit, ms=50):
        self.plc.bits[bit] = True
        self.run_ms(ms)
        self.plc.bits[bit] = False
        self.run_ms(ms)


def setup(m, fwd=300.0, rev=250.0):
    d = m.plc.d
    d['D220'] = f2i(fwd); d['D222'] = f2i(rev)
    d['D224'] = f2i(80.0)    # slowdown distance (> fast-speed decel distance)
    d['D226'] = f2i(0.0)     # overrun comp
    d['D228'] = 3            # 0.3 s dwell
    d['D234'] = f2i(400.0); d['D236'] = f2i(400.0)


def test_reciprocates():
    m = Machine()
    setup(m)
    m.run_ms(200)
    assert not m.plc.bits.get('M43'), 'should not be READY before zeroing'
    m.press('M10')                                  # ZERO
    assert m.plc.bits.get('M24'), 'referenced after zero'
    assert m.plc.bits.get('M43'), f"not READY, M52={m.plc.bits.get('M52')} M50={m.plc.bits.get('M50')}"
    m.press('M40')                                  # START
    assert m.plc.bits.get('M100')
    peaks = []; last_dir = 0; prev = m.pos_mm()
    for _ in range(int(20000 / SCAN_MS)):
        m.step()
        cur = m.pos_mm(); d = (cur > prev) - (cur < prev)
        if d and last_dir and d != last_dir:
            peaks.append(round(prev, 1))
        if d: last_dir = d
        prev = cur
    print('turn-round points (mm):', peaks[:8])
    print('actual fwd/rev recorded on GOT: %.1f / %.1f' % (m.plc.fval('D324'), m.plc.fval('D326')))
    print('passes D240 =', m.plc.d.get('D240'))
    assert len(peaks) >= 6, 'not reciprocating'
    for pk in peaks:
        assert 295 <= pk <= 310 or -260 <= pk <= -245, f'turn-round {pk} outside tolerance'
    assert m.plc.d.get('D240', 0) >= 6
    assert abs(m.plc.fval('D324') - max(peaks)) < 2
    # change width while running
    m.plc.d['D220'] = f2i(150.0); m.plc.d['D222'] = f2i(150.0)
    m.run_ms(6000)
    mx = -1e9; mn = 1e9
    for _ in range(int(6000 / SCAN_MS)):
        m.step(); mx = max(mx, m.pos_mm()); mn = min(mn, m.pos_mm())
    print('after width change: %.1f .. %.1f' % (mn, mx))
    assert 145 <= mx <= 160 and -160 <= mn <= -145
    m.press('M41')                                   # STOP
    m.run_ms(1000)
    assert not m.plc.bits.get('Y000') and not m.plc.bits.get('Y001')
    assert not m.plc.bits.get('M100')


def test_invalid_settings_block_start():
    m = Machine(); setup(m, fwd=500.0)              # > max fwd travel 400
    m.press('M10'); m.press('M40')
    assert m.plc.bits.get('M52') and not m.plc.bits.get('M100')


def test_wrong_direction_hits_overtravel():
    # A/B swapped: motor runs away, the hardware limit switch must stop it
    m = Machine(invert_encoder=True); setup(m)
    m.press('M10'); m.press('M40')
    m.run_ms(5000)
    assert m.plc.bits.get('M55'), 'fwd overtravel fault expected'
    assert not m.plc.bits.get('Y000') and not m.plc.bits.get('Y001')


def test_wrong_direction_fault():
    # same, with limit switches far away: software direction check trips
    m = Machine(invert_encoder=True); setup(m)
    m.fwd_limit_mm, m.rev_limit_mm = 1e9, -1e9
    m.press('M10'); m.press('M40')
    m.run_ms(5000)
    assert m.plc.bits.get('M58'), 'wrong-direction fault expected'
    assert not m.plc.bits.get('Y000') and not m.plc.bits.get('Y001')


def test_stall_fault():
    m = Machine(); setup(m)
    m.press('M10'); m.press('M40')
    m.run_ms(300)
    # encoder cable cut: counter freezes
    m.fwd_limit_mm, m.rev_limit_mm = 1e9, -1e9
    start = m.pos_mm()
    m.encoder_dead = True
    m.run_ms(3000)
    print('encoder dead: travelled %.0f mm blind before stall fault' % (m.pos_mm() - start))
    assert m.plc.bits.get('M57'), 'stall fault expected'
    assert not m.plc.bits.get('Y000') and not m.plc.bits.get('Y001')


def test_estop_and_reset():
    m = Machine(); setup(m)
    m.press('M10'); m.press('M40'); m.run_ms(500)
    m.inputs['X005'] = False; m.run_ms(100)
    assert m.plc.bits.get('M54') and not m.plc.bits.get('Y000') and not m.plc.bits.get('M100')
    m.inputs['X005'] = True; m.press('M51')
    assert not m.plc.bits.get('M50')


def test_jog_soft_limit():
    m = Machine(); setup(m)
    m.press('M10')
    m.plc.bits['M44'] = True
    m.run_ms(8000)
    m.plc.bits['M44'] = False
    m.run_ms(2000)
    print('jog fwd stopped at %.1f mm (soft limit 400)' % m.pos_mm())
    assert 395 <= m.pos_mm() <= 410


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn(); print('PASS', name)
