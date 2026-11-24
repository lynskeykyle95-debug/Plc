# GOT2000 screens (GT Designer3 - GOT2000)

## Connection settings

**Common > Controller Setting > CH1**

| Setting | RS-422 (FX3G built-in port) | Ethernet (FX3GE only) |
|---|---|---|
| Manufacturer | Mitsubishi Electric | Mitsubishi Electric |
| Controller Type | MELSEC-FX | MELSEC-FX |
| I/F | Standard I/F (RS422/485) | Standard I/F (Ethernet) |
| Driver | MELSEC-FX | Ethernet (FX), Gateway |
| Detail | 115200 bps | PLC IP address; must match the FX3GE Ethernet parameters |

Cable: GOT RS-422 port to the FX3G mini-DIN 8 programming port (e.g. GT01-C30R4-8P).
Check the *GOT2000 Connection Manual - MELSEC-FX* for the cable that suits your GOT model.

Data types:
* Every value marked *Real* is **32-bit Real (floating point)**.
* Counts are **32-bit Signed**.
* D228 is **16-bit Signed**.

---

## Screen 1 - RUN (operator)

```
+--------------------------------------------------------+
|  FOLDER                    [READY] [RUNNING] [FAULT]   |
|                                                        |
|   REVERSE  <------------- 0 ------------->  FORWARD    |
|   [ 250.0 ] mm          [ +12.3 ]          [ 300.0 ] mm|
|   (input)               position           (input)     |
|                                                        |
|   WIDTH  [ 550.0 ] mm        PASSES [  1234 ] [RESET]  |
|   ACTUAL TURN  rev [-250.5]   fwd [ 300.5]             |
|                                                        |
|   [ START ]        [ STOP ]          [JOG/HOME>] [SETUP>]
+--------------------------------------------------------+
```

| Object | Device | Type | Notes |
|---|---|---|---|
| Numerical Input - Forward travel | D220 | Real | 1 decimal; upper limit = your max fwd travel; **can be changed while running** |
| Numerical Input - Reverse travel | D222 | Real | enter a positive value; the folder turns at minus this |
| Numerical Display - Position | D10 | Real | 1 decimal |
| Numerical Display - Width | D244 | Real | |
| Numerical Display - Passes | D240 | 32-bit Signed | |
| Bit Switch - Reset passes | M48 | Momentary | |
| Numerical Display - Actual fwd turn | D324 | Real | where it really turned round |
| Numerical Display - Actual rev turn | D326 | Real | |
| Bit Switch - START | M40 | Momentary | |
| Bit Switch - STOP | M41 | Momentary | |
| Bit Lamp - READY | M43 | | green |
| Bit Lamp - RUNNING | M100 | | |
| Bit Lamp - FAULT | M50 | | red, blink |
| Bit Lamp - SETTINGS INVALID | M52 | | show text "CHECK TRAVEL SETTINGS" |
| Bit Lamp - NOT REFERENCED | M24 (OFF state) | | show text "PRESS ZERO / HOME" when OFF |
| Optional: Bar graph / slider | D10 | Real | range = -max rev travel to +max fwd travel; a moving bar shows the folder position |

## Screen 2 - JOG / HOME

```
+--------------------------------------------------------+
|  JOG / HOME                                 [< RUN]    |
|   POSITION [ +12.3 ] mm       SPEED [  60.0 ] RPM      |
|                                                        |
|   [ <<< JOG REV ]                 [ JOG FWD >>> ]      |
|                                                        |
|   [ SET CENTRE HERE (ZERO) ]   [ HOME ON Z ]           |
|   (o) REFERENCED  (o) HOMING ARMED  (o) HOMED          |
+--------------------------------------------------------+
```

| Object | Device | Type | Notes |
|---|---|---|---|
| Bit Switch - JOG REV | M45 | Momentary | hold to run, slow speed |
| Bit Switch - JOG FWD | M44 | Momentary | |
| Bit Switch - SET CENTRE (ZERO) | M10 | Momentary | add a confirmation dialog |
| Bit Switch - HOME ON Z | M22 | Momentary | then jog slowly over the Z pulse |
| Lamps | M24 / M20 / M21 | | |
| Position / Speed | D10 / D20 | Real | |

## Screen 3 - SETUP (engineer - put a GOT security level / password on it)

| Object | Device | Type | Notes |
|---|---|---|---|
| Encoder pulses per rev | D200 | 32-bit Signed | from the encoder label |
| Distance per motor rev | D204 | Real | must be > 0 |
| 4x counting | M400 | Alternate | press ZERO after changing |
| Slowdown distance | D224 | Real | must exceed the fast-speed stopping distance |
| Overrun compensation | D226 | Real | stop this much early; tune from the ACTUAL TURN displays |
| Dwell at each end | D228 | 16-bit Signed | 0.1 s units (5 = 0.5 s; 0 = reverse immediately) |
| Max forward travel | D234 | Real | soft limit - **must be set or nothing will run** |
| Max reverse travel | D236 | Real | soft limit (positive number) |
| Home position value | D208 | Real | position assigned at the Z pulse / PRESET |

## Screen 4 - ALARMS

Bit lamps or a Bit Alarm (User Alarm) object, with M51 FAULT RESET as a momentary switch:

| Device | Message |
|---|---|
| M54 | E-STOP PRESSED OR DRIVE FAULT |
| M55 | FORWARD OVERTRAVEL LIMIT HIT |
| M56 | REVERSE OVERTRAVEL LIMIT HIT |
| M57 | MOTOR NOT MOVING / ENCODER NOT COUNTING |
| M58 | WRONG DIRECTION - CHECK ENCODER A/B OR MOTOR WIRING |
