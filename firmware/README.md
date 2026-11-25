# Firmware and operation

PCW-MC-01 uses stock FluidNC v4.1.1, Wi-Fi build for the classic ESP32, with
the [board configuration](config.yaml). Follow the
[programming instructions](../manufacturing/process.md#programming).
[FluidNC downloads](https://github.com/bdring/FluidNC/releases/tag/v4.1.1) ·
[FluidNC source and build configuration](https://github.com/bdring/FluidNC/tree/v4.1.1)

This configuration is for the board marked **PCW-MC-01 R100** on the back,
with four 0.100 Ω shunts at R17–R20. Use the matching configuration on
earlier revisions, including the U8 board with fault feedback on GPIO34.

Before running a job, set each axis's steps per millimetre, direction, maximum
speed, acceleration, travel, and current for the machine. The supplied
configuration disables homing and soft limits. The virtual Z axis has no
physical output. The stepper drivers disable after 500 ms of idle time.

Use a regulated **12 V / 3 A adapter**. The supplied configuration sets
`run_amps: 0.600` on both axes, requesting 0.600 A RMS per phase. Keep
`r_sense_ohms: 0.100` for the R100 board. Upload the configuration and
restart. The current setting takes effect through UART. The startup macro
releases the interlock when a normal boot reaches Idle, so check the boot reports for both
driver addresses during commissioning before the first jog.
[Programming and UART checks](../manufacturing/process.md#programming) ·
[First-article acceptance](../manufacturing/process.md#first-article-acceptance)

Apply 12 V. After a normal boot, FluidNC is ready for motion and solenoid
commands. Both motors and the solenoid stay off until commanded. If power
was lost during a job, re-establish machine position before starting a new job.

For service at idle, `$RM=1` inhibits both outputs and `$RM=0` restores
normal operation. A normal power cycle also restores operation.

At 100% spindle override, `M3 S500` commands 50% duty and `M3 S1000` commands
100% duty. The configured PWM frequency is 1 kHz. `M5` turns the output
off after queued motion finishes. Feed hold or a lost connection can leave
PWM active. Keep the 12 V disconnect accessible.
