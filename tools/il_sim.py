"""Tiny FX3 Instruction List simulator - enough of the instruction set to
test plc/encoder_fx3g_list.txt against a simulated VFD + motor + encoder.

Not a full PLC emulator: interrupts run between scans, timing is idealised.
"""
import re
import struct

def f2i(x):  # float -> 32-bit pattern (signed int)
    return struct.unpack('<i', struct.pack('<f', x))[0]

def i2f(i):
    return struct.unpack('<f', struct.pack('<I', i & 0xFFFFFFFF))[0]

def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v

class PLC:
    def __init__(self, path):
        self.prog = []
        for line in open(path):
            line = line.strip()
            if line:
                self.prog.append(line.split())
        self.labels = {}
        for i, ins in enumerate(self.prog):
            if re.fullmatch(r'[IP]\d+', ins[0]):
                self.labels[ins[0]] = i
        self.bits = {}      # 'M10' -> bool
        self.d = {}         # 'D0' -> 32-bit int pattern (we store dwords at base)
        self.timers = {}    # 'T0' -> [acc_ms, done]
        self.counter = 0    # C251
        self.edge = {}      # instruction index -> previous state
        self.first = True
        self.ms = 0

    # ---- operand access ----
    def bit(self, name):
        if name == 'M8000': return True
        if name == 'M8002': return self.first
        if name.startswith('T'): return self.timers.get(name, [0, False])[1]
        return self.bits.get(name, False)

    def dword(self, op):
        if op.startswith('K'): return int(op[1:])
        if op == 'C251': return self.counter
        return self.d.get(op, 0)

    def fval(self, op):
        if op.startswith('K'): return float(int(op[1:]))
        return i2f(self.dword(op))

    def setd(self, op, v):
        if op == 'C251': self.counter = s32(v); return
        self.d[op] = s32(v)

    def setf(self, op, x):
        self.setd(op, f2i(x))

    # ---- run a block from index until END/FEND/IRET/SRET ----
    def run(self, start, stop_at):
        acc = True; stack = []; blocks = []
        i = start
        cmp_ops = {'=': lambda a, b: a == b, '<>': lambda a, b: a != b,
                   '<': lambda a, b: a < b, '>': lambda a, b: a > b,
                   '<=': lambda a, b: a <= b, '>=': lambda a, b: a >= b}
        while i < len(self.prog):
            ins = self.prog[i]; op = ins[0]; a = ins[1:]
            if op in stop_at:
                return
            if re.fullmatch(r'[IP]\d+', op) or op == 'EI':
                i += 1; continue
            m = re.fullmatch(r'(LD|AND|OR)D(<=|>=|<>|=|<|>)', op)
            if m:
                v = cmp_ops[m.group(2)](self.dword(a[0]), self.dword(a[1]))
                kind = m.group(1)
                if kind == 'LD': blocks.append(acc); acc = v
                elif kind == 'AND': acc = acc and v
                else: acc = acc or v
            elif op in ('LD', 'LDI', 'LDP'):
                blocks.append(acc)
                v = self.bit(a[0])
                if op == 'LDI': v = not v
                if op == 'LDP':
                    prev = self.edge.get(i, False); self.edge[i] = v; v = v and not prev
                acc = v
            elif op in ('AND', 'ANI'):
                v = self.bit(a[0]); acc = acc and (v if op == 'AND' else not v)
            elif op in ('OR', 'ORI', 'ORP'):
                v = self.bit(a[0])
                if op == 'ORI': v = not v
                if op == 'ORP':
                    prev = self.edge.get(i, False); self.edge[i] = v; v = v and not prev
                acc = acc or v
            elif op == 'ANB':
                acc = blocks.pop() and acc
            elif op == 'ORB':
                acc = blocks.pop() or acc
            elif op == 'MPS': stack.append(acc)
            elif op == 'MRD': acc = stack[-1]
            elif op == 'MPP': acc = stack.pop()
            elif op == 'OUT':
                if a[0].startswith('T'):
                    t = self.timers.setdefault(a[0], [0, False])
                    if acc:
                        pre = self.dword(a[1]) * 100
                        t[1] = t[0] >= pre
                    else:
                        t[0] = 0; t[1] = False
                elif a[0] == 'C251':
                    pass
                else:
                    self.bits[a[0]] = acc
            elif acc:
                self.exec(op, a)
            # every output instruction keeps acc for following outputs
            i += 1

    def exec(self, op, a):
        if op == 'SET': self.bits[a[0]] = True
        elif op == 'RST':
            if a[0] == 'C251': self.counter = 0
            else: self.bits[a[0]] = False
        elif op == 'ZRST':
            p, s, e = a[0][0], int(a[0][1:]), int(a[1][1:])
            for n in range(s, e + 1): self.bits[f'{p}{n}'] = False
        elif op == 'DMOV': self.setd(a[1], self.dword(a[0]))
        elif op == 'DSUB': self.setd(a[2], self.dword(a[0]) - self.dword(a[1]))
        elif op == 'DINC': self.setd(a[0], self.dword(a[0]) + 1)
        elif op == 'DFLT': self.setf(a[1], float(self.dword(a[0])))
        elif op == 'DINT': self.setd(a[1], int(self.fval(a[0])))
        elif op == 'DEADD': self.setf(a[2], self.fval(a[0]) + self.fval(a[1]))
        elif op == 'DESUB': self.setf(a[2], self.fval(a[0]) - self.fval(a[1]))
        elif op == 'DEMUL': self.setf(a[2], self.fval(a[0]) * self.fval(a[1]))
        elif op == 'DEDIV': self.setf(a[2], self.fval(a[0]) / self.fval(a[1]))
        elif op == 'DECMP':
            x, y = self.fval(a[0]), self.fval(a[1]); b = int(a[2][1:])
            self.bits[f'M{b}'] = x > y; self.bits[f'M{b+1}'] = x == y; self.bits[f'M{b+2}'] = x < y
        elif op == 'CALL':
            self.run(self.labels[a[0]] + 1, ('SRET',))
        else:
            raise NotImplementedError(op)

    # ---- scan + time ----
    def scan(self, scan_ms):
        self.run(0, ('FEND', 'END'))
        self.first = False
        self.ms += scan_ms

    def tick_timers(self, ms):
        for name, t in self.timers.items():
            t[0] += ms  # timers only count while coil is ON; reset handled in OUT

    def interrupt(self, label):
        self.run(self.labels[label] + 1, ('IRET',))
