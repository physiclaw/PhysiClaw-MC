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

## IC implementation

| IC | Circuit and layout |
| --- | --- |
| U1 AP63203WU-7 | Fixed 3.3 V feedback, EN follows VIN. L1 3.9 µH, C2 10 µF, C4/C5 22 µF each, C3 100 nF from BST to SW. SW stays on L1 copper. [Diodes datasheet, Table 2](https://www.diodes.com/datasheet/download/AP63200-AP63201-AP63203-AP63205.pdf) |
| U2 ESP32-WROOM-32UE-N4 | C6/C7 are 22 µF and 100 nF. EN uses 10 kΩ and 1 µF. GPIO0 has a pull-up and download transistors. GPIO2/GPIO12 use the module straps. GPIO34 takes an externally pulled-up fault signal. [Espressif datasheet](https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.html) |
| U3 USBLC6-2SC6 | Pins 1/6 carry D+, 3/4 carry D−, 5 connects to VBUS and C12, and 2 returns to ground beside J2. [ST datasheet](https://www.st.com/resource/en/datasheet/usblc6-2.pdf) |
| U4 CH340C | V3 and VCC share 3.3 V with 100 nF at each pin. R232 is low. The internal oscillator drives the UART, with TXD/RXD crossed to the ESP32. [WCH datasheet](https://www.wch-ic.com/downloads/CH340DS1_PDF.html) |
| U5/U6 TMC2209-LA-T | Each driver has 100 nF at each VS pin, 220 µF bulk, 22 nF across CPI–CPO, 100 nF across VCP–VS and two 0.100 Ω shunts with separate ground returns. CLK is grounded. MS1/MS2 select addresses 0 and 1. VREF is open for digital current scaling. [ADI datasheet §§2, 3, 21][TMC2209 datasheet] · [FluidNC driver initialization](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TMC2209Driver.cpp) |
| U7 TS3USB221ARSER | S selects port 2. OE stays high until VBUS turns on Q5. C29 bypasses VCC. [TI datasheet][TS3USB221A datasheet] |
| U8 TPS1H200AQDGNRQ1 | DIAG_EN connects to V12, within its 0–40 V range. FAULT pulls up to 3.3 V. R33 sets a nominal 1.21 A limit (0.8 V × 2500 / 1650 Ω). C30 selects delayed latch-off. D4's cathode connects to the switched output. The exposed pad is grounded. [TI datasheet §§5–7](https://www.ti.com/lit/ds/symlink/tps1h200a-q1.pdf) |
| U9 SN74LVC2G125DCTR | ACT_OE_N controls both active-low enables. With U9 disabled, R9 pulls the driver disables high and R22 pulls the solenoid input low. C31 is 100 nF. [TI datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc2g125.pdf) |
| U10 SN74LVC1G132DBVR | The Schmitt NAND enables U9 when ESP_EN and ACTUATOR_ARM are both high. R35 pulls ARM low at startup. C32 is 100 nF. [TI datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc1g132.pdf) |
| U11 TLV803EA30DBZR | Active-low open-drain reset, 3.08 V nominal falling threshold and 200 ms nominal release delay. R40 couples reset to ESP_EN, R3 pulls up and C33 bypasses VDD. [TI datasheet](https://www.ti.com/lit/ds/symlink/tlv803e.pdf) |

ADI calls for 2.2–4.7 µF and a short ground return at each 5VOUT. C17 and C24
return directly to their drivers, with clearance to the L1 GND pour.
At 25 °C and 5 V bias, Samsung's typical curves give 0.96 µF for the former
2.2 µF 0603 and 3.36 µF for the fitted 4.7 µF, 25 V X7R 0805 (C98195).
The fitted part gives about 3.26 µF at 5.25 V.
[Original capacitor](https://product.samsungsem.com/mlcc/CL10A225KO8NNN.do) ·
[Fitted capacitor](https://product.samsungsem.com/mlcc/CL21B475KAFNNN.do)

## Layout and enclosure

- L2 is continuous GND. Each of the 13 L3 ground regions has at least two
  plated ties to L2, with five stitching vias near USB. L3 ground also
  connects the thermal holes at U2, U5, U6 and U8.
- L4 USB, VBUS, STEP/DIR, motor UART and interlock traces reference L3 GND
  outside via clearances. Y_STEP references L2 from L1. SOL_CMD joins the
  indicator branch below the 3.3 V feed and uses the U9 ground stitch at
  (122.5, 79.2) mm. The largest centre-to-centre distances to a ground
  tie in the same L3 region are 1.65 mm for motor UART, 1.57 mm for ESP_EN
  and 1.90 mm for SOL_CMD.
- Five L3 pours distribute 3.3 V. Parallel vias connect the regulator and
  central feed. L4 links feed the west rail and R8 pour. All five pours
  remain connected in the copper model with any one 3.3 V via barrel open.
- The Y_A2 escape runs over V12 and clears the 3.3 V pour across its full
  width. Winding current returns through the paired motor phase and
  H-bridge. Local VS capacitors and shunt returns close the switching loops.

[TI PCB return-path guidance](https://www.ti.com/lit/an/slla414a/slla414a.pdf) ·
[ADI TMC2209 layout guidance][TMC2209 datasheet]

Use `build/PCW-MC-01-bare-board.step` to locate the outline and four M3
mounting holes. Allow space above the board for motor plugs, on the left
for solenoid wiring, and on the right for DC and USB-C plugs. Leave room for
the antenna cable and probe access on both sides. Verify fit with the actual
components and cables.

## USB-C

J2 ties A6 to B6 (D+) and A7 to B7 (D−). Both 0.20 mm wide ties run on L1
over L2 and measure 3.132 mm between contact centres. The USB Type-C
recommendation is at most 3.5 mm. CC1 and CC2 each have a 5.1 kΩ
pull-down. [USB Type-C Rev 2.4, Table 3-5, note 2]

Both lanes drop to L4 on opposite sides of the J2 contact row, then
return to L1 through off-pad vias beside U3. L3 GND reaches the U3 ground
stitch. The J2 D− via is 0.79 mm from its nearest ground stitch, centre
to centre. From J2 to U4 through U3 and U7, the D+/D− trace-length
mismatch is 1.27 mm in both plug orientations, excluding package
internals and via barrels.
[TI USB layout guidance] · [Fabrication requirements](../manufacturing/process.md#bare-board-fabrication)

R41 and R42 (49.9 Ω, 1%, 0402) separately shunt U7's 1D+ and 1D− pins
to ground, following TI's recommendation for unused pins. Their top-layer
routes measure 1.17 mm and 1.16 mm, respectively, and the resistors share
a ground via. [TI TS3USB221A datasheet, §8.2.2][TS3USB221A datasheet]

The 90 Ω differential sections use 0.28 mm traces and a 0.18 mm gap.
A 2D cross-section model estimated 89–91 Ω on uniform L1, 89 Ω on uniform
L4, 96 Ω near the L4 via launch and 92 Ω at the 0.26 mm D− entry to U7.4.
The 0.38 mm ends of the L4 fanouts modelled at 45 Ω single-ended.
Inputs were JLC04161H-7628 (outer dielectric 0.2104 mm, Dk 4.4),
40.64 µm finished copper and solder mask (Dk 3.8).
[JLC stackup] · [TI layout guidance, §8.4][TS3USB221A datasheet]

[USB Type-C Rev 2.4, Table 3-5, note 2]:
  https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/USB-Type_2D00_C-Spec-R2.4-_2D00_-October-2024.pdf
[JLC stackup]: https://jlcpcb.com/impedance
[TMC2209 datasheet]: https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf
[TS3USB221A datasheet]: https://www.ti.com/lit/ds/symlink/ts3usb221a.pdf
[TI USB layout guidance]: https://www.ti.com/lit/an/slla414a/slla414a.pdf
