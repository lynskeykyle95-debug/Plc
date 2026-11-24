# GOT2000 screens (GT Designer3 - GOT2000)

## Project / connection settings

**Common > Controller Setting > CH1**

| Setting | RS-422 (FX3G built-in port) | Ethernet (FX3GE only) |
|---|---|---|
| Manufacturer | Mitsubishi Electric | Mitsubishi Electric |
| Controller Type | MELSEC-FX | MELSEC-FX |
| I/F | Standard I/F (RS422/485) | Standard I/F (Ethernet) |
| Driver | MELSEC-FX | Ethernet (FX), Gateway |
| Detail | Transmission speed 9600-115200 bps (115200 recommended) | PLC IP address + port; must match the FX3GE Ethernet parameters in GX Works2 |

Cable (RS-422): GOT RS-422 port to the FX3G mini-DIN 8 programming port, e.g. GT01-C30R4-8P.
Check the *GOT2000 Connection Manual (Mitsubishi Electric Products) - MELSEC-FX* for the cable for your GOT model.

## Screen 1 - "ENCODER" (monitor)

```
+-----------------------------------------------+
|  ENCODER MONITOR                     [SETUP>] |
|                                               |
|  POSITION   [  -1234.56 ] mm                  |
|  SPEED      [   1500.0  ] RPM                 |
|  LIN. SPEED [ 150000.0  ] mm/min              |
|  REVS       [    -12.345]                     |
|  RAW COUNT  [ -49382    ]                     |
|                                               |
|  (o) REVERSE   (o) HOMING ARMED   (o) HOMED   |
|                                               |
|  [ ZERO ]   [ PRESET ]   [ HOME ON Z ]        |
+-----------------------------------------------+
```

| Object | Device | Data type | Format / notes |
|---|---|---|---|
| Numerical Display - Position | D10 | 32-bit Real | 2 decimals |
| Numerical Display - Speed | D20 | 32-bit Real | 1 decimal |
| Numerical Display - Linear speed | D22 | 32-bit Real | 1 decimal |
| Numerical Display - Revs | D54 | 32-bit Real | 3 decimals |
| Numerical Display - Raw count | D0 | 32-bit Signed BIN | integer |
| Bit Lamp - Reverse | M30 | bit | |
| Bit Lamp - Homing armed | M20 | bit | blink when ON |
| Bit Lamp - Homed | M21 | bit | |
| Bit Switch - ZERO | M10 | Momentary | add confirmation dialog if wanted |
| Bit Switch - PRESET | M11 | Momentary | sets position to D208 |
| Bit Switch - HOME ON Z | M22 | Momentary | next Z pulse sets position to D208 |
| Go To Screen Switch - SETUP | screen 2 | | |

## Screen 2 - "SETUP"

```
+-----------------------------------------------+
|  ENCODER SETUP                     [<MONITOR] |
|                                               |
|  PULSES / REV       [   1000 ]                |
|  DISTANCE / REV     [ 100.00 ] mm             |
|  PRESET / HOME POS  [   0.00 ] mm             |
|  4x COUNTING        [ ON/OFF ]                |
+-----------------------------------------------+
```

| Object | Device | Data type | Format / notes |
|---|---|---|---|
| Numerical Input - Pulses/rev | D200 | 32-bit Signed BIN | limits 1 - 100000 |
| Numerical Input - Distance/rev | D204 | 32-bit Real | 2-3 decimals, must not be 0 (negative value reverses direction) |
| Numerical Input - Preset | D208 | 32-bit Real | 2 decimals |
| Bit Switch - 4x | M400 | Alternate | lamp on same device; press ZERO after changing |
| Go To Screen Switch - MONITOR | screen 1 | | |

Tip: put the setup screen behind a GOT security level (password) so operators can't change scaling.
