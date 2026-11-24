# PCW-MC-01 design notes

## Power and control

- A single 12 V adapter supplies both motors, the solenoid, and the logic.
  The 2.5 A steady-state input target covers all three loads. A TPS54302 buck
  regulator supplies 3.3 V to the logic.
- The ESP32-WROOM-32UE-N4 uses an external antenna. A CH340C bridges the
  ESP32's UART to USB-C for programming and serial communication. Each
  TMC2209 uses direct STEP and DIR signals, a dedicated current-sense
  circuit, and a separate address on the shared UART.
- Q6 (AO4407A) switches the positive coil lead. Q7 (MMBT3904) drives its gate.
  A flyback diode carries coil current when the switch opens. The hardware interlock
  inhibits the drivers and solenoid during reset and until the operator
  arms the board through FluidNC.

The KiCad project contains the editable schematic. `make build` exports it
to `build/schematic.pdf`. [KiCad project](../pcb/kicad/PCW-MC-01.kicad_pro) ·
[Build instructions](../README.md#generate-the-manufacturing-files)

## IC implementation

| IC | Circuit and layout |
| --- | --- |
| U1 TPS54302DDCR | The 100 kΩ / 22.1 kΩ divider sets 3.293 V typical. EN floats for always-on operation. L1 is 6.8 µH, C2 is 47 µF / 25 V, C3 is 100 nF from BOOT to SW, C4/C5 are 47 µF each, and C35 is 47 pF across R43. The DDC0006A land pattern follows TI’s package drawing. [TI datasheet, §§4, 6.3, 7.2 and 10](https://www.ti.com/lit/ds/symlink/tps54302.pdf) |
| U2 ESP32-WROOM-32UE-N4 | C6/C7 are 22 µF and 100 nF. EN uses 10 kΩ and 1 µF. GPIO0 has a pull-up and download transistors. GPIO2/GPIO12 use the module straps. GPIO34 is unconnected. [Espressif datasheet](https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.html) |
| U3 USBLC6-2SC6 | Pins 1/6 carry D+, 3/4 carry D−, 5 connects to VBUS and C12, and 2 returns to ground beside J2. [ST datasheet](https://www.st.com/resource/en/datasheet/usblc6-2.pdf) |
| U4 CH340C | V3 and VCC share 3.3 V with 100 nF at each pin. R232 is low. The internal oscillator drives the UART, with TXD/RXD crossed to the ESP32. [WCH datasheet](https://www.wch-ic.com/downloads/CH340DS1_PDF.html) |
| U5/U6 TMC2209-LA-T | Each driver has 100 nF at each VS pin, 220 µF bulk, 22 nF across CPI–CPO, 100 nF across VCP–VS and two 0.100 Ω shunts with separate ground returns. CLK is grounded. MS1/MS2 select addresses 0 and 1. VREF is open for digital current scaling. [ADI datasheet §§2, 3, 21][TMC2209 datasheet] · [FluidNC driver initialization](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TMC2209Driver.cpp) |
| U7 TS3USB221ARSER | S selects port 2. OE stays high until VBUS turns on Q5. C29 bypasses VCC. [TI datasheet][TS3USB221A datasheet] |
| Q6 AO4407A and Q7 MMBT3904 | Q6 source pins 1–3 connect to V12 and drain pins 5–8 feed J5 pin 1. Q7 sinks the gate through R45. R33 returns the gate to V12 when Q7 is off. D4 returns flyback current from ground to the switched output. [AOS datasheet](https://www.aosmd.com/sites/default/files/res/datasheets/AO4407A.pdf) · [CJ datasheet](https://www.jscj-elec.com/gallery/file/MMBT3904%20SOT-23V2.pdf) |
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
| 12 V input | J1 is rated 5 A at the 2.5 A design load. Q1 has its drains on the fused input and sources on V12. F1 is 5 A. A 3 A current-limited adapter can sustain a fault below F1's opening current, so fault recovery depends on the adapter's overload behavior. [J1 drawing](https://jp.sameskydevices.com/product/resource/pj-102bh.pdf) · [Q1 datasheet](https://www.aosmd.com/sites/default/files/res/datasheets/AO4407A.pdf) · [F1 opening times](https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d) |
| 3.3 V buck | At 12 V in and 0.60 A out, 6.8 µH at 400 kHz gives 0.88 A peak-to-peak ripple and 1.04 A nominal peak in L1. With −20% inductance, the 290 kHz minimum center frequency and −6% dither, the continuous-conduction estimate is 1.41 A peak and 0.76 A RMS. U1 can skip pulses at light load. Cjiang lists 7.8 A typical saturation current for L1, above U1’s 6 A maximum high-side current-limit threshold. Its typical 20 °C-rise current is 4.8 A. The 0.1% divider and TI’s FB limits give 3.205–3.381 V static at 12 V. C2 provides about 15 µF typical at 12 V bias, or about 12 µF with −20% initial tolerance applied to that curve. TI recommends over 10 µF local ceramic input capacitance. C1 adds 220 µF of bulk storage. At 3.3 V, C4/C5 contribute about 44 µF typical near U1 and C6 adds about 15 µF. With 59 µF, TI’s Equation 14 estimates 26 kHz crossover before feed-forward. Check transient response and hot fault recovery on the first article. [TI datasheet, §§5.5, 7.2 and 7.4](https://www.ti.com/lit/ds/symlink/tps54302.pdf) · [Cjiang FEXL0550A land pattern and ratings](https://datasheet.lcsc.com/datasheet/pdf/f40adaf039c1475297db7da23c31da4d.pdf) · [Taiyo Yuden C2 bias curve, p. 2](https://static6.arrow.com/aropdfconversion/390ef171f49858851c7ebe9f223658ce3b0cd44a/msast32mab5476mpndt1ss.pdf) · [Murata C4/C5 bias data](https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR61A476ME15%22%5D) |
| Motor current and layout | U5/U6 have the specified 5 mm QFN, 0.50 mm pitch, nominal 3.7 mm grounded pad and 22 nF / 50 V pump capacitors. ADI recommends short, equal sense paths. Both X pin-to-shunt traces are 3.00 mm long and have the same length at each width. The Y traces measure 2.37 and 2.41 mm. For 35 µm copper at 20 °C, the estimated trace resistance is 3.59 mΩ on both X phases and 3.56/3.61 mΩ on Y, excluding pads and ground returns. At 0.400 A RMS with 0.100 Ω shunts and the 180 mV sense range, the nominal equation gives an IRUN register value near 11. This fits the StealthChop range of 8–31 and is below ADI's preferred 16–31 for best microstep precision. Verify the programmed range and measure phase current and low-speed motion with the intended motors. [ADI datasheet, §§6, 9, 21–22][TMC2209 datasheet] |
| Solenoid | U9 drives Q7 through 2.2 kΩ R21. R22 pulls the base to ground during reset or disarm. At 12 V, a saturated Q7 and the 2.2 kΩ / 1 kΩ gate divider give about −8.1 V gate-to-source. AOS specifies 17 mΩ maximum at −6 V and 25 °C, giving about 11 mW of conduction loss at 0.8 A. At 200 Hz, a 1% command is 50 µs. Verify the actual gate swing, duty range, coil release and temperature on the first article. The 5 A input fuse and adapter are shared by the board. The solenoid branch has no dedicated current limit or fault feedback. |

### JLC China availability

On 24 November 2026 all 43 SMT ordering codes and all four hand-soldered codes
in the generated BOM had domestic stock for a two-board build. Q6 uses the
same C16072 AO4407A as Q1 (6,365 pieces). Q7 uses C20526 MMBT3904 with
over four million pieces. R21, R22, R33 and R45 use existing resistor
ordering codes. The lowest reported SMT balance was L1 (1,379 pieces).
The PJ-102BH through-hole jack had 68 pieces.
[JLC China BOM matcher](https://www.jlc-smt.com/bom) · [AO4407A](https://www.jlc-smt.com/lcsc/detail/C16072.html) · [MMBT3904](https://www.jlc-smt.com/lcsc/detail/C20526.html)

| Reference | Stocked ordering code | Compatibility with the board |
| --- | --- | --- |
| L1 | FEXL0550A-6R8M, C5378515 | 6.8 µH ±20%, 28.6 mΩ maximum DCR. The recommended lands are 4.7 × 1.25 mm with a 2.0 mm gap, identical to the PCB footprint. The catalog pad 1 to pad 2 axis is 0°, giving 90° in the CPL. [Cjiang datasheet](https://datasheet.lcsc.com/datasheet/pdf/f40adaf039c1475297db7da23c31da4d.pdf) |
| C4, C5 | GRM21BR61A476ME15L, C124129 | The L and K suffixes identify reel size. Both contain the same 0805, 47 µF, 10 V X5R capacitor with the same DC-bias curve. [Murata datasheet](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM21BR61A476ME15-01A.pdf) |
| R44 | RT0603BRD0722K1L, C723484 | 22.1 kΩ ±0.1%, 100 mW, ±25 ppm/°C, 0603. The divider ratio and initial tolerance are unchanged. [Yageo datasheet](https://yageogroup.com/component-documentation/download/specsheet/RT0603BRD0722K1L) |

J1 (C3095964), J3/J4 (C144395), J5 (C5188434) and C1/C15/C22 (C5111097)
are purchased for manual installation. Upload only the SMT BOM for placement.

### International IC availability

JLCPCB’s public international parts catalog reported the quantities below on
23 November 2026 for U2–U11. They describe that catalog before assembly losses. JLC
China order allocation and replenishment dates require a lot-specific quote.

| Ref | Manufacturer part number | JLCPCB reported pieces |
| --- | --- | ---: |
| U1 | TPS54302DDCR | [C311983 listing](https://jlcpcb.com/partdetail/TexasInstruments-TPS54302DDCR/C311983) |
| U2 | ESP32-WROOM-32UE-N4 | [9,712](https://jlcpcb.com/partdetail/C701344) |
| U3 | USBLC6-2SC6 | [38,798](https://jlcpcb.com/partdetail/C7519) |
| U4 | CH340C, SOP-16 | [16](https://jlcpcb.com/partdetail/C7464026) |
| U5/U6 | TMC2209-LA-T, two per board | [21,405](https://jlcpcb.com/partdetail/C2150710) |
| U7 | TS3USB221ARSER | [95,696](https://jlcpcb.com/partdetail/C128396) |
| U9 | SN74LVC2G125DCTR | [1,929](https://jlcpcb.com/partdetail/C206035) |
| U10 | SN74LVC1G132DBVR | [25,652](https://jlcpcb.com/partdetail/C403723) |
| U11 | TLV803EA30DBZR | [6,912](https://jlcpcb.com/partdetail/C5218924) |

For U4, JLC's second listing for the same WCH CH340C in SOP-16
reported 71,042 pieces under C84681. Confirm pin 1 and catalog rotation in
the placement preview if adopting that code. [JLC alternate U4 listing](https://jlcpcb.com/partdetail/WCH_Jiangsu_Qin_Heng-CH340C/C84681)

## Layout and enclosure

In `build/view/`, read `top-routing.svg` (L1) and `bottom-routing.svg` (L4) in
the same orientation, looking through the board from the component side.
J1 and J2 are on the right, J3 and J4 are along the lower edge, and J5 is
on the left. Use `component-reference.svg` to locate components by designator.

- **Power input and buck.** The input runs from J1 through F1 and Q1 on L1.
  F1 provides overcurrent protection, Q1 blocks reverse polarity, and
  D1 clamps Q1's gate-to-source voltage. Its cathode shares the L1 feed
  from Q1 pin 2. Its anode connects straight across to the gate at pin 4,
  where the trace turns down to R1. D2 clamps transients on V12.
  Its cathode reaches C1 through the
  L3 12 V plane, and two vias tie its anode to L2 ground. At U1, C2's
  positive pad feeds VIN directly. C2 ground and U1 ground each have two
  vias to L2. From U1 pin 2, a straight 2.18 mm trace, 0.55 mm wide, reaches
  L1. C3 branches from the switch-side land. On the other side of L1,
  a wide 3.3 V trace feeds C4 and C5. Two vias at
  C5 feed the 3.3 V plane. A separate sense trace runs from C5 to R43 and
  C35. Below U1, a straight trace joins the feedback ends of R44, R43 and
  C35. R44 returns to U1 pin 1 on the top layer. A copper-pour keepout
  isolates this return up to pin 1. R2 shares the reset supervisor’s plane feed. TP3 has its own via.
- **Planes and returns.** L2 is a continuous ground plane. On L3, the
  12 V zone fills the area outside the 3.3 V and ground zones. Each
  supply forms one continuous region. Three ground regions connect to L2.
  U2 and U5 share the western region. The eastern control region reaches
  U6. A separate rounded ground pour
  beneath J2 and U3 leaves a passage for 3.3 V between USB and the controls.
  The western ground boundary follows X STEP and DIR toward U5, then
  widens beneath the motor UART crossing. Along the north edge, a
  37 mm stretch of 3.3 V copper links the ESP32 side to the USB side.
  It is at least 3.34 mm wide throughout and 4.04 mm wide at its
  narrowest point above the indicator routes. In the east, a rounded 3.3 V
  branch enters U6 between the Y control and winding routes. Ground
  wraps around its tip to reach the U6 thermal pad. The 12 V plane
  reaches C21 along the south side of the branch.
  L3 ground covers the full width of all 42 L4 digital and motor winding segments
  outside their via and connector-pad clearances. Each via or winding
  connector pin on these routes is within 1.89 mm of a plated
  connection from the same L3 ground region to L2, measured centre to centre.
- **USB and reset.** Follow the USB data pair from J2 through U3 and U7 to
  the CH340C (U4). On L1, two 0.30 mm VBUS branches leave U3 pin 5
  at matching 45° angles, run 2.15 mm north and south, then turn toward
  J2. The upper branch passes through C12 and between the pads of R13.
  The lower branch passes between the pads of R12. CC1 runs from
  J2 to R12 in 3.34 mm with one bend. CC2 reaches R13 in 2.15 mm.
  The ESP32 receive line runs diagonally beside TX into U4 pin 2 on L1.
  Both reset controls stay on L1. From U4 pins 13 and 14, follow DTR
  and RTS north to R5 and Q3. To find their southern branches, look at
  the opposite row of U4 pins. RTS passes between pins 3 and 4 to R6.
  DTR passes between pins 4 and 5 to R8, then runs west between the pads
  of C11 and R6 to Q4. The 3.3 V via between U4 pin 4 and C11 feeds both
  on one straight trace.
  From Q3, follow ESP_EN across the upper end of U2 to its EN pin. On
  the left, the reset supervisor U11 connects through R40 to the same
  trace as SW1 and TP9. The rear recovery pads TP1 (IO0) and TP2 (GND)
  are 2.50 mm apart.
- **Indicators.** From U2 pins 30 (IDLE) and 31 (ALARM), two parallel
  9.50 mm diagonals on L4 end beside R27. Both layer changes share the
  ground return at R27's ground pad. On L1, IDLE heads north to R26 and
  R24 on the upper row. ALARM reaches R27's signal pad and continues
  east to R25. The rows end at D7 (IDLE) and D8 (ALARM).
- **Interlock.** On L1, follow ACTUATOR_ARM from U2 pin 12 through the
  R35 pull-down junction to U10 pin 1. ESP_EN runs beside it into pin 2.
  From U10 pin 4, follow the diagonal through TP12 to both U9 enable pins.
  The driver-disable command from U2 pin 16 passes through the signal pad
  of R37 on its way to U9 pin 2. R37 takes 3.3 V from C32.
- **Solenoid.** On L1, SOL_CMD leaves U2 pin 8, passes between the pads
  of R21, then meets R38 and R23 on its way to U9 pin 5. The buffered
  output, SOL_SAFE, runs straight from U9 pin 3 to R21 and continues as
  SOL_ENABLE to the base of Q7. R45 and R33 control the Q6 gate beside
  the source pads. The four drain pads join a wide top-layer bus to D4
  and J5 pin 1. A separate via beside the Q6 source bank connects directly
  to the continuous L3 12 V plane. C28 and C34 share a second local feed.
- **Motor control.** The motor UART receive line leaves U2 pin 27 on a
  45° diagonal and turns once into R11. The shared bus runs from R10 and R11 between D2's
  pads on L1, then turns diagonally toward U6. Its final straight run
  passes between the pads of C23 and ends at U6 pin 14.
  For U5, follow the L1 diagonal from R10 to its via. The branch then
  runs left across the interlock on L4 and continues on the same line
  on L1 into U5 pin 14.
  On L1, follow DRIVERS_DISABLE down from U9 pin 6 to the horizontal
  trace below the drivers. Left leads to U5 pin 2. Right passes the R9
  pull-up and TP5 on the way to U6 pin 2.
- **X motor.** STEP and DIR leave U2 pins 10 and 11 toward the left and
  drop to L4. Follow the two diagonals toward U5. On L1, STEP runs
  straight through the R31 pull-down pad to pin 16. DIR goes straight
  from its via to pin 19. U5 and U6 both use a 90° footprint rotation.
  X_A2 leaves pin 21 to the left and changes to L4 beside the driver.
  X_B2 runs directly to J3 pin 4 on L1 over L2 ground.
  X_B1 runs between shunts R17 and R18
  before joining X_A1 and X_A2 on L4. The three parallel diagonals terminate
  at J3 pins 1 (A1), 2 (A2) and 3 (B1). R17 and R18 face each other.
  Follow the matching sense traces from U5 pins 23 and 27 to their inner
  pads. Each outer pad has two ground vias.
- **Y motor.** Y STEP runs south from its ESP32 via on L4 and makes one
  45° turn toward U6. The diagonal continues across its via onto L1,
  passes through R32's pull-down pad and enters U6 pin 16. The L3
  3.3 V branch feeds the 1.72 mm L1 trace between C23 and VCC_IO
  (pin 15), then continues to the via beside MS2 (pin 9).
  C23 has a local ground via. All four Y motor
  outputs approach J4 in pin order on L4 over L3 ground. Y_A1 runs beside
  Y_A2, then turns once into J4 pin 1. Y_B1 passes
  between the two shunts on L1 before changing layers. Y_B2 leaves
  U6 pin 1, passes below C20 and turns onto an L4 diagonal at its via.
  It then runs straight to pin 4. Each shunt has two ground vias, and
  the disable trace reaches U6 on L1.

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
| Q6 output to J5 | 0.85 mm drain bus, 1.00 mm to D4 and 1.20 mm to J5 | 0.80 A solenoid |
| U5/U6 winding outputs | 0.25–0.35 mm at the driver, 0.55–0.60 mm on longer runs | 0.40 A RMS per phase |
| U5/U6 current-sense pins to shunts | 0.30 and 0.50 mm on X, 0.25 and 0.45 mm on Y | Same phase current |
| Buck and ESP32 | 0.55 mm switch trace, 1.00 mm from the inductor to C5, 0.635 mm at U2 | 0.60 A on 3.3 V, including 0.50 A at U2 |

C16 bypasses U5's 3.3 V digital I/O supply. The L3 supply via sits on
the 1.62 mm trace between C16 and U5 pin 15, 0.83 mm from the capacitor.
C16's ground pad connects directly to a ground via on its other side.
Both traces are 0.30 mm wide. U5 takes motor power through its two 12 V
supply pins.
[TMC2209 datasheet, §§3 and 20.2][TMC2209 datasheet]

For 35 µm outer copper, the IPC-2152 curve fit gives about 9 °C rise for
a uniform 1.50 mm trace at 2.50 A.
Each short 1.00 mm fuse connection dissipates about 1.8 mW at 2.50 A
using the hot-copper resistance. The fuse body also heats its pads.
[KiCad track-current equations](https://docs.kicad.org/doxygen/tracks__width__versus__current__formula_8h.html)

The DC model assumes 35 µm outer copper, 15.2 µm inner copper, 18 µm
via-wall plating and copper resistivity at 70 °C.

- **12 V rail, 2.50 A total.** The model assigns 0.75 A to each motor
  driver, 0.80 A to the solenoid and 0.20 A to the buck input. On the
  revised board, measure the voltage drop between Q1 and Q6 under combined load.
- **3.3 V rail, 0.60 A total.** From the inductor output, the copper drop
  is about 3.7 mV at the ESP32 and 3.3 mV at the CH340.
- **Q1 vias, 2.00 A total.** With the 12 V loads scaled proportionally,
  the vias beside Q1 pins 1, 2 and 3 carry about 0.69, 0.59 and 0.72 A,
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
return to L1 through off-pad vias beside U3. Six plated ground vias tie
their dedicated L3 reference to the continuous L2 ground plane.
The J2 D− via is 0.79 mm from its nearest ground stitch, centre
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
