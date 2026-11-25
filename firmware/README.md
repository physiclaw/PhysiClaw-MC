# Firmware and operation

PCW-MC-01 uses stock FluidNC v4.1.1, Wi-Fi build for the classic ESP32, with
the [board configuration](config.yaml). Follow the
[programming instructions](../manufacturing/process.md#programming).
[FluidNC downloads](https://github.com/bdring/FluidNC/releases/tag/v4.1.1) ·
[FluidNC source and build configuration](https://github.com/bdring/FluidNC/tree/v4.1.1)

This configuration is for boards fitted with Q6, Q7 and four 0.100 Ω
current-sense resistors at R17–R20. Use the matching configuration on
earlier revisions, including the U8 board with fault feedback on GPIO34.

## CoreXY motion

Send toolhead X/Y coordinates to FluidNC. With both motors fixed to the frame
and `x_scaler: 1.0`, FluidNC drives the two belts as follows.
[FluidNC CoreXY guide](https://github.com/bdring/fluidnc-wiki-content/blob/main/config/kinematics.md#corexy)

| Connector and silkscreen | Motor and belt | FluidNC driver | UART address | Motor travel |
| --- | --- | --- | --- | --- |
| J3 · X MOTOR | Right motor B, upper belt | `axes.x.motor0` | 0 | X + Y |
| J4 · Y MOTOR | Left motor A, lower belt | `axes.y.motor0` | 1 | X − Y |

Both drives use 80 steps/mm, assuming 200 full steps/rev and 16 microsteps
with a 20-tooth pulley and 2 mm belt pitch (200 × 16 ÷ 40 mm). Nominal
toolhead travel is 110 mm along the crossbeam (X) and 200 mm along the
rails (Y). Both axes have a maximum speed of 10000 mm/min and an acceleration
of 1000 mm/s². There are no endstops, so homing and soft limits are disabled.
The virtual Z axis has no physical output.
[PhysiClaw gantry dimensions](https://github.com/physiclaw/PhysiClaw/blob/1a2b667bf5179a41c1ae34879fe192f71abc1437/hardware/assembly/travel_ranges.py)

### Wiring

Disconnect DC and USB before connecting the motors. At each disconnected
board-end plug, check for one winding across pins 1–2 and the other across
3–4, with no continuity between pairs. Seat the keyed four-pin plugs at J3
and J4. [Motor harness pinout](../manufacturing/process.md#motor-harnesses)

Connect the 12 V solenoid across J5 pin 1 (switched +12 V) and pin 2 (GND).
Keep the separate stylus housing earth lead. J1 takes a regulated 12 V / 3 A
adapter with a 5.5 × 2.5 mm centre-positive plug. J2 takes a USB-C data
cable. The mounting hole centres are 62 × 42 mm apart.

### First jogs

Start near the centre with the solenoid off. Run each relative jog separately
and observe the carriage and both pulleys. Check the sign and measure the
displacement on each commanded axis.

| FluidNC jog | Expected toolhead displacement | Motors turning |
| --- | --- | --- |
| `$J=G91 G21 X5 Y5 F200` | +5 mm X, +5 mm Y | Right B (J3) only |
| `$J=G91 G21 X5 Y-5 F200` | +5 mm X, −5 mm Y | Left A (J4) only |
| `$J=G91 G21 X5 F200` | 5 mm to the right along the crossbeam | A and B |
| `$J=G91 G21 Y5 F200` | 5 mm away from the fixed motor beam | A and B |

If the wrong pulley turns on a diagonal, power off and check the J3/J4
harness assignment. If the intended pulley turns but that diagonal runs in
reverse, invert its `direction_pin` polarity, upload the file and restart.
Repeat the jogs after any direction change. Verify the configured speed
and acceleration with the payload, including moves along both diagonals.
The PhysiClaw host requests swipe speeds of 3000–10000 mm/min.
[PhysiClaw host motion settings](https://github.com/physiclaw/PhysiClaw/blob/1a2b667bf5179a41c1ae34879fe192f71abc1437/src/physiclaw/core/hardware/arm.py)

## Motor current and outputs

Use a regulated **12 V / 3 A adapter**. The supplied configuration sets
`run_amps: 0.800` on both motors, requesting 0.800 A RMS per phase. Keep
`r_sense_ohms: 0.100` for the fitted 0.100 Ω shunts. Upload the configuration and
restart. The current setting takes effect through UART. The startup macro
releases the interlock when a normal boot reaches Idle, so check the boot reports for both
driver addresses during commissioning before the first jog.
[Programming and UART checks](../manufacturing/process.md#programming) ·
[First-article acceptance](../manufacturing/process.md#first-article-acceptance)

During a pure X or Y move both drivers use running current. On a 45° diagonal
one motor stops stepping and can settle to the configured holding current
(`hold_amps: 0.150`) while the other runs. After 500 ms of machine idle,
FluidNC disables both drivers.

Apply 12 V. After a normal boot, FluidNC is ready for motion and solenoid
commands. Both motors and the solenoid stay off until commanded. If power
was lost during a job, re-establish machine position before starting a new job.

For service at idle, `$RM=1` inhibits both outputs and `$RM=0` restores
normal operation. A normal power cycle also restores operation.

At 100% spindle override, `M3 S500` commands 50% duty and `M3 S1000` commands
100% duty. The configured PWM frequency is 1 kHz. `M5` turns the output
off after queued motion finishes. Feed hold or a lost connection can leave
PWM active. Keep the 12 V disconnect accessible.
