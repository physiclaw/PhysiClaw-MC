# Changelog

## Unreleased

- Move the solenoid flyback diode D4, rotate it 180°, and reroute the
  solenoid output and ground return.
- Widen part of the bottom-layer 12 V input trace (`VIN_RAW`) from 0.8 mm
  to 1.5 mm.
- Shorten the USB-C D− contact tie and adjust the USB data traces for the
  proposed JLC04161H-2116 stackup.
- Add a v1.0 schematic PDF, bill of materials, and board renders.
- Include the bare-board STEP model and FluidNC configuration in `build/`.
- Prefix the JLC manufacturing files with `PHYSICLAW-JLC`.
- Use Python 3.12 and run build and placement checks in CI on Linux, Windows,
  and macOS.
- Document contribution and hardware release steps.

## Hardware v1.0 engineering baseline

The four-layer PCW-MC-01 has two TMC2209 drivers, a protected solenoid output,
USB-C programming, and 15 test pads. The board uses FluidNC v4.1.1. Factory
acceptance and bench qualification are pending.
[v1.0 reference files](docs/v1.0/README.md)
