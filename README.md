# FX3G encoder -> GOT2000

Reads an incremental (A/B quadrature) encoder with a Mitsubishi **FX3G** high-speed counter.
It scales the count to position and speed and shows the results on a **GOT2000** HMI.

| File | What it is |
|---|---|
| `plc/encoder_fx3g_commented.txt` | The PLC program in Instruction List, with every rung explained |
| `plc/encoder_fx3g_list.txt` | The same program with no comments, ready to type in List mode |
| `plc/device_map.csv` | Every device used (paste into GX Works2 Device Comment) |
| `got/screen_layout.md` | GT Designer3 connection settings and the two screens with their objects |

## 1. Hardware / wiring

| Encoder signal | FX3G input |
|---|---|
| A | X000 |
| B | X001 |
| Z (index, optional) | X002 |
| 0 V / 24 V | per sink/source below |

* FX3G 24 V DC inputs are **sink or source** depending on how the S/S terminal is wired:
  * **NPN** (open-collector) encoder: S/S to **24V**, encoder 0 V to **0V**.
  * **PNP** encoder: S/S to **0V**.
* **Line-driver (RS-422 / 5 V differential)** encoders can't be wired straight to the inputs.
  Use a line-driver-to-open-collector converter, or an encoder with 24 V push-pull/NPN outputs.
* Use shielded twisted-pair cable and earth the shield at the PLC end only.
* **Frequency limit:** C251 on X000/X001 handles roughly 30 kHz (2-phase) on the FX3G main unit.
  Check the *FX3G User's Manual - Hardware Edition* for your exact model.
  Required frequency = PPR x max RPM / 60.
  For example, 1000 PPR at 1800 RPM is 30 kHz, which is right at the limit.

## 2. How the program works

* **C251** is a 32-bit hardware quadrature counter (A = X000, B = X001).
  The `OUT C251 K2147483647` coil keeps it running.
  **M8198** switches it to 4-edge (x4) counting, controlled from the GOT through **M400**.
* Every scan, the raw count is converted to floating point:
  * `revs = count / (PPR x 1 or 4)`
  * `position = revs x distance_per_rev + offset`
* **Speed:** the timer interrupt **I650** runs exactly every 50 ms and stores the counts moved in that window (D30).
  * `RPM = D30 / counts_per_rev x 1200`
  * `linear speed = RPM x distance_per_rev`
* **Zero / Preset:** the main program sets a request flag (M12).
  The counter is reset inside I650, so the speed sample never sees a false jump.
* **Home on Z (optional):** press HOME ON Z to arm homing.
  On the next Z pulse, input interrupt **I201** (X002 rising) resets the counter and sets position = preset value.
* **Settings are retained** through power loss:
  * D200-D215 sit in the FX3G EEPROM-latched range (D128-D1099).
  * M400 sits in the latched range (M384-M1535).
  * If the settings are blank, defaults of 1000 PPR and 100.0 units/rev are loaded.

### Device map (GOT side)

| Device | Type | Meaning |
|---|---|---|
| D0 | 32-bit signed | Raw count |
| D10 | 32-bit real | Position |
| D20 | 32-bit real | Speed (RPM) |
| D22 | 32-bit real | Linear speed (units/min) |
| D54 | 32-bit real | Revolutions |
| D200 | 32-bit signed | **Setting:** pulses per rev |
| D204 | 32-bit real | **Setting:** distance per rev (negative = invert direction) |
| D208 | 32-bit real | **Setting:** preset / home value |
| M400 | bit (alternate) | **Setting:** 4x counting |
| M10 / M11 / M22 | bit (momentary) | ZERO / PRESET / HOME ON Z |
| M30 / M20 / M21 | bit | Reverse / homing armed / homed lamps |

## 3. Loading the PLC program (GX Works2)

> GX Works3 does **not** support the FX3 series. Use GX Works2 (or GX Developer).

1. New project: *Simple Project*, Series **FXCPU**, Type **FX3G/FX3GC** (the FX3GE uses the FX3G type), Ladder.
2. Open the program, then right-click > **Switch to List** (or use the List view).
3. Type in the lines of `plc/encoder_fx3g_list.txt` one per line.
   For the interrupt pointers `I650` / `I201`, type the pointer on its own line.
   In Ladder view the pointers appear at the left rail.
4. **Convert/Compile** (F4).
5. Optional: open *Device Comment*, then paste columns 1 and 4 of `plc/device_map.csv`.
6. PLC parameters: nothing special is needed.
   The program fixes its own HSC and interrupt settings, and the latched ranges are the defaults.
7. Online > Write to PLC (Program + Parameters + Device comments), then RUN.

## 4. GOT2000 (GT Designer3)

Follow `got/screen_layout.md`. In short:

1. Controller Setting CH1 = **MELSEC-FX**, I/F **Standard I/F (RS422/485)**, driver **MELSEC-FX**, 115200 bps.
2. Cable from the GOT RS-422 port to the FX3G mini-DIN 8 programming port.
   On an FX3GE you can use Ethernet instead.
3. Build the Monitor and Setup screens with the objects/devices listed.
   Set the float values to **Real** and the counts to **32-bit Signed**.
4. Write the project to the GOT (USB or SD card).

Because the GOT uses the PLC's programming port, use the GOT's **FA transparent** function to go online with GX Works2 through the GOT's USB port.

## 5. Commissioning checklist

1. Monitor X000/X001 in GX Works2 and turn the shaft slowly. Both inputs should toggle.
2. Turn forward. **D0 should increase.**
   If it decreases, swap A and B, or enter a negative distance/rev.
3. Turn exactly one revolution. D0 should change by PPR (or 4 x PPR with 4x ON).
4. Set distance/rev on the Setup screen.
   For example: roller circumference = pi x diameter; leadscrew pitch x gearbox ratio.
5. Press ZERO, move a known distance, and check the position against a ruler.
6. Run at a known speed and check RPM.

## 6. Notes / limits

* **Speed resolution** = 1 count per 50 ms.
  At 1000 PPR with 1x counting that is 1.2 RPM per count, and 4x counting improves it to 0.3 RPM.
  For a steadier display at low speed, raise the GOT refresh interval or average D20.
* **Float precision:** 32-bit floats are exact up to about 16.7 million counts.
  Beyond that the position resolution gets coarser, so ZERO/home periodically on long continuous runs.
* **Power-off movement:** an incremental encoder can't see movement while the PLC is off.
  After power-up, press ZERO or HOME ON Z if the machine might have moved.
* **Absolute encoders** (SSI/BiSS etc.) need a different interface module and aren't covered here.
