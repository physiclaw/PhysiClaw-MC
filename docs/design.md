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

### Component review, 23 November 2026

For v1.0 at `c7292ef`, all 101 fitted references (45 distinct MPNs) agreed
across the schematic, PCB, assembly BOM and supplier table on MPN, order
code and assigned footprint. KiCad 10.0.8 ERC and DRC with zone refill and
schematic parity reported zero violations, unconnected items or parity
issues. All 21 repository tests passed. The IC pin assignments in the
exported netlist agree with the manufacturer pinouts cited above.

| Circuit | Fit and operating margin |
| --- | --- |
| 12 V input and buck | J1 is rated 5 A at the 2.5 A design load. Q1 has its drains on the fused input and sources on V12. At 12 V in, 3.3 V out and 0.60 A load, U1's nominal 1.1 MHz and 3.9 µH give about 0.56 A peak-to-peak ripple and 0.88 A peak in L1. L1 is rated 2.1 A thermal and 3 A saturation. F1 is 5 A. A 3 A current-limited adapter can sustain a fault below F1's opening current, so fault recovery depends on the adapter's overload behavior. [J1 drawing](https://jp.sameskydevices.com/product/resource/pj-102bh.pdf) · [Q1 datasheet](https://www.aosmd.com/sites/default/files/res/datasheets/AO4407A.pdf) · [U1 datasheet, §§9–10](https://www.diodes.com/datasheet/download/AP63200-AP63201-AP63203-AP63205.pdf) · [L1 ratings](https://jlcpcb.com/partdetail/Sunlord-SWPA4030S3R9MT/C96899) · [F1 opening times](https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d) |
| Motor current and layout | U5/U6 have the specified 5 mm QFN, 0.50 mm pitch, nominal 3.7 mm grounded pad and 22 nF / 50 V pump capacitors. ADI recommends short, equal sense paths. Pin-to-shunt lengths are 3.04/2.09 mm on X and 2.37/2.41 mm on Y. At 35 µm copper and 20 °C the different widths give about 4.07/4.12 mΩ and 3.56/3.61 mΩ respectively, excluding pads and ground returns. At 0.400 A RMS with 0.100 Ω shunts and the 180 mV sense range, the nominal equation gives an IRUN register value near 11. This fits the StealthChop range of 8–31 and is below ADI's preferred 16–31 for best microstep precision. Verify the programmed range and measure phase current and low-speed motion with the intended motors. [ADI datasheet, §§6, 9, 21–22][TMC2209 datasheet] |
| Solenoid | U9 drives U8 IN through 10 kΩ with 47 kΩ to ground. At a 3.3 V drive and TI's 150 kΩ minimum internal pulldown the input is about 2.58 V, above its 1.8 V high threshold. R33 gives a nominal 1.21 A limit, about 1.02–1.41 A including its 1% tolerance and TI's ±15% under the specified limit-test conditions. Compare the minimum to cold-coil current at the highest adapter voltage. At 200 Hz a 1% command lasts 50 µs. TI gives 20–90 µs turn-on delay at 13.5 V and 0.1 A, before the output rise. Determine usable duty range and release time on the actual coil. [TI datasheet, §§5.5–5.6](https://www.ti.com/lit/ds/symlink/tps1h200a-q1.pdf) |

### IC availability

JLCPCB's public international parts catalog reported the quantities below on
23 November 2026. They describe that catalog before assembly losses. JLC
China order allocation and replenishment dates require a lot-specific quote.

| Ref | Manufacturer part number | JLCPCB reported pieces |
| --- | --- | ---: |
| U1 | AP63203WU-7 | [7](https://jlcpcb.com/partdetail/C780769) |
| U2 | ESP32-WROOM-32UE-N4 | [9,712](https://jlcpcb.com/partdetail/C701344) |
| U3 | USBLC6-2SC6 | [38,798](https://jlcpcb.com/partdetail/C7519) |
| U4 | CH340C, SOP-16 | [16](https://jlcpcb.com/partdetail/C7464026) |
| U5/U6 | TMC2209-LA-T, two per board | [21,405](https://jlcpcb.com/partdetail/C2150710) |
| U7 | TS3USB221ARSER | [95,696](https://jlcpcb.com/partdetail/C128396) |
| U8 | TPS1H200AQDGNRQ1 | [0](https://jlcpcb.com/partdetail/C2653785) |
| U9 | SN74LVC2G125DCTR | [1,929](https://jlcpcb.com/partdetail/C206035) |
| U10 | SN74LVC1G132DBVR | [25,652](https://jlcpcb.com/partdetail/C403723) |
| U11 | TLV803EA30DBZR | [6,912](https://jlcpcb.com/partdetail/C5218924) |

For U8, TI lists the exact switch as active and AEC-Q100 qualified, and
DigiKey lists the DGN part in cut tape. Request JLC sourcing of that MPN
before scheduling assembly. For U1, Farnell lists the fixed 3.3 V order
code. For U4, JLC's second listing for the same WCH CH340C in SOP-16
reported 71,042 pieces under C84681. Confirm pin 1 and catalog rotation in
the placement preview if adopting that code. [TI U8 status](https://www.ti.com/product/TPS1H200A-Q1/part-details/TPS1H200AQDGNRQ1) · [DigiKey U8](https://www.digikey.com/en/products/detail/texas-instruments/TPS1H200AQDGNRQ1/9593381) · [Farnell U1](https://jp.farnell.com/en-JP/diodes-inc/ap63203wu-7/dc-dc-conv-sync-buck-1-1mhz-85deg/dp/3518307) · [JLC alternate U4 listing](https://jlcpcb.com/partdetail/WCH_Jiangsu_Qin_Heng-CH340C/C84681)

## Layout and enclosure

- The input runs from J1 through F1 and Q1 on L1. F1 provides overcurrent
  protection, Q1 blocks reverse polarity, and D1 clamps Q1's gate-to-source
  voltage. D2 clamps transients on V12. Its cathode reaches C1 through the
  L3 12 V plane, and two vias tie its anode to L2 ground.
- L2 is a continuous ground plane. On L3, the 12 V zone fills the area
  outside the 3.3 V and ground zones. Each supply forms one continuous
  region. Three ground regions connect to L2 and serve U2 and U5 in the
  west, J2 and U6 in the east, and U8 locally.
- L3 ground covers the full width of all 69 L4 signal and winding segments
  outside their via and connector-pad clearances. Each via or winding
  connector pin on these routes is within 1.93 mm of a plated
  connection from the same L3 ground region to L2, measured centre to centre.
- DTR and RTS cross the U2 area on L1. The motor UART runs from R10 and R11
  between D2's pads on L1, above Y_DIR and Y_STEP, then turns toward U6.
- U5 and U6 both use a 90° footprint rotation. At U5, X_B2 runs directly
  to J3 pin 4 on L1 over L2 ground. X_B1 runs between shunts R17 and R18
  before joining X_A1 and X_A2 on L4. Both shunts have two ground vias.
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

The DC model assumes 35 µm outer copper, 15.2 µm inner copper, 18 µm
via-wall plating and copper resistivity at 70 °C.

- **12 V rail, 2.50 A total.** The model assigns 0.75 A to each motor
  driver, 0.80 A to U8 and 0.20 A to the buck input. The largest copper
  drop is about 45 mV, from Q1's source pads to U8's supply pin.
- **3.3 V rail, 0.60 A total.** From the inductor output, the copper drop
  is about 4.6 mV at the ESP32 and 4.9 mV at the CH340.
- **Q1 vias, 2.00 A total.** With the 12 V loads scaled proportionally,
  the vias beside Q1 pins 1, 2 and 3 carry about 0.67, 0.59 and 0.74 A,
  respectively. The three via barrels dissipate about 2.1 mW in total.

Measure temperature rise above ambient on the assembled board at steady
load in the intended enclosure.
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
