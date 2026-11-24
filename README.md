# Pastry laminator folding unit - FX3G + encoder + GOT2000

A motor drives the folder back and forth to lay the pastry sheet.
The **FX3G** reads the motor's encoder and runs the inverter forward/reverse between two end points.
The operator sets those end points on the **GOT2000**, and that sets the fold width.

```
        reverse end                 centre (0)                forward end
  -250 |<====== slow | fast ===========|=========== fast | slow ======>| +300
       ^            ^                                     ^            ^
   turn round   slowdown point                     slowdown point   turn round
```

* The operator enters **forward travel** and **reverse travel** from the centre, e.g. 300 and 250, so the width is 550.
  The values can be changed while the folder is running.
* The folder runs **fast** through the middle and drops to **slow** a set distance before each end.
  It stops (with an optional dwell) and reverses.
* The GOT shows where the folder **actually** turned round on each pass, so the overrun can be tuned out.

| File | What it is |
|---|---|
| `plc/encoder_fx3g_commented.txt` | The PLC program (Instruction List), with every rung explained |
| `plc/encoder_fx3g_list.txt` | The same program with no comments, ready to type into GX Works2 |
| `plc/device_map.csv` | Every input, output and register used |
| `got/screen_layout.md` | GOT connection settings and four screens: Run, Jog/Home, Setup, Alarms |
| `tools/il_sim.py`, `tools/test_folder.py` | Simulator that runs the program against a model motor/VFD/encoder |

## 1. Wiring

**FX3G inputs (all 8 inputs of a 14-point unit are used)**

| Input | Signal | Contact |
|---|---|---|
| X000 | Encoder A | |
| X001 | Encoder B | |
| X002 | Encoder Z (index) | optional, for homing |
| X003 | Start pushbutton | NO |
| X004 | Stop pushbutton | **NC** |
| X005 | E-stop relay / drive healthy | **NC** (ON = healthy) |
| X006 | Forward overtravel limit switch | **NC** (ON = clear) |
| X007 | Reverse overtravel limit switch | **NC** (ON = clear) |

**FX3G outputs to the inverter (Mitsubishi FR-series terminal names shown)**

| Output | Inverter terminal | Function |
|---|---|---|
| Y000 | STF | Forward run |
| Y001 | STR | Reverse run |
| Y002 | RH | Fast speed (set with Pr.4) |
| Y003 | RL | Slow speed (set with Pr.6), used for the approach to each end and for jog |

Wire the output COM to the inverter SD (sink) or PC (source) terminal, as the inverter manual describes.

* **Encoder:** a 24 V NPN or PNP (push-pull) encoder wires straight in.
  For NPN, connect S/S to 24V; for PNP, connect S/S to 0V.
  A 5 V line-driver encoder needs a converter.
  Use shielded cable, with the shield earthed at the PLC end.
* **Pulse rate limit:** about 30 kHz on C251.
  Pulse rate = PPR x max motor RPM / 60, e.g. 1000 PPR at 1500 RPM = 25 kHz.
* **Safety:** the E-stop **must** remove drive power or use the inverter's safe-torque-off (STO) through a safety relay.
  X005 only tells the PLC about it.
  Overtravel limit switches should also be in place: they are the backstop if the encoder fails.

## 2. What the program does

| Feature | How |
|---|---|
| Position | High-speed counter C251 (X000/X001), scaled to mm. 0 = centre of the fold |
| Reciprocating cycle | Fwd fast, fwd slow, stop, dwell, rev fast, rev slow, stop, dwell, repeat |
| Start direction | Heads away from whichever end it is nearer |
| Settings check | Won't start, and stops if running, if the travel exceeds the soft limits, the width is less than 2 x slowdown, or a value is negative |
| Referencing | Won't run in auto until ZERO (set centre here) or HOME ON Z has been done since power-up |
| Jog | Hold-to-run, slow speed, stays inside the soft limits once referenced |
| Turn-round record | D324/D326 show the real reversal points of the last pass |
| Pass counter | D240 |
| Faults (latched, reset from GOT) | E-stop/drive, overtravel in auto, **stall/encoder dead** (no counts for 1 s while driving), **wrong direction** (count going the wrong way for 3 s) |
| Interlocks | Forward and reverse can never be on together; ZERO/PRESET are ignored while moving |

