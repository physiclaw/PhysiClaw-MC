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

L2 provides a continuous ground reference, and L3 carries power and ground
pours. Preserve return paths when routing signals between layers. Check USB
impedance and via geometry against the approved PCB stackup.
[Fabrication requirements](../manufacturing/process.md#bare-board-fabrication)

Use `build/PCW-MC-01-bare-board.step` to locate the outline and four M3
mounting holes. Allow space above the board for motor plugs, on the left
for solenoid wiring, and on the right for DC and USB-C plugs. Leave room for
the antenna cable and probe access on both sides. Verify fit with the actual
components and cables.
