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

J2 ties its two D+ contacts together and does the same for D−. Each CC pin
has its own 5.1 kΩ pull-down. Use 3.5 mm for the planar trace check on
each tie and include the vias in electrical validation.
[USB Type-C Rev 2.4, Table 3-5]

Keep the USBLC6-2 (U3) close to J2 with a short ground return. VBUS connects
to U3's clamp rail and enables the TS3USB221A switch (U7) through Q5. The
CH340C (U4) runs from the board's 3.3 V rail with V3 and VCC tied together.
[USBLC6-2 datasheet] · [CH340C datasheet]

The data traces from U3 through U7 to U4 are 0.20 mm wide on L1 over L2.
The parallel sections are about 0.26–0.28 mm apart edge to edge, with short
fanouts at the pads. [TI USB layout guidance] · [Fabrication requirements](../manufacturing/process.md#bare-board-fabrication)

[USB Type-C Rev 2.4, Table 3-5]:
  https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/USB-Type_2D00_C-Spec-R2.4-_2D00_-October-2024.pdf
[USBLC6-2 datasheet]: https://www.st.com/resource/en/datasheet/usblc6-2.pdf
[CH340C datasheet]:
  https://datasheet.lcsc.com/datasheet/pdf/e2f14e51aaa60c793f1f0cbc8a5d5faa.pdf?productCode=C84681
[TI USB layout guidance]: https://www.ti.com/lit/an/slla414a/slla414a.pdf