## 3. Commissioning

1. **Load the PLC:** follow the steps under "Loading the PLC program" below.
2. **Inverter:**
   * Set Pr.4 (fast) and Pr.6 (slow) frequencies, and Pr.7/Pr.8 accel/decel.
   * Run it from its own panel first.
3. **Encoder direction:**
   * Jog FWD from the GOT. The position (D10) must **increase**.
   * If it decreases, swap encoder A and B. Don't use a negative distance per rev.
   * Wrong direction trips the M58 alarm.
4. **Scaling (Setup screen):**
   * Enter pulses per rev (from the encoder label) and distance per rev.
   * Distance per rev is the motor rev to folder travel, e.g. pulley circumference / gearbox ratio.
   * Jog a measured distance and check the position.
5. **Soft limits:** enter max forward / reverse travel just inside the overtravel switches.
   Until these are set, the "settings invalid" lamp stays on and nothing runs in auto.
6. **Centre:** jog to the centre of the fold and press SET CENTRE (ZERO).
   Or use HOME ON Z: set the home position value, press HOME ON Z, then jog slowly over the Z pulse.
7. **Slowdown distance:** must be **longer than the distance the folder takes to slow from fast to slow speed**.
   Rough figure: fast speed (mm/s) x decel time (s) / 2.
   If it's too short, the folder overshoots the end and can hit the limit switch.
8. **Overrun compensation:** run in auto and watch ACTUAL TURN on the Run screen.
   If it reverses at 302.0 when set to 300.0, enter 2.0.
9. **Dwell:** 0 reverses immediately.
   A few tenths of a second gives a cleaner stop at the fold, and also lets the inverter stop before it reverses.

## 4. Loading the PLC program (GX Works2)

> GX Works3 does **not** support FX3. Use GX Works2 (free with the MELSOFT suite) or GX Developer.

1. *New Project*: Simple Project, Series **FXCPU**, Type **FX3G/FX3GC**, Ladder.
2. Switch the program to **List** view and type in `plc/encoder_fx3g_list.txt`.
   The pointers `P0`, `I650`, `I201` each go on their own line.
3. Convert (F4), then Write to PLC (Program + Parameters), then RUN.
4. Optional: paste `plc/device_map.csv` (columns 1 and 4) into the Device Comment editor.

**Retained settings:**
* All GOT settings (D200-D244) and M400 sit in the FX3G EEPROM-latched ranges, so they survive power-off.
* Referencing (M24) is deliberately **not** retained: the encoder can't see movement while the power is off.

## 5. Testing without hardware

```
python3 tools/test_folder.py
```

This runs the actual instruction list in a simple simulator, with a model inverter (ramps, fast/slow speeds), motor, encoder and limit switches.
It checks:
* the folder reciprocates between the set end points;
* width changes while running;
* invalid settings block start;
* stop, E-stop and fault reset;
* the wrong-direction and dead-encoder faults;
* jog soft limits.

It is a logic check, not a substitute for commissioning on the real machine.

## 6. Limits and possible upgrades

* **End-point accuracy** depends on the slow speed and the scan time (a few ms).
  At a slow speed of 100 mm/s it is about 0.5 mm, before overrun compensation.
* **Speed from the GOT:** fast/slow speeds are currently set in the inverter.
  With an FX3G-485-BD and RS-485 to the inverter, the GOT could set them directly.
  An FX3G-4DA-ADP analog output would also work.
* **Smoother reversal:** a servo would give exact, adjustable motion profiles instead of fast/slow steps.
  The FX3G has pulse outputs on transistor models.
