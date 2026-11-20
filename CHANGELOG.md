# Changelog

## Unreleased

- Use 1.00 × 2.05 mm plated slots at J1, 0.15 mm component-outline
  silkscreen strokes and 0.50 mm copper-to-edge clearance.
- Move the F1 vias and 16 other vias away from SMT lands. Add thermal
  relief to four 0603 ground pads.
- Stitch each L3 ground region to L2 at two or more points. Fill around
  thermal holes, U6, U7 and the interlock. Add redundant feeds to the L3
  3.3 V pours and connect the U6 and U7 pours to adjacent regions.
- Rotate U9 and R37, route SOL_SAFE on L1 and carry SOL_CMD over L3 ground.
  Move TP9, TP12 and TP5 onto their traces. The seven interlock nets now use
  11 vias and 184.6 mm of trace, down from 26 vias and 243.7 mm.
- Tie the reversible USB-C contacts on L1 and extend L3 ground under VBUS.
  Move the U3 data vias off-pad. Resin-fill and copper-cap the four J2–U3
  data vias (0.60 mm lands, 0.30 mm drills) and 50 thermal holes.
- Add two 49.9 Ω shunts to U7 port 1 and move C29 and its 3.3 V via.
- Use 4.7 µF 0805 capacitors on both TMC2209 5VOUT rails. Stitch ground
  near the UART and reset transitions, run the Y_A2 escape over V12 and
  straighten Y_DIR.
- Move the U1/C2 12 V via, simplify the R8 and U6 3.3 V feeds, route DTR
  into R8 with one 45° segment and remove two RTS layer changes at R6.
- Move the solenoid flyback diode D4, rotate it 180°, and reroute the
  solenoid output and ground return.
- Widen part of the bottom-layer 12 V input trace (`VIN_RAW`) from 0.8 mm
  to 1.5 mm.
- Shorten the USB-C D− tie, tune USB routing for JLC04161H-7628, and stitch
  ground near the J2 crossover.
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
