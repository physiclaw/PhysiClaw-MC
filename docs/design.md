# PCW-MC-01 design notes

## Power and control

- A single 12 V adapter supplies both motors, the solenoid, and the logic.
  The 2.5 A steady-state input target covers all three loads. An AP63203 buck
  regulator supplies 3.3 V to the logic.
- The ESP32-WROOM-32UE-N4 uses an external antenna. A CH340C bridges the
  ESP32's UART to USB-C for programming and serial communication. Each
  TMC2209 uses direct STEP and DIR signals, a dedicated current-sense
  circuit, and a separate address on the shared UART.
- A TPS1H200A switches the positive coil lead and reports faults. A flyback
  diode carries coil current when the switch opens. The hardware interlock
  inhibits the drivers and solenoid during reset and until the operator
  arms the board through FluidNC.

[Read the schematic](v1.0/schematic.pdf)

## Layout and enclosure

L2 provides a continuous ground reference. L3 carries power and provides a
local ground reference for the L4 USB crossover and STEP/DIR routes. Keep
ground stitching vias close to signal vias.
[Fabrication requirements](../manufacturing/process.md#bare-board-fabrication)

Use `build/PCW-MC-01-bare-board.step` to locate the outline and four M3
mounting holes. Allow space above the board for motor plugs, on the left
for solenoid wiring, and on the right for DC and USB-C plugs. Leave room for
the antenna cable and probe access on both sides. Verify fit with the actual
components and cables.

## USB-C

J2 ties A6 to B6 (D+) and A7 to B7 (D−). CC1 and CC2 each have a 5.1 kΩ
pull-down. The USB Type-C specification recommends a 3.5 mm maximum
shorting trace length. The layout check measures the planar copper path
between each pair of contacts. Electrical validation includes the via
transitions. [USB Type-C Rev 2.4, Table 3-5, note 2]

Keep the USBLC6-2 (U3) close to J2 with a short ground return. VBUS connects
to U3's clamp rail and enables the TS3USB221A switch (U7) through Q5. The
CH340C (U4) runs from the board's 3.3 V rail with V3 and VCC tied together.
[USBLC6-2 datasheet] · [CH340C datasheet]

The L1 USB trunks use 0.28 mm traces and a 0.18 mm edge gap over L2 ground.
JLC estimates 89.4 Ω for these uniform sections on JLC04161H-7628. Check the
short 0.18–0.20 mm pad fanouts and nearby same-layer copper separately.

Each J2 data pad connects to its via along the X axis on L1. The D− vias
are offset 0.259 mm toward the connector opening relative to the D+ vias.
The L4 ties use 0.20 mm traces with mirrored 45° bends. Each tie connects
two vias with 0.40 mm lands and 0.30 mm drills.

L3 ground provides the reference for both L4 ties outside the signal via
antipads. Four nearby ground vias stitch L2, L3 and L4 together. Each has
a 0.60 mm land and a 0.30 mm drill.
[TI USB layout guidance] · [Fabrication requirements](../manufacturing/process.md#bare-board-fabrication)

[USB Type-C Rev 2.4, Table 3-5, note 2]:
  https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/USB-Type_2D00_C-Spec-R2.4-_2D00_-October-2024.pdf
[USBLC6-2 datasheet]: https://www.st.com/resource/en/datasheet/usblc6-2.pdf
[CH340C datasheet]:
  https://datasheet.lcsc.com/datasheet/pdf/e2f14e51aaa60c793f1f0cbc8a5d5faa.pdf?productCode=C84681
[TI USB layout guidance]: https://www.ti.com/lit/an/slla414a/slla414a.pdf
