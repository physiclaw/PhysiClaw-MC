# Changelog

## Unreleased

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
