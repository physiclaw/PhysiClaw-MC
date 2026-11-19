# Firmware and operation

PCW-MC-01 uses stock FluidNC v4.1.1, Wi-Fi build for the classic ESP32, with
the [board configuration](config.yaml). Follow the
[programming instructions](../manufacturing/process.md#programming).
[FluidNC downloads](https://github.com/bdring/FluidNC/releases/tag/v4.1.1) ·
[FluidNC source and build configuration](https://github.com/bdring/FluidNC/tree/v4.1.1)

Before running a job, set each axis's steps per millimetre, direction, maximum
speed, acceleration, travel, and current for the machine. The supplied
configuration disables homing and soft limits. The virtual Z axis has no
physical output. The stepper drivers disable after 500 ms of idle time.

Complete the [first-article checks](../manufacturing/process.md#first-article-acceptance)
before operating the 12 V / 0.8 A solenoid. Use `$RM=0` to arm and `$RM=1` to disarm.
At 100% spindle override, `M3 S500` commands 50% duty and `M3 S1000` commands
100% duty. The provisional PWM frequency is 200 Hz. `M5` turns the output
off after queued motion finishes. Feed hold or a lost connection can leave
PWM active. Keep the 12 V disconnect accessible.
