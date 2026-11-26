# PCW-MC-01 design notes

## Power and control

- A single 12 V adapter supplies both motors, the solenoid, and the logic.
  The full-load design budget is 2.5 A from a regulated 12 V / 3 A adapter. A TPS54302 buck
  regulator supplies 3.3 V to the logic.
- The ESP32-WROOM-32UE-N4 uses an external antenna. A CP2102N bridges the
  ESP32's UART to USB-C for programming and serial communication. Each
  TMC2209 uses direct STEP and DIR signals, a dedicated current-sense
  circuit, and a separate address on the shared UART.
- Q6 (AO4407A) switches the positive coil lead. Q7 (MMBT3904) drives its gate.
  A flyback diode carries coil current when the switch opens. The hardware interlock
  inhibits the drivers and solenoid during hardware reset. When FluidNC
  starts in Idle, it disables motor drive and solenoid PWM before releasing
  the interlock for normal commands.

The KiCad project contains the editable schematic. `make build` exports it
to `build/schematic.pdf`. [KiCad project](../pcb/kicad/PCW-MC-01.kicad_pro) ·
[Build instructions](../README.md#generate-the-manufacturing-files)

## IC implementation

| IC | Circuit and layout |
| --- | --- |
| U1 TPS54302DDCR | The 102 kΩ / 22.1 kΩ divider sets 3.347 V typical. EN floats for always-on operation. L1 is 6.8 µH, C2 is 47 µF / 25 V, C3 is 100 nF from BOOT to SW, C4/C5 are 47 µF each, and C35 is 47 pF across R43. The DDC0006A land pattern follows TI’s package drawing. [TI datasheet, §§4, 6.3, 7.2 and 10](https://www.ti.com/lit/ds/symlink/tps54302.pdf) |
| U2 ESP32-WROOM-32UE-N4 | C6/C7 are 22 µF and 100 nF. EN uses 10 kΩ and 1 µF. GPIO0 has a pull-up and download transistors. GPIO2/GPIO12 use the module straps. GPIO34 is unconnected. [Espressif datasheet](https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.html) |
| U3 SP0503BAHTG | Pins 2, 3 and 4 clamp VBUS, D+ and D− respectively to ground at pin 1. [Littelfuse datasheet](https://www.littelfuse.com/assetdocs/tvs-diode-array-spasp050xba-lead-freegreen-datasheet?assetguid=15a03de1-f0c6-457a-95f1-55d449fdd756) |
| U4 CP2102N-A02-GQFN24R | VIO, VDD and VREGIN use the board’s regulated 3.3 V. R47 pulls RSTb up through 1 kΩ. Pins 3 and 4 connect directly to D+ and D−. [Silicon Labs, figures 2.3 and 2.6](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf) |
| U5/U6 TMC2209-LA-T | Each driver has 100 nF at each VS pin, 220 µF bulk, 22 nF across CPI–CPO, 100 nF across VCP–VS and two 0.100 Ω shunts with separate ground returns. CLK is grounded. MS1/MS2 select addresses 0 and 1. VREF is open for digital current scaling. [ADI datasheet §§2, 3, 21][TMC2209 datasheet] · [FluidNC driver initialization](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TMC2209Driver.cpp) |
| Q6 AO4407A and Q7 MMBT3904 | Q6 source pins 1–3 connect to V12 and drain pins 5–8 feed J5 pin 1. Q7 sinks the gate through R45. R33 returns the gate to V12 when Q7 is off. D4 returns flyback current from ground to the switched output. [UMW datasheet][UMW AO4407A] · [CJ datasheet](https://www.jscj-elec.com/gallery/file/MMBT3904%20SOT-23V2.pdf) |
| U9 SN74LVC2G125DCTR | ACT_OE_N controls both active-low enables. With U9 disabled, R9 pulls the driver disables high and R22 pulls the solenoid input low. C31 is 100 nF. [TI datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc2g125.pdf) |
| U10 SN74LVC1G132DBVR | The Schmitt NAND enables U9 when ESP_EN and ACTUATOR_ARM are both high. R35 pulls ARM low at startup. C32 is 100 nF. [TI datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc1g132.pdf) |
| U11 TLV803EA30DBZR | Active-low open-drain reset, 3.08 V nominal falling threshold and 200 ms nominal release delay. R40 couples reset to ESP_EN, R3 pulls up and C33 bypasses VDD. [TI datasheet](https://www.ti.com/lit/ds/symlink/tlv803e.pdf) |

Both STDBY pins (20) are grounded, and C16/C23 bypass the drivers’ 3.3 V
VCC_IO supplies. ADI calls for 2.2–4.7 µF and a short ground return at each 5VOUT. C17 and C24
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

### IC datasheet review, 25 November 2026

The CP2102N migration supersedes the USB circuit in commit `4bc99ea`. The remaining IC and firmware findings below come from the 25 November board review. First-article measurements are pending.

Datasheets used for the current circuit include TPS54302 rev. C, ESP32-WROOM-32UE v2.1, CP2102N rev. 1.5, Littelfuse SP050xBA, TMC2209 rev. 1.09, SN74LVC2G125 rev. Q, SN74LVC1G132 rev. E and TLV803E rev. J.

Firmware findings use the tagged source and the project's cited TMCStepper
v0.7.3. FluidNC's build accepts a range of library versions. A UART capture
on the shipped image can establish the actual register sequence.
[Manufacturer links](#ic-implementation) · [FluidNC dependency range](https://github.com/bdring/FluidNC/blob/v4.1.1/platformio.ini)

**USB host detection and power sequencing.** J2 VBUS reaches U4 pin 8 through R29 (22.1 kΩ) with R30 (47.5 kΩ) to ground. At 5.0 V the nominal sense voltage is 3.41 V. At 4.4 V and opposing 1% tolerances the lower bound is 2.98 V before leakage. The board’s 3.437 V high supply corner gives a 2.837 V input-high requirement. Silicon Labs explicitly permits the divider to limit input current while VIO is off. U3 has separate ground clamps for D+, D− and VBUS. The previous external data-line-to-VBUS feedback path has been removed. [Silicon Labs, §2.3 and tables 3.7, 3.10](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=9) · [Littelfuse diode topology](https://www.littelfuse.com/assetdocs/tvs-diode-array-spasp050xba-lead-freegreen-datasheet?assetguid=15a03de1-f0c6-457a-95f1-55d449fdd756)

**Bridge supply and UART.** VIO (5), VDD (6) and VREGIN (7) share 3.3 V. Figure 2.3 calls for 100 nF and 4.7 µF close to each power pin. The top-layer paths from pins 5, 6 and 7 to C10, C11 and C29 (100 nF) measure 1.57, 2.31 and 2.32 mm respectively. The three 4.7 µF capacitors share parallel 3.3 V and ground traces beside U4. Top-layer paths from pin 7 to C36, C37 and C38 measure 4.17, 5.72 and 7.27 mm respectively. Check VDD at C11 under load against the 3.0–3.6 V operating range. Pin 2 and the exposed pad return to ground. TXD (21) drives ESP_RX and RXD (20) receives ESP_TX through R28. DTR (23) and RTS (19) drive the auto-download circuit. [Silicon Labs, figure 2.3 and §5.2](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf)

**QFN24 land pattern.** The Gerbers match the land dimensions in table 7.2, the 0.060 mm mask expansion and the four 0.90 mm square center paste windows. Figure 7.2 shows rounded inner ends on the peripheral lands and a 0.25 mm chamfer on the exposed land at the pin 1 corner. The Gerbers use rectangular peripheral lands and a square exposed land. [Silicon Labs, figure and table 7.2](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=39)

**USB cold start and production configuration.** A02 erratum E110 documents undefined D+ and D− levels around power-on reset, typically for 15 ms. Some hosts may miss attachment. During the first-article 12 V power-cycle test with USB already connected, verify enumeration on the intended host and hub. Check that VDD takes at least 10 µs to rise past 2.2 V. The factory descriptor advertises bus power and 100 mA. Program the self-powered descriptor and read it back after cycling power. [Silicon Labs, tables 3.3 and 4.5](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf) · [A02 erratum E110](https://www.silabs.com/documents/public/errata/cp2102n-errata.pdf#page=3)

With 12 V retained, transfer the enumerated board from the host to the Appendix F fixture and measure VBUS, D+ and D− against the 0.4 V limit. Exercise host power removal and re-enumeration separately in both plug orientations. [USB-IF test procedure, Appendix F](https://www.usb.org/sites/default/files/USB-IFTestProc1_3.pdf)

If the host leaves VBUS open, C12 (100 nF) discharges through R29 and R30 in series (69.6 kΩ). With board capacitance alone the nominal time constant is 6.96 ms. Cable and host capacitance can extend it. R30 pulls U4 pin 8 to ground once VBUS discharges. If the host keeps VBUS powered through sleep, U4 supports host-initiated USB resume or bus reset. [Silicon Labs, figure 2.6 and §4.1](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf)

**Both TMC2209s use the single-node UART reply delay.** The board connects
both PDN_UART pins to one bus at addresses 0 and 1. ADI specifies
`NODECONF.SENDDELAY ≥ 2` on every node so that a reply to one driver does
not look like a transmission error to the other. The FluidNC v4.1.1 and
TMCStepper v0.7.3 initialization paths reviewed here leave the reset value
of 0. At 115200 baud that gives 8 bit times (69 µs) before a reply instead
of the recommended minimum setting's 24 bit times (208 µs). Initialize
both addresses before the first diagnostic read, then capture alternating
reads on the production image and check each node's write counter.
[ADI TMC2209 rev. 1.09, §§4.1.2 and 5.1](https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf#page=19) · [FluidNC initialization](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TMC2209Driver.cpp) · [TMCStepper initialization](https://github.com/teemuatlut/TMCStepper/blob/v0.7.3/src/source/TMC2208Stepper.cpp#L46-L53)

**Motor enable can follow a failed driver setup.** FluidNC records a failed
driver communication test and skips that driver's current and microstep setup.
If boot reaches Idle, the board's `after_reset` macro releases U9. A later
move drives the shared ENN low independently of either driver's error flag.
For a driver that received no setup writes and has standard factory OTP,
open VREF and the fitted 0.100 Ω shunts give about 1.40 A RMS at full run
scale versus 0.796 A configured. The straps also select 8 microsteps on X
and 32 on Y versus 16 commanded on both. The result can be incorrect CoreXY
travel as well as excess motor current. A local driver reset can also
restore defaults while the ESP32 remains powered. Qualify with the motors
disconnected and one UART branch open at boot. On a jog request, check
TP12 (inhibit) and TP5 (ENN). A release implementation should keep the
drivers disabled until both addresses accept configuration and should
repeat that check after a driver reset. The boot-time IFCNT test precedes
the current-setting writes. ADI provides IFCNT for verifying accepted writes
to write-only registers such as IHOLD_IRUN. [Board configuration](../firmware/config.yaml) · [FluidNC driver error handling](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TrinamicBase.cpp) · [Shared enable logic](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Machine/Axes.cpp) · [ADI §§2, 4, 8–9 and 17][TMC2209 datasheet]

**Two motor-driver acceptance criteria need tighter limits.** U5/U6 use
their internal 5 V regulators. ADI §20.1 specifies 5.5–29 V on VS in that
circuit. The first-article guide currently accepts motion down to 4.75 V.
Measure at pins 22 and 28 of each driver under combined load and require
at least 5.5 V during operation. For the enclosure soak, the operating
junction limit is 125 °C, while the nominal 120 °C prewarning can trip as
high as 140 °C. Clear OTPW and OT flags alone cannot establish junction
temperature margin. Record a thermally justified upper bound on junction
temperature at the specified 50 °C enclosure condition. [First-article guide](../manufacturing/process.md#first-article-acceptance) · [ADI §§20.1–20.3](https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf#page=75)

**The first move has no guaranteed StealthChop tuning interval.** ADI's
initial offset calibration needs an enabled, stationary motor at run current
for up to about 130 ms. The startup macro disables both drivers, and
`disable_delay_us` is zero. On the first move FluidNC enables the drivers
and starts the step timer. The 500 ms idle timeout applies after motion.
Capture ENN, STEP and phase current from cold start. Verify the first move
on each motor and allow the initial standstill and subsequent constant-speed
tuning segment when qualifying the motion profile. [ADI §6.1, Figure 6.2](https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf#page=38) · [FluidNC stepper wake-up](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Stepper.cpp)

The other static checks support the nominal 12 V design. U1's divider gives
3.257–3.437 V at the specified 12 V feedback-voltage corners, leaving 68 mV
at the low corner above U11's maximum calculated release threshold. On L1
the VIN-to-C2 trace measures 2.50 mm and the 100 nF U2 bypass connects in
1.95 mm. U2's boot straps, 10 kΩ / 1 µF EN network, and U4's tied V3/VCC
supply match their application circuits. U9 and U10 implement the specified
enable polarities, including the physical ENN pull-up when U9 is disabled.
Each motor driver has a local 100 nF capacitor on each VS pin with 2.40–2.95 mm
top-layer paths, the specified charge-pump connections, and 16 grounded
thermal vias. Q6's source, drain, and gate drive agree with the fitted UMW
part. Rail load steps, driver VS slew at hot-plug, motor temperature, and
Q6 switching at the 10 µs PWM endpoints still require the assembled board.
[IC implementation and datasheets](#ic-implementation) · [Operating margins](#operating-margins) · [First-article measurements](../manufacturing/process.md#first-article-acceptance)

### Operating margins

| Circuit | Fit and operating margin |
| --- | --- |
| 12 V input | J1 is rated 5 A at the 2.5 A design load. Q1 has its drains on the fused input and sources on V12. F1 is 5 A. A 3 A current-limited adapter can sustain a fault below F1's opening current, so fault recovery depends on the adapter's overload behavior. [J1 drawing](https://jp.sameskydevices.com/product/resource/pj-102bh.pdf) · [UMW Q1 datasheet][UMW AO4407A] · [F1 opening times](https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d) |
| 3.3 V buck | At 12 V in, 3.347 V out and 0.60 A load, 6.8 µH at 400 kHz gives 0.89 A peak-to-peak ripple and 1.04 A nominal peak in L1. With −20% inductance, the 290 kHz minimum center frequency and −6% dither, the continuous-conduction estimate is 1.41 A peak and 0.76 A RMS. U1 can skip pulses at light load. Cjiang lists 7.8 A typical saturation current for L1, above U1’s 6 A maximum high-side current-limit threshold. Its typical 20 °C-rise current is 4.8 A. The 0.1% divider and TI’s FB limits give 3.257–3.437 V static at 12 V, before divider temperature drift, distribution drop and transients. U11’s maximum rising threshold is 3.08 × 1.02 × 1.015 = 3.189 V, leaving 68 mV of static release margin. The high corner is 163 mV below the 3.6 V logic limit. C2 provides about 15 µF typical at 12 V bias, or about 12 µF with −20% initial tolerance applied to that curve. TI recommends over 10 µF local ceramic input capacitance. C1 adds 220 µF of bulk storage. At 3.3 V, C4/C5 contribute about 44 µF typical near U1 and C6 adds about 15 µF. With 59 µF, TI’s Equation 14 estimates 26 kHz crossover before feed-forward. Check transient response and hot fault recovery on the first article. [TI datasheet, §§5.5, 7.2 and 7.4](https://www.ti.com/lit/ds/symlink/tps54302.pdf) · [Cjiang FEXL0550A land pattern and ratings](https://datasheet.lcsc.com/datasheet/pdf/f40adaf039c1475297db7da23c31da4d.pdf) · [Taiyo Yuden C2 bias curve, p. 2](https://static6.arrow.com/aropdfconversion/390ef171f49858851c7ebe9f223658ce3b0cd44a/msast32mab5476mpndt1ss.pdf) · [Murata C4/C5 bias data](https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR61A476ME15%22%5D) |
| Motor current and layout | U5/U6 have the specified 5 mm QFN, 0.50 mm pitch, nominal 3.7 mm grounded pad and 22 nF / 50 V pump capacitors. ADI recommends short, equal sense paths. Both X pin-to-shunt traces are 3.00 mm long and have the same length at each width. The Y traces measure 2.37 and 2.41 mm. For 35 µm copper at 20 °C, the estimated trace resistance is 3.59 mΩ on both X phases and 3.56/3.61 mΩ on Y, excluding pads and ground returns. With 0.100 Ω shunts and a 0.800 A RMS request, TMCStepper selects the 180 mV sense range and IRUN = 23. The nominal winding current is 0.7955 A RMS per phase (1.125 A sine peak). Measure the winding current with the intended motors. Under standard reset settings with open VREF, an enabled driver can request about 1.40 A RMS. These figures exclude resistor tolerance, copper resistance and IC variation. [ADI datasheet, §§6, 9, 21–22][TMC2209 datasheet] · [TMCStepper current calculation](https://github.com/teemuatlut/TMCStepper/blob/v0.7.3/src/source/TMCStepper.cpp#L18-L41) |
| Solenoid | U9 drives Q7 through 2.2 kΩ R21. R22 pulls the base to ground during reset or disarm, and R33 returns Q6's gate to its source. The 5 A input fuse and adapter are shared by the board. The solenoid branch has no dedicated current limit or fault feedback. |

### Q6 switching margins

D6 (yellow, SOL CMD) follows GPIO32 before the hardware interlock. D9 (blue,
SOL) and R46 (5.1 kΩ) form a separate branch across the J5 terminals.
At 12 V the branch draws about 1.8 mA. D9 follows the output PWM and can
light with the coil unplugged.

At 12 V, allowing 0.2 V across saturated Q7 gives 3.69 mA through R33 and R45
and −8.1 V from Q6 gate to source. UMW specifies 18.5 mΩ maximum at −4.5 V
and 25 °C. Using that figure at 0.8 A gives about 15 mV drop and 12 mW
conduction loss at full duty. On-resistance rises with junction temperature.
[UMW AO4407A, pp. 3 and 5][UMW AO4407A]

When D4 conducts at turn-off, Q6 sees the local V12 rail plus D4's forward
drop across source and drain. Harness ringing and rail surges add to that
stress. UMW rates Q6 for −30 V drain-to-source and ±25 V gate-to-source.
R33 alone turns Q6 off through 2.2 kΩ. UMW measured switching times with a
3 Ω generator. At the configured 1 kHz, a 1% on- or off-interval is 10 µs.
Use measured edges to establish the usable duty range with the intended coil
and harness. [UMW AO4407A, pp. 1 and 3][UMW AO4407A] ·
[First-article measurements](../manufacturing/process.md#first-article-acceptance)

### JLC China availability

Before the R43 and D2 substitutions on 24 November 2026 all 43 SMT ordering codes and all four hand-soldered codes
in the generated BOM had domestic stock for a two-board build. The JLC China
SMT catalog showed 41,963 pieces of UMW AO4407A (C2841482), used at both
Q1 and Q6, and 6,959 pieces of the AOS alternate (C16072). Q7 uses C20526
MMBT3904 with over four million pieces. The lowest reported SMT balance
was L1 (1,379 pieces). The PJ-102BH through-hole jack had 68 pieces.
[JLC China BOM matcher](https://www.jlc-smt.com/bom) · [UMW AO4407A](https://www.jlc-smt.com/lcsc/detail/C2841482.html) · [AOS alternate](https://www.jlc-smt.com/lcsc/detail/C16072.html) · [MMBT3904](https://www.jlc-smt.com/lcsc/detail/C20526.html)

| Reference | Stocked ordering code | Compatibility with the board |
| --- | --- | --- |
| Q1, Q6 | UMW AO4407A, C2841482 | The −30 V P-channel MOSFET uses a 1.27 mm pitch SOP-8. Pins 1–3 are source, pin 4 is gate and pins 5–8 are drain. The AOS AO4407A (C16072) fits the same lands and pinout. [UMW datasheet][UMW AO4407A] · [AOS datasheet](https://www.aosmd.com/sites/default/files/res/datasheets/AO4407A.pdf) |
| L1 | FEXL0550A-6R8M, C5378515 | 6.8 µH ±20%, 28.6 mΩ maximum DCR. The existing Bourns SRP5050FA footprint matches the 4.7 × 1.25 mm recommended lands and 2.0 mm gap. Both parts have a 5.5 × 5.3 × 4.8 mm nominal body. Allow 5.0 mm maximum part height for L1. The catalog pad 1 to pad 2 axis is 0°, giving 90° in the CPL. [Cjiang datasheet](https://datasheet.lcsc.com/datasheet/pdf/f40adaf039c1475297db7da23c31da4d.pdf) |
| C4, C5 | GRM21BR61A476ME15L, C124129 | The L and K suffixes identify reel size. Both contain the same 0805, 47 µF, 10 V X5R capacitor with the same DC-bias curve. [Murata datasheet](https://search.murata.co.jp/Ceramy/image/img/A01X/G101/ENG/GRM21BR61A476ME15-01A.pdf) |
| R44 | RT0603BRD0722K1L, C723484 | 22.1 kΩ ±0.1%, 100 mW, ±25 ppm/°C, 0603. R43 is the matching 102 kΩ, 0.1% upper resistor (C861068). [Yageo datasheet](https://yageogroup.com/component-documentation/download/specsheet/RT0603BRD0722K1L) |

R17–R20 use Yageo RL1206FR-7W0R1L, 0.100 Ω, 1%, 0.5 W in 1206
(C859927), included in the original domestic stock check. On 24 November
2026 the domestic catalog showed 7,842 pieces of the revised R43 and 1,004
of D2. [R17–R20](https://www.jlc-smt.com/lcsc/detail/C859927.html) ·
[R43](https://www.jlc-smt.com/lcsc/detail/C861068.html) · [D2](https://www.jlc-smt.com/lcsc/detail/C151252.html)

J1 (C3095964), J3/J4 (C144395), J5 (C5188434) and C1/C15/C22 (C5111097)
are purchased for manual installation. Upload only the SMT BOM for placement.

The minimum chip resistor and capacitor size is **0402 imperial** (1005 metric,
1.0 × 0.5 mm nominal). The six fitted parts of this size are the three 100 nF
CP2102N bypass capacitors C10/C11/C29, the UART series resistor R28,
the CP2102N reset pull-up R47 and the supervisor output resistor R40.
All other fitted chip resistors and capacitors are 0603 or larger.

### International IC availability

JLCPCB’s public international parts catalog reported the quantities below on
23 November 2026 for U2–U11. They describe that catalog before assembly losses. JLC
China order allocation and replenishment dates require a lot-specific quote.

| Ref | Manufacturer part number | JLCPCB reported pieces |
| --- | --- | ---: |
| U1 | TPS54302DDCR | [C311983 listing](https://jlcpcb.com/partdetail/TexasInstruments-TPS54302DDCR/C311983) |
| U2 | ESP32-WROOM-32UE-N4 | [9,712](https://jlcpcb.com/partdetail/C701344) |
| U3 | SP0503BAHTG | [C7074 listing](https://jlcpcb.com/partdetail/C7074) |
| U4 | CP2102N-A02-GQFN24R | [C969151 listing](https://jlcpcb.com/partdetail/C969151) |
| U5/U6 | TMC2209-LA-T, two per board | [21,405](https://jlcpcb.com/partdetail/C2150710) |
| U9 | SN74LVC2G125DCTR | [1,929](https://jlcpcb.com/partdetail/C206035) |
| U10 | SN74LVC1G132DBVR | [25,652](https://jlcpcb.com/partdetail/C403723) |
| U11 | TLV803EA30DBZR | [6,912](https://jlcpcb.com/partdetail/C5218924) |

Check available stock for U3 and U4 against the assembly quantity when ordering.

## Layout and enclosure

In `build/view/`, read `top-routing.svg` (L1) and `bottom-routing.svg` (L4) in
the same orientation, looking through the board from the component side.
J1 and J2 are on the right, J3 and J4 are along the lower edge, and J5 is
on the left. Use `component-reference.svg` to locate components by designator.

### Follow the outer-layer routes

| Board area | Top copper (L1) | Bottom copper (L4) |
| --- | --- | --- |
| 12 V input and buck | From J1 on the right, follow F1 and Q1 to the 12 V plane. Pick up the supply at C2 beside U1 in the upper left. U1 feeds the inductor, then C4 and C5. | Power distribution uses the inner planes. |
| USB-C and serial | Follow J2 D+/D− past the U3 shunt pads to the south edge of U4. The UART leaves the west side of U4. R28 sits beside the ESP32 TX pad. | TX and RX each make one 45° turn on L4 between their two vias. The USB connector escape also uses L4. |
| Reset and interlock | In the upper left, follow U11 through R40 and down between the pads of C33 and R2. The diagonal meets the switch trace, passes through TP9 and heads east toward the ESP32. From the ESP32 EN trace, a branch runs south to U10. | BOOT_N crosses beneath the LED feeds between Q4 and GPIO0 and also reaches rear probe TP1. |
| Status lights | U2 pin 30 runs to R26 and R24 for D7 (IDLE). Pin 31 runs to R27 and R25 for D8 (ALARM). Both rows sit below and to the left of U4. | Both LED signals use L1 throughout. |
| Solenoid | Follow U2 pin 8 through the interlock at U9, then R21, Q7 and Q6. From the Q6 drain bank, the wide trace runs left to D4 and J5 pin 1. From pin 1, the indicator trace angles down and right, then runs straight into R46. It continues left to D9 and straight up to J5 pin 2. | The command and switched output stay on L1. |
| Shared motor controls | From R10/R11, the UART runs to U6 on the right. From U9 pin 6, the disable line branches left to U5 and right past R9 and TP5 to U6. | The UART branch to U5 crosses the board horizontally and returns to L1 in line with pin 14. |
| X driver and J3 | From the two control vias, follow STEP through R31 to U5 pin 16 and DIR to pin 19. X_B2 runs from the driver to J3 pin 4 on top. | STEP and DIR each run south, then diagonally toward U5. Three winding traces run to J3 pins 1–3. |
| Y driver and J4 | DIR leaves U2 pin 36 toward the module center. STEP leaves pin 33 toward the board edge. At U6, STEP passes through R32 to pin 16 and DIR enters pin 19. | Both controls run south and turn once toward U6. DIR passes just west of the rear IO0 probe. All four winding traces reach J4 in pin order. |

### Copper details

- **Power input and buck.** The input runs from J1 through F1 and Q1 on L1.
  F1 provides overcurrent protection, Q1 blocks reverse polarity, and
  D1 clamps Q1's gate-to-source voltage. Its cathode shares the L1 feed
  from Q1 pin 2. Its anode connects straight across to the gate at pin 4,
  where the trace turns down to R1. D2 (Littelfuse SMBJ13A) has 13 V standoff and clamps to at most 21.5 V at the specified 28 A, 10/1000 µs pulse at 25 °C. This leaves 3.5 V to C2’s 25 V rating under that test condition. Qualify local peaks with the shipped adapter and harness. [Littelfuse SMBJ data](https://datasheet.lcsc.com/lcsc/Littelfuse-SMBJ11A_C224004.pdf)
  Its cathode reaches C1 through the
  L3 12 V plane, and two vias tie its anode to L2 ground. At U1, C2's
  positive pad feeds VIN directly. C2 ground and U1 ground each have two
  vias to L2. From U1 pin 2, a straight 2.18 mm trace, 0.55 mm wide, reaches
  L1. From the inductor's switch-side land, the C3 branch turns once
  onto a 45° diagonal to the capacitor. On the other side of L1,
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
  In the east, a rounded 3.3 V
  branch enters U6 between the Y control and winding routes. Ground
  wraps around its tip to reach the U6 thermal pad. The 12 V plane
  reaches C21 along the south side of the branch.
  The production Gerbers show continuous L3 ground under all 43 L4 digital
  and motor winding segments outside their own via and connector-pad clearances.
  All 28 routed vias and seven motor connector pins have a plated connection
  from the local L3 ground region to L2 within 2.0 mm, measured centre to
  centre. The largest spacing is 1.913 mm at the ESP32 end of ESP_RX.
- **USB and reset.** J2’s paired data traces reach U4 pins 3 and 4 past U3. C12 sits on the VBUS trace 1.62 mm from U3 pin 2. U4 pin 8 senses VBUS through R29/R30. R5 and R6 sit directly below Q3. DTR and RTS connect to both transistor branches on L1. The DTR path from U4 to Q4 has two bends. R8 sits directly below the DTR branch point, 3.07 mm of top copper from pin 23. The RTS path from U4 to R6 has one bend. The ESP32 UART crosses this area on L4 with 0.22 mm traces. TX uses 5.01 mm of L4 after R28 and RX uses 6.23 mm. U4 pin 7 feeds C11 and C29 horizontally on L1. A 45° segment from C29 reaches C36 at the near end of the 4.7 µF bank. Pin 5 feeds C10 with one bend. The ground ends of C10, C11 and C29 share a local via to L2. Two parallel 0.40 mm top traces run down the power and ground pads of C36–C38. R8 uses a separate 1.03 mm connection to its L3 supply via.

  On the connector side of U4, the VBUS sense trace runs north to R30 and
  continues horizontally to R29. The top-layer sense path from pin 8 to R29
  measures 8.46 mm. Pin 9 reaches its reset
  pull-up R47 in 1.54 mm on the top layer.

  From Q3, follow ESP_EN across the upper end of U2 to its EN pin. On
  the left, the reset supervisor U11 connects through R40 to the same
  trace as SW1 and TP9. The rear recovery pads TP1 (IO0) and TP2 (GND)
  are 2.50 mm apart.
- **Indicators.** The two GPIO signals leave U2 on L1 and turn south
  toward the rows below U4. The upper row runs from the R27 pull-down
  through R25 to D8 (ALARM). The lower row runs from R26 through R24
  to D7 (IDLE). From the GPIO pad to the series-resistor input the
  paths measure about 7.0 mm and 9.0 mm, respectively. Each series
  resistor's output pad connects horizontally to its LED anode in 1.56 mm.
- **Interlock.** On L1, follow ACTUATOR_ARM from U2 pin 12 through the
  R35 pull-down junction to U10 pin 1. ESP_EN runs beside it into pin 2.
  From U10 pin 4, follow the diagonal through TP12 to both U9 enable pins.
  The driver-disable command from U2 pin 16 passes through the signal pad
  of R37 on its way to U9 pin 2. R37 takes 3.3 V from C32.
- **Solenoid.** On L1, SOL_CMD leaves U2 pin 8, passes between the pads
  of R21, then meets R38 and R23 on its way to U9 pin 5. The buffered
  output, SOL_SAFE, runs straight from U9 pin 3 to R21. From R21 pad 2,
  SOL_ENABLE runs left through TP14 to R22. A straight branch from TP14
  reaches the base of Q7. Its collector runs straight up to R45, whose
  other pad lines up with R33 pad 2 and Q6's gate. The four drain pads
  join a wide top-layer bus to D4
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
  drop to L4. Each turns once toward U5. STEP continues diagonally across
  its via and through the R31 pull-down pad, then turns into pin 16. DIR goes straight
  from its via to pin 19. U5 and U6 both use a 90° footprint rotation.
  X_A2 leaves pin 21 to the left and launches diagonally from its via
  toward J3. The adjacent X_A1 via has copper lands on L1 and L4.
  The inner planes clear its drill, leaving ground beneath the X_A2 trace.
  X_B2 runs directly to J3 pin 4 on L1 over L2 ground.
  X_B1 runs between shunts R17 and R18
  before joining X_A1 and X_A2 on L4. The three parallel diagonals terminate
  at J3 pins 1 (A1), 2 (A2) and 3 (B1). R17 and R18 face each other.
  Follow the matching sense traces from U5 pins 23 and 27 to their inner
  pads. Each outer pad has two ground vias.
- **Y motor.** STEP and DIR each run south on L4 and turn 45° toward U6.
  Both diagonals continue across their driver-side vias onto L1. Follow
  STEP through R32 to pin 16 and DIR to pin 19. Below U6, pins 4 and 5
  fan out symmetrically to C25, with C26 on the same row. The L3
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
| U5/U6 winding outputs | 0.25–0.35 mm at the driver, 0.55–0.60 mm on longer runs | 0.80 A RMS per phase, 1.13 A peak (rounded design values) |
| U5/U6 current-sense pins to shunts | 0.30 and 0.50 mm on X, 0.25 and 0.45 mm on Y | Same phase current |
| Buck and ESP32 | 0.55 mm switch trace, 1.00 mm from the inductor to C5, 0.635 mm at U2 | 0.60 A on 3.3 V, including 0.50 A at U2 |

C16 bypasses U5's 3.3 V digital I/O supply. The L3 supply via sits on
the 1.62 mm trace between C16 and U5 pin 15, 0.83 mm from the capacitor.
C16's ground pad connects directly to a ground via on its other side.
Both traces are 0.30 mm wide. U5 takes motor power through its two 12 V
supply pins.
[TMC2209 datasheet, §§3 and 20.2][TMC2209 datasheet]

With 35 µm outer copper at 70 °C, each 0.50 mm fuse neck dissipates
about 1.8 mW at 2.5 A. The DC winding paths from U5/U6 to J3/J4 measure
12–23 mΩ per lead using routed lengths and widths, a 1.53 mm via barrel and
18 µm via-wall plating. At 0.80 A RMS the highest-loss lead dissipates
about 14.7 mW. Each 0.100 Ω shunt dissipates up to 0.064 W averaged over a
sine cycle and 0.128 W at a 1.13 A crest. Check shunt temperature against
the 0.5 W part's derating curve in the assembled enclosure.

Each driver has 16 filled and capped exposed-pad vias into the ground
copper. ADI's thermal example already gives 2.8 W per driver at 1.4 A RMS
under its 24 V short-duration test. Continuous dual-axis operation at 12 V
depends on heat dissipation in the fitted enclosure. Qualify both drivers
together at the specified ambient and payload. [ADI datasheet, §20.3][TMC2209 datasheet]

- **12 V rail, 2.50 A design budget.** At 0.80 A RMS and 1.6 Ω per cold
  winding, the two 17HD4401S motors together dissipate about 4.1 W in
  copper. The 0.8 A coil adds 9.6 W. The 30 W continuous board budget
  leaves 16.3 W for hot-winding resistance rise, mechanical output, drivers,
  logic and board losses. The 3 A adapter supplies up to 36 W. Measure J1
  current and driver VS directly during loaded acceleration and braking.
- **3.3 V rail, 0.60 A total.** Measure the local rail at the CP2102N and ESP32 during combined USB, Wi-Fi and actuator operation.

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

Both lanes use one short L4 escape between J2 and U3 with a nearby ground return at each transition. From the U3 data pads the pair continues on L1 into U4. The routed lengths differ by 0.50 mm for either plug orientation, excluding via barrels and package internals.

The straight portions on both outer layers use 0.26 mm wide traces with a 0.20 mm edge gap. L1 references L2 GND and L4 references the local L3 GND region. Between the U3 shunt pads the traces use 0.22 mm width and 0.16 mm gap. They widen as they separate to meet the data pads. At the bridge, the 45° section uses 0.27 mm traces with a 0.19 mm edge gap. The final QFN approach uses 0.28 mm traces on the 0.50 mm pin pitch.

| Cross-section | PCB sample location in mm | Estimated differential impedance, JLC China process |
| --- | --- | ---: |
| L1 straight pair | X = 154.35, 154.72, 155.07, 155.67, 156.10, 156.29, 156.54 and 156.67, centred at Y = 63.80 | 90.5–91.9 Ω |
| L4 straight pair | X = 160.18 and 160.42, centred at Y = 62.88 | 90.9–91.2 Ω |
| L1 between U3 pads | X = 157.65, centred at Y = 63.80 | 89.7–92.0 Ω |
| L1 diagonal and QFN approach | Normal to the pair at (153.30, 63.025) and (152.40, 61.94) | 89.4–91.0 Ω |

At X = 154.11 on L1, the Y-directed slice crosses D+ after its bend and D− obliquely before its bend. This cut gives 85.6–85.8 Ω in 2D. The bend itself requires a 3D model or a measurement.

At X = 160.64 on L4 the section crosses the D+ via land. Its wider copper gives a local 2D estimate of about 81.6 Ω. The complete via transition also includes the barrel and reference-plane openings.

The 2D quasi-static estimates use the routed copper and refilled ground. For the specified JLC04161H-7628 stackup, both outer layers have 0.2104 mm of 7628 prepreg (Dk 4.4) to their reference plane. The JLC China calculation uses 40.64 µm finished outer copper and a trace top 12.70 µm narrower than the base. The solder mask has Dk 3.8 and is 15.24 µm over copper and 25.40 µm over the laminate and between traces. [JLC stackup] · [JLC China calculation parameters](https://www.jlc.com/portal/q7i37381.html)

The ranges cover the sampled locations and two assumptions for nearby VBUS and 3.3 V copper, omitted or treated as AC ground. Fabrication tolerances and the three-dimensional effects at pads, bends and vias require separate validation. Request an L1 and an L4 differential TDR coupon, each with an 81–99 Ω acceptance window, and verify the assembled USB channel with the full-speed waveform test. [Fabrication requirements](../manufacturing/process.md#bare-board-fabrication)

[USB Type-C Rev 2.4, Table 3-5, note 2]:
  https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/USB-Type_2D00_C-Spec-R2.4-_2D00_-October-2024.pdf
[JLC stackup]: https://jlcpcb.com/impedance
[TMC2209 datasheet]: https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf
[TI USB layout guidance]: https://www.ti.com/lit/an/slla414a/slla414a.pdf

[UMW AO4407A]: https://www.umw-ic.com/static/pdf/5e7bac0574bc94a52e928614220994e9.pdf
