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

The KiCad project contains the editable schematic. `make build` exports it
to `build/schematic.pdf`. [KiCad project](../pcb/kicad/PCW-MC-01.kicad_pro) ·
[Build instructions](../README.md#generate-the-manufacturing-files)

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

- The input runs from J1 through F1 and Q1 on L1. F1 provides overcurrent
  protection, Q1 blocks reverse polarity, and D1 clamps Q1's gate-to-source
  voltage. D2 clamps transients on V12. Its cathode reaches C1 through the
  L3 12 V plane, and two vias tie its anode to L2 ground.
- L2 is a continuous ground plane. L3 has continuous 3.3 V and 12 V planes
  and three ground regions tied to L2. The west ground region ties U2 to
  U5, the east region reaches from J2 to U6, and the third serves U8.
- L4 signals run over L3 ground outside via clearances. Each signal
  transition to L4 has a ground tie to L2 within 2 mm in the same L3
  region. DTR and RTS cross the U2 area on L1, leaving the L3 3.3 V
  plane continuous. The motor UART crosses under Y_STEP near D2.
- U5 and U6 both use a 90° footprint rotation. At U5, X_B2 runs directly
  to J3 pin 4 on L1 over L2 ground. X_B1 runs between shunts R17 and R18
  before joining X_A1 and X_A2 on L4. Each L4 winding runs over L3 ground
  with a plated return to L2 within 2 mm of its via and connector pin.
  Both shunts have two ground vias.
- C23 connects directly to U6's VCC_IO pin through a 1.45 mm trace and
  has a local ground via. R32 lands directly on Y_STEP. All four Y motor
  outputs approach J4 in pin order on L4 over L3 ground. Y_B1 passes
  between the two shunts on L1 before changing layers. Each shunt has
  two ground vias, and the disable trace reaches U6 on L1.
- Rear boot recovery pads TP1 (IO0) and TP2 (GND) are labelled and spaced
  2.50 mm apart.

[TI PCB return-path guidance](https://www.ti.com/lit/an/slla414a/slla414a.pdf) ·
[ADI TMC2209 layout guidance][TMC2209 datasheet]

Use `build/PCW-MC-01-bare-board.step` to locate the outline and four M3
mounting holes. Allow space above the board for motor plugs, on the left
for solenoid wiring, and on the right for DC and USB-C plugs. Leave room for
the antenna cable and probe access on both sides. Verify fit with the actual
components and cables.

## Power trace widths

| Copper path | Routed width | Current used for review |
| --- | --- | --- |
| J1 through F1 to Q1 | 1.50 mm, with a 0.50 mm long, 1.00 mm wide connection at each F1 pad | 2.50 A steady input |
| Q1 to L3 12 V | Three 0.80 mm feeds and three 0.30 mm drilled vias | 2.50 A shared |
| U8 output to J5 | 0.40 mm for the first 1.10 mm, then 0.80 and 1.20 mm | 0.80 A solenoid |
| U5/U6 winding outputs | 0.25–0.35 mm at the driver, 0.55–0.60 mm on longer runs | 0.40 A RMS per phase |
| U5/U6 current-sense pins to shunts | 0.25–0.45 mm | Same phase current |
| Buck and ESP32 | 0.60 mm switch trace, 1.00 mm from the inductor to C5, 0.635 mm at U2 | 0.60 A on 3.3 V, including 0.50 A at U2 |

C16 bypasses U5's 3.3 V digital I/O supply. Its feed from the supply via
through C16 to U5 pin 15 is 0.30 mm throughout. Its ground connection is
also 0.30 mm. U5 takes motor power through its two 12 V supply pins.
[TMC2209 datasheet, §§3 and 20.2][TMC2209 datasheet]

For 35 µm outer copper, the IPC-2152 curve fit gives about 9 °C rise for
a uniform 1.50 mm trace at 2.50 A and 4 °C for a 0.40 mm trace at 0.80 A.
Each short 1.00 mm fuse connection dissipates about 1.8 mW at 2.50 A
using the hot-copper resistance. The fuse body also heats its pads.
[KiCad track-current equations](https://docs.kicad.org/doxygen/tracks__width__versus__current__formula_8h.html)

A DC copper model used 35 µm outer copper, 15.2 µm inner copper, assumed
18 µm barrel plating and copper resistivity at 70 °C. A 2.50 A load case
allocated 0.75 A to each driver's 12 V supply, 0.80 A to U8 and 0.20 A to
the buck input. The estimated drop from Q1's source pads to U8's supply
pin was about 47 mV. With a 0.60 A load on 3.3 V, the estimated drop from
the inductor output to the ESP32 was about 5 mV. These estimates cover PCB
copper. Connector, fuse and semiconductor losses and temperature rise need
first-article measurements at the intended load and enclosure temperature.
[First-article acceptance](../manufacturing/process.md#first-article-acceptance)

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
