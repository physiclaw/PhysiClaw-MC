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
| U3 TPD4E05U06DQAR | Pins 1, 2 and 5 clamp D−, D+ and VBUS to ground. Pins 3 and 8 each have a short return to L2. Typical line capacitance is 0.5 pF at 2.5 V and 1 MHz. [TI datasheet, Table 4-2 and §5.4](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf) |
| U4 CP2102N-A02-GQFN24R | VIO, VDD and VREGIN use the board’s regulated 3.3 V. R47 pulls RSTb up through 1 kΩ. Pins 3 and 4 connect directly to D+ and D−. [Silicon Labs, figures 2.3 and 2.6](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf) |
| U5/U6 TMC2209-LA-T | Each driver has 100 nF at each VS pin, 220 µF bulk, 22 nF across CPI–CPO, 100 nF across VCP–VS and two 0.100 Ω shunts with separate ground returns. CLK is grounded. MS1/MS2 select addresses 0 and 1. VREF is open for digital current scaling. [ADI datasheet §§2, 3, 21][TMC2209 datasheet] · [FluidNC driver initialization](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TMC2209Driver.cpp) |
| Q6 AO4407A and Q7 MMBT3904 | Q6 source pins 1–3 connect to V12 and drain pins 5–8 feed J5 pin 1. Q7 sinks the gate through R45. R33 returns the gate to V12 when Q7 is off. D4 returns flyback current from ground to the switched output. [UMW datasheet][UMW AO4407A] · [CJ datasheet](https://www.jscj-elec.com/gallery/file/MMBT3904%20SOT-23V2.pdf) |
| U9 and U12 SN74LVC1G125DBVR | Both OE pins (1) share ACT_OE_N. U9 buffers DRV_DISABLE_CMD to DRIVERS_DISABLE. U12 buffers SOL_CMD to SOL_SAFE. On each chip A is pin 2 and Y is pin 4. When disabled, R9 pulls ENN high and R22 pulls the Q7 base low. C39 bypasses U9 and C31 bypasses U12, each with 100 nF. [TI datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc1g125.pdf) |
| U10 SN74LVC1G132DBVR | The Schmitt NAND enables U9 and U12 when ESP_EN and ACTUATOR_ARM are both high. R35 pulls ARM low at startup. C32 is 100 nF. [TI datasheet](https://www.ti.com/lit/ds/symlink/sn74lvc1g132.pdf) |
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

Datasheets used for the current circuit include TPS54302 rev. C, ESP32-WROOM-32UE v2.1, CP2102N rev. 1.5, TI TPD4E05U06 rev. O, TMC2209 rev. 1.09, SN74LVC1G125 rev. U, SN74LVC1G132 rev. E and TLV803E rev. J.

Firmware findings use the tagged source and the project's cited TMCStepper
v0.7.3. FluidNC's build accepts a range of library versions. A UART capture
on the shipped image can establish the actual register sequence.
[Manufacturer links](#ic-implementation) · [FluidNC dependency range](https://github.com/bdring/FluidNC/blob/v4.1.1/platformio.ini)

**USB host detection and power sequencing.** J2 VBUS reaches U4 pin 8 through R29 (22.1 kΩ) with R30 (47.5 kΩ) to ground. At 5.0 V the nominal sense voltage is 3.41 V. At 4.4 V and opposing 1% tolerances the lower bound is 2.98 V before leakage. The board’s 3.437 V high supply corner gives a 2.837 V input-high requirement. Silicon Labs explicitly permits the divider to limit input current while VIO is off. U3 uses three steering-diode channels and a shared internal TVS to ground. VBUS connects to a protected I/O channel. [Silicon Labs, §2.3 and tables 3.7, 3.10](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=9) · [TI functional block diagram](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf)

**Bridge supply and UART.** VIO (5), VDD (6) and VREGIN (7) share 3.3 V. Figure 2.3 calls for 100 nF and 4.7 µF close to each power pin. The top-layer paths from pins 5, 6 and 7 to C10, C11 and C29 (100 nF) measure 1.57, 2.31 and 2.32 mm respectively. The three 4.7 µF capacitors share parallel 3.3 V and ground traces beside U4. Top-layer paths from pin 7 to C36, C37 and C38 measure 4.00, 5.55 and 7.10 mm respectively. Check VDD at C11 under load against the 3.0–3.6 V operating range. Pin 2 and the exposed pad return to ground. TXD (21) drives ESP_RX and RXD (20) receives ESP_TX through R28. DTR (23) and RTS (19) drive the auto-download circuit. [Silicon Labs, figure 2.3 and §5.2](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf)

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
If boot reaches Idle, the board's `after_reset` macro releases U9 and U12. A later
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
circuit. The 25 November first-article guide accepted motion down to 4.75 V.
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
1.95 mm. U2's boot straps and 10 kΩ / 1 µF EN network match Espressif's
application circuit. U9, U10 and U12 implement the specified
enable polarities, including the physical ENN pull-up when U9 is disabled.
Each motor driver has a local 100 nF capacitor on each VS pin with 2.40–2.95 mm
top-layer paths, the specified charge-pump connections, and 16 grounded
thermal vias. Q6's source, drain, and gate drive agree with the fitted UMW
part. Rail load steps, driver VS slew at hot-plug, motor temperature, and
Q6 switching at the 10 µs PWM endpoints still require the assembled board.
[IC implementation and datasheets](#ic-implementation) · [Operating margins](#operating-margins) · [First-article measurements](../manufacturing/process.md#first-article-acceptance)

### PCB and firmware review, 26 November 2026

The reviewed working tree was based on `b9d06f1` and included the CP2102N,
TPD4E05U06 and two single-channel actuator buffers. The PCB SHA-256 begins
with `8060468afd06c428`. KiCad 10.0.8 reported zero ERC and DRC violations,
unconnected items or schematic-parity issues after zone refill. All 53
repository tests passed. All 385 numbered component pins agreed between
the exported netlist and the PCB. All 107 fitted references (51 MPNs)
matched the schematic, PCB, assembly BOM and supplier table. The full
manufacturing build passed. Production qualification remains open.

**Motor enable after incomplete configuration.** U10 releases the buffers
when ESP_EN and GPIO27 are high. The circuit has no driver-ready input.
FluidNC v4.1.1 checks each driver's UART before writing its current and
microstep settings. A later move can assert the shared ENN even if setup
failed. With factory defaults, the fitted shunts give about 1.40 A RMS at
full run scale and the X/Y straps select 8/32 microsteps. A partial setup
has a second failure mode. FluidNC turns off analog current scaling before
programming the sense range and run current. If only the first of those
writes takes effect, the nominal full-run target becomes
`0.325 V / (√2 × 0.120 Ω) = 1.92 A RMS`. Successful setup gives 0.796 A
RMS and 16 microsteps on both axes. These are calculated current targets.
Keep ENN high until both addresses have accepted their configuration.
Check readable registers and the IFCNT increment across write-only settings.
Repeat after a driver reset. Program SENDDELAY ≥ 2 on both addresses before
the first read. The library sequence here uses the project's referenced
TMCStepper v0.7.3. Capture the actual release image on the bus.
[FluidNC register order](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TMC2209Driver.cpp#L66-L96) ·
[Shared enable](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Machine/Axes.cpp#L66-L92) ·
[TMCStepper current calculation](https://github.com/teemuatlut/TMCStepper/blob/v0.7.3/src/source/TMCStepper.cpp#L22-L40) ·
[ADI §§3.4, 4.1.2, 8–9 and 17][TMC2209 datasheet]

**Motor-supply brownout.** U11 monitors 3.3 V. U1 can regulate at 5 V
input, while U5/U6 require VS ≥ 5.5 V with their internal 5 V regulators.
A sustained input sag can therefore take the motors outside their operating
range while the ESP32 remains armed. A deeper or local dip can also reset a
driver independently. On the first article, capture VS, TP3, TP5 and TP12
during a controlled sag and recovery. Check the driver's reset flag and
configuration before resuming motion. Monitor VS or add a motor-supply
inhibit if motion must be prevented throughout this interval.
[TI TPS54302 §§5.3, 6.3.5](https://www.ti.com/lit/ds/symlink/tps54302.pdf) ·
[ADI §§17 and 20][TMC2209 datasheet]

**Open motor winding.** With both axes configured for StealthChop and
automatic PWM scaling, an open winding can make the driver increase current
in the intact winding. The boot UART test checks communication. The shipped
configuration enables no winding diagnostic. ADI describes a SpreadCycle
open-load test after at least four full steps at low or nominal speed, or
monitoring PWM_SCALE_SUM against a characterized range. Qualify this with
the actual motor and harness, including a single open phase. The initial
StealthChop standstill tuning interval also needs verification on cold start.
[FluidNC driver setup](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TMC2209Driver.cpp#L84-L97) ·
[ADI §§6.1, 6.6.1 and 15.3][TMC2209 datasheet]

**USB discharge path.** On the reviewed board, each data line changed layers
twice before the active clamp. The J2 A6/A7 pair now runs through U3
to U4 on L1. B6 joins A6 on L1. B7 reaches the main pair through two vias before U3. Each
via has two nearby connections between its L3 and L2 ground references.
The enclosure ESD check covers USB traffic, ESP_EN and actuator enable. [Current routing and return paths](#usb-c)
[TI ESD layout guide §§2.1–2.4](https://www.ti.com/lit/an/slva680a/slva680a.pdf) ·
[U3 pin functions, table 4-2](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf)

The assembly review also found that a uniform 0.125 mm stencil gives the
eight narrow U3 apertures a 0.61 area ratio. The manufacturing guide records
the U3/U4 printing options and the separate machine bond needed for the
motor cases and frame with isolated M3 mounting rings.
[Stencil](../manufacturing/process.md#reflow-and-stencil) ·
[Motor harnesses and bonding](../manufacturing/process.md#motor-harnesses)

**Static checks that passed.** The 12 V input PMOS and TVS polarities,
the buck feedback and bootstrap connections, the ESP32 straps, the USB-C
CC resistors and self-powered VBUS divider, and the Q6/Q7 drive and D4
flyback polarity agree with their intended circuits. In the logic supply's
valid range, either ESP_EN low or ARM low disables both buffers. R9 then
holds ENN high and R22 holds Q7 off. The buck divider gives 3.257–3.437 V
at the 12 V feedback corners. Its low corner leaves 68 mV above the
supervisor's maximum release threshold before distribution loss or ripple.
Check that margin under load, both driver junction temperatures at 50 °C
enclosure air, and the solenoid's 10 µs PWM endpoints with the fitted coil.
[IC pinouts and application circuits](#ic-implementation) ·
[First-article measurements](../manufacturing/process.md#first-article-acceptance)

### IC pin-by-pin audit, 26 November 2026

All **156 numbered pins on the ten fitted ICs** match their intended nets on
the schematic and PCB, including 41 deliberately open pins. The motor-enable
logic still permits motion commands after an incomplete driver setup. Two
additional concerns are position tracking during service inhibit and the
ESP32 reset-low voltage with an attached USB host.

This audit used the working tree based on `b9d06f1`, PCB SHA-256
`8e9b2e4b57f775f8f4db15addb272a365e11a8a4918ae15680f35a1ac323315d`
and [the board configuration](../firmware/config.yaml). A fresh KiCad
10.0.8 XML netlist was compared by reference and pin number with the
manufacturer pin tables and numbered copper pads. The front-copper pad order
on all ten footprints follows the package top views, including the ground
pads under U2, U4, U5 and U6. All 385 exported component pins matched the
PCB. ERC, zone-refilled DRC and schematic parity reported
zero violations or unrouted connections under the project rules. All 52
repository tests passed. The following voltage and current values are
calculations. Bench results are pending.

#### Logic findings

1. **A failed driver setup can still enable both motors.** U9 drives both
   ENN pins. The Idle startup macro raises GPIO27 after `M5` and `$MD`.
   FluidNC skips configuration for a driver that fails its communication
   test, but a later jog still asserts the shared enable. With factory OTP
   and no accepted setup writes, the X/Y straps select 8/32 microsteps and
   open VREF gives about 1.40 A RMS at full run scale. Successful setup gives
   16/16 and 0.7955 A RMS. A partial setup that disables analog scaling while
   leaving full digital scale can request 1.92 A RMS. Keep TP5 high until
   both addresses pass register readback and the expected IFCNT increment
   across the write-only settings. Repeat after a driver reset.
   [FluidNC driver test](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TrinamicBase.cpp) ·
   [Register order](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Motors/TMC2209Driver.cpp) ·
   [Shared enable](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Machine/Axes.cpp) · [ADI §§2, 4, 8–9][TMC2209 datasheet]
2. **A jog while disarmed changes the reported position.** The service macro
   drops GPIO27. U9 releases ENN and R9 disables the power stages. STEP and
   DIR still run directly from U2 to each driver. FluidNC treats GPIO27 as
   a general-purpose output and counts commanded steps independently. If a
   jog is accepted while disarmed, the next absolute move starts from an
   incorrect position. On an unloaded fixture, compare the reported position,
   STEP and TP5 across a disarmed jog. Reject moves during inhibit or
   re-establish position before resuming after such a command.
   [Board macros](../firmware/config.yaml) ·
   [FluidNC digital output handling](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/GCode.cpp) ·
   [Step counting](https://github.com/bdring/FluidNC/blob/v4.1.1/FluidNC/src/Stepping.cpp)
3. **USB modem outputs can reduce reset-low margin.** During U11's reset
   hold, an actively high DTR can source current through R5 and Q3's
   base–collector junction into ESP_EN when RTS is also high. At 3.3 V,
   with ESP_EN at its 0.60 V reset limit, R3 supplies 270 µA. Assuming
   0.65 V across that junction, R5 supplies another 205 µA. Those paths
   alone drop 0.39 V across R40, leaving about 0.21 V for U11's output.
   Reverse transistor action can add current from Q3's physical emitter.
   TI specifies up to 0.30 V at its 3.3 V, 2 mA test point. The data
   do not establish the assembled margin at this lighter load. Capture
   U11 pin 2 and TP9 separately during a supervisor reset with USB active
   and both modem outputs high. Require TP9 at or below 0.60 V for at
   least 50 µs. Repeat with USB detached. SW1 grounds TP9 directly, so a
   push-button test alone misses this path.
   [TI §7.5](https://www.ti.com/lit/ds/symlink/tlv803e.pdf#page=8) ·
   [Espressif tables 9 and 15](https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf) ·
   [Q3 pinout](https://www.jscj-elec.com/gallery/file/MMBT3904%20SOT-23V2.pdf)
4. **Two drivers share a bus with the single-node reply delay.** The
   address straps and TX/RX resistor network are correct. ADI specifies
   `NODECONF.SENDDELAY ≥ 2` on every node. The reviewed FluidNC v4.1.1
   and TMCStepper v0.7.3 startup paths leave the reset value of zero.
   Set the delay at both addresses before the first read and verify
   alternating replies on the shipped image. FluidNC allows a range of
   TMCStepper dependency versions. [ADI §4.1.2][TMC2209 datasheet] ·
   [TMCStepper initialization](https://github.com/teemuatlut/TMCStepper/blob/v0.7.3/src/source/TMC2208Stepper.cpp) ·
   [FluidNC dependency constraint](https://github.com/bdring/FluidNC/blob/v4.1.1/platformio.ini)
5. **The supervisor cannot detect a motor-only supply sag.** U11 measures
   V3V3. The buck can keep that rail valid with 5 V at its input, while
   these two internally regulated drivers need at least 5.5 V at VS.
   Capture VS at U5/U6 and TP3, TP5 and TP12 during sag and recovery.
   Check each driver's reset flag and configuration before resuming.
   On cold start also check the first STEP against ENN. A zero enable
   delay gives no guaranteed stationary interval for StealthChop's
   initial calibration. [TI §§5.3 and 6.3](https://www.ti.com/lit/ds/symlink/tps54302.pdf) ·
   [ADI §§6.1, 17 and 20.1][TMC2209 datasheet]

#### Pin and net record

Numbers below are package pin numbers. “Open” denotes an individually
isolated pad. Paired columns give the actual connections for each fitted
copy of the same device.

**U1 · TPS54302DDCR.** The 102 kΩ / 22.1 kΩ divider gives 3.347 V nominal.
At 12 V input the reference and resistor limits give 3.257–3.437 V. The
low end is 68 mV above U11's maximum calculated release threshold before
ripple and distribution drop. [TI rev. C, table 4-1 and §5.5](https://www.ti.com/lit/ds/symlink/tps54302.pdf)

| Pin | Function | Net and endpoint |
| --- | --- | --- |
| 1 | GND | GND, feedback return R44 and local capacitor returns |
| 2 | SW | BUCK_SW to L1 and C3 pin 2 |
| 3 | VIN | V12, protected input with C2 and C1 to ground |
| 4 | FB | R43/R44 junction with C35 across the upper resistor R43 |
| 5 | EN | Open, internal bias enables the converter |
| 6 | BOOT | BUCK_BST to C3 pin 1, 100 nF to SW |

**U2 · ESP32-WROOM-32UE-N4.** The N4 module supports GPIO16/17 for the
motor UART. C6/C7 bypass the supply. The unused strapping inputs take
their documented reset defaults. [Espressif v2.1, §§3–4 and figures 8–9](https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf)

| Pin | Function | Net and endpoint |
| --- | --- | --- |
| 1, 15, 38, 39 | GND, including exposed pad 39 | GND |
| 2 | 3V3 | V3V3, C6 22 µF and C7 100 nF |
| 3 | EN | ESP_EN at TP9, shared with U10 pin 1, R3 pull-up, C8, SW1, Q3 and R40 |
| 4, 5, 6, 7 | SENSOR_VP, SENSOR_VN, GPIO34, GPIO35 | Four open input-only pins |
| 8 | GPIO32 | SOL_CMD to U12 pin 2, R38 pull-down and D6 command indicator through R23 |
| 9, 13, 26, 37 | GPIO33, GPIO14, GPIO4, GPIO23 | Open |
| 10, 11 | GPIO25, GPIO26 | X_STEP to U5 pin 16 with R31 pull-down, X_DIR to U5 pin 19 |
| 12 | GPIO27 | ACTUATOR_ARM to U10 pin 2, R35 pull-down |
| 14, 24 | GPIO12, GPIO2 | Open straps with internal pull-downs, 3.3 V flash selection and download-compatible GPIO2 |
| 16 | GPIO13 | DRV_DISABLE_CMD to U9 pin 2, R37 pull-up |
| 17–22, 32 | NC | All seven package pads open |
| 23, 29 | GPIO15, GPIO5 | Open straps with internal pull-ups |
| 25 | GPIO0 | BOOT_N at TP1, R4 pull-up, Q4 can select download at reset |
| 27, 28 | GPIO16, GPIO17 | TMC_RX via R11 (0 Ω) and TMC_TX via R10 (1 kΩ) to TMC_BUS |
| 30, 31 | GPIO18, GPIO19 | STATUS_IDLE and STATUS_ALARM to D7/D8 through R24/R25 |
| 33, 36 | GPIO21, GPIO22 | Y_STEP to U6 pin 16 with R32 pull-down, Y_DIR to U6 pin 19 |
| 34, 35 | RXD0, TXD0 | ESP_RX from U4 pin 21, ESP_TX_SRC via R28 (499 Ω) to U4 pin 20 |

**U3 · TPD4E05U06DQAR.** TI's four protected channels are electrically
equivalent. The D1+ and D1− names do not set USB polarity. Continuity from
J2 to U4 determines polarity. [TI rev. O, table 4-2 and functional diagram](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf)

| Pin | Function | Net and endpoint |
| --- | --- | --- |
| 1, 10 | D1+ clamp, NC routing pad | USB_DM_CONN from J2 A7/B7 to U4 pin 4 |
| 2, 9 | D1− clamp, NC routing pad | USB_DP_CONN from J2 A6/B6 to U4 pin 3 |
| 3, 8 | GND | Both grounded |
| 4 | D2+ clamp | Open spare channel |
| 5 | D2− clamp | USB_VBUS, J2 A4/A9/B4/B9 and divider input R29 |
| 6, 7 | NC routing pads | Both open. Pins 9 and 10 above use TI's permitted flow-through copper routing |

**U4 · CP2102N-A02-GQFN24R.** J2 CC1 and CC2 have independent 5.1 kΩ
pull-downs. R29/R30 follow the self-powered reference circuit, giving
3.41 V nominal at pin 8 with 5.0 V on VBUS. U4 runs from the local 3.3 V
supply. Qualify enumeration with USB already attached when 12 V comes up
because A02 erratum E110 affects the data-line state at power-on.
[Silicon Labs rev. 1.5, figures 2.3/2.6 and table 5.2](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf) ·
[A02 erratum E110](https://www.silabs.com/documents/public/errata/cp2102n-errata.pdf#page=3)

| Pin | Function | Net and endpoint |
| --- | --- | --- |
| 1, 18, 22, 24 | RI/CLK, CTS, DSR, DCD | Open, serial connection uses no hardware flow control |
| 2, 25 | GND, exposed pad | Both grounded |
| 3, 4 | D+, D− | USB_DP_CONN and USB_DM_CONN respectively, through J2/U3 copper |
| 5, 6, 7 | VIO, VDD, VREGIN | All V3V3, with C10/C11/C29 and C36/C37/C38 |
| 8 | VBUS sense | USB_VBUS_SENSE, R29 22.1 kΩ from USB_VBUS and R30 47.5 kΩ to GND |
| 9 | RSTb | USB_BRIDGE_RESET_N, R47 1 kΩ to V3V3 |
| 10, 16 | NC | Both open as required |
| 11–14 | GPIO3/WAKEUP, GPIO2/RS485, GPIO1/RXT, GPIO0/TXT | All four open |
| 15, 17 | SUSPENDb, SUSPEND | Both open outputs |
| 19 | RTS | USB_RTS_N to Q3 emitter and R6 feeding Q4 base |
| 20, 21 | RXD, TXD | ESP_TX from U2 pin 35 via R28, ESP_RX to U2 pin 34 |
| 23 | DTR | USB_DTR_N to Q4 emitter and R5 feeding Q3 base |

With U11 released, physical RTS low and DTR high pull ESP_EN low. RTS high
and DTR low pull GPIO0 low. Equal modem output levels release both digital
commands. For automatic download, GPIO0 must still be low when ESP_EN rises
and for at least 1 ms afterward. The module has its own 499 Ω in series
with TXD0, giving about 998 Ω from the SoC transmitter through R28 to U4
RXD. At a shared 3.3 V, Espressif lists 2.64 V minimum output high and
Silicon Labs lists 2.70 V minimum input high. The light RXD load should
give a higher actual level. Check U4 pin 20 against its local VIO minus
0.6 V during serial traffic and flashing.
[Espressif table 5, table 15 and figure 8](https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf) ·
[Silicon Labs table 3.7](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=13)

**U5 and U6 · TMC2209-LA-T.** The configured 4 µs STEP pulse and 1 µs
DIR setup exceed the driver timing minima with the internal clock. Each
motor connector puts winding A on pins 1–2 and winding B on 3–4. Check
the mating harness for actual winding continuity. [ADI rev. 1.09, §§2.2, 3, 9, 13 and 20][TMC2209 datasheet]

| Pin | Function | U5, X | U6, Y |
| --- | --- | --- | --- |
| 1 | OB2 | X_B2 to J3.4 | Y_B2 to J4.4 |
| 2 | ENN | DRIVERS_DISABLE from U9.4, R9 pull-up | Same net |
| 3, 18, 29 | GND, including exposed pad 29 | GND | GND |
| 4, 5 | CPO, CPI | X_CPO/X_CPI across C18, 22 nF | Y_CPO/Y_CPI across C25, 22 nF |
| 6 | VCP | X_VCP via C19, 100 nF to V12 | Y_VCP via C26, 100 nF to V12 |
| 7 | SPREAD | GND, StealthChop strap | GND |
| 8 | 5VOUT | X_5VOUT to C17, 4.7 µF to GND | Y_5VOUT to C24, 4.7 µF to GND |
| 9, 10 | MS1/AD0, MS2/AD1 | GND/GND, address 0 | V3V3/GND, address 1 |
| 11, 12 | DIAG, INDEX | Both outputs open | Both outputs open |
| 13 | CLK | GND, internal oscillator | GND |
| 14 | PDN_UART | TMC_BUS to R10/R11 and U6.14 | TMC_BUS to R10/R11 and U5.14 |
| 15 | VCC_IO | V3V3, C16 100 nF | V3V3, C23 100 nF |
| 16 | STEP | X_STEP, GPIO25 | Y_STEP, GPIO21 |
| 17 | VREF | Open, digital scaling after setup | Open |
| 19 | DIR | X_DIR, GPIO26 | Y_DIR, GPIO22 |
| 20 | STDBY | GND, internal regulator active | GND |
| 21, 24 | OA2, OA1 | X_A2 to J3.2, X_A1 to J3.1 | Y_A2 to J4.2, Y_A1 to J4.1 |
| 22, 28 | VS | V12, C13/C14 100 nF and C15 220 µF | V12, C20/C21 100 nF and C22 220 µF |
| 23, 27 | BRA, BRB | X_SENSE_A/B to R17/R18, each 0.100 Ω to GND | Y_SENSE_A/B to R19/R20, each 0.100 Ω to GND |
| 25 | Unused | GND, explicitly permitted by ADI | GND |
| 26 | OB1 | X_B1 to J3.3 | Y_B1 to J4.3 |

**U9, U10, U11 and U12 · actuator inhibit and reset.** U11 has the
standard DBZ pin order of the fitted TLV803EA30DBZR. Its active-low,
open-drain output and 200 ms nominal release delay act on ESP_EN.
[TI SN74LVC1G125 rev. U, §4](https://www.ti.com/lit/ds/symlink/sn74lvc1g125.pdf) ·
[TI SN74LVC1G132 rev. E, §4](https://www.ti.com/lit/ds/symlink/sn74lvc1g132.pdf) ·
[TI TLV803E rev. J, §§5–7](https://www.ti.com/lit/ds/symlink/tlv803e.pdf)

| Pin | U9, motor buffer | U12, solenoid buffer | U10, Schmitt NAND | U11, supervisor |
| --- | --- | --- | --- | --- |
| 1 | Active-low OE, ACT_OE_N | Active-low OE, ACT_OE_N | A, ESP_EN from TP9 | GND |
| 2 | A, DRV_DISABLE_CMD from GPIO13 | A, SOL_CMD from GPIO32 | B, ACTUATOR_ARM from GPIO27 | RESET_SINK to ESP_EN through R40, 820 Ω |
| 3 | GND | GND | GND | VDD, V3V3 with C33 |
| 4 | Y, DRIVERS_DISABLE to both ENN pins | Y, SOL_SAFE through R21 to Q7 base | Y, ACT_OE_N to both OE pins and R36 pull-up | — |
| 5 | VCC, V3V3 with C39 | VCC, V3V3 with C31 | VCC, V3V3 with C32 | — |

| ESP_EN | ARM | ACT_OE_N | Motor ENN | Solenoid |
| --- | --- | --- | --- | --- |
| Low | Either | High | R9 pulls high, disabled | R22 pulls Q7 base low, off |
| High | Low | High | R9 pulls high, disabled | R22 pulls Q7 base low, off |
| High | High | Low | Follows GPIO13, low enables | Follows GPIO32, high energizes |

These states apply with the logic rail in range. Q1 has drains 5–8 on
VIN_FUSED and sources 1–3 on V12. Q6 has sources 1–3 on V12 and drains
5–8 on J5.1. R33 returns gate 4 to V12 when Q7 is off. Q7 sinks the gate
through R45 when driven. D4 has its anode on ground and cathode on J5.1
for flyback. D6 indicates the PWM command and D9 follows the switched
terminal voltage. Neither measures coil current. Verify J5 switching
with the fitted coil, especially the 10 µs endpoints at 1 kHz.
[UMW AO4407A][UMW AO4407A] · [CJ MMBT3904](https://www.jscj-elec.com/gallery/file/MMBT3904%20SOT-23V2.pdf) ·
[First-article acceptance](../manufacturing/process.md#first-article-acceptance)

### Passive component review, 26 November 2026

The review covers all 78 fitted passives on the working board based on
`b9d06f1` (40 resistors, 36 capacitors, L1 and F1, across 29 order codes).
The KiCad schematic export and PCB agree on both pads of every passive.
Their values, footprints, MPNs and order codes agree with the assembly and
purchasing records. The design loads are 0.60 A on V3V3, 0.80 A RMS per motor
phase and a 12 V / 0.8 A coil. The adapter specification allows up to 13 V
steady and the enclosure qualification reaches 50 °C. Capacitances under
DC bias below are typical manufacturer data. [Board loads and first-article tests](../manufacturing/process.md#first-article-acceptance)

**Three margins need first-article evidence.**

| Circuit | Evidence and acceptance |
| --- | --- |
| U11 to ESP32 reset, R3/R5/R40 | With both USB modem outputs high, Q3 can feed current into ESP_EN while U11 sinks it through 820 Ω. At the 0.60 V ESP32 reset limit, R3 and the forward-biased Q3 base–collector path alone account for about 0.39 V across R40 at 3.3 V. That leaves about 0.21 V at U11, below its published 0.30 V maximum at the 2 mA test point. During a supervisor-initiated reset, measure U11 pin 2 and TP9 with USB detached and with DTR/RTS both high. Require TP9 ≤0.60 V for at least 50 µs. [Reset circuit analysis](#logic-findings) · [TI §7.5](https://www.ti.com/lit/ds/symlink/tlv803e.pdf#page=8) · [Espressif tables 9 and 15](https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf) |
| U1 input, C2 | The 47 µF, 25 V, ±20% X5R measures about 15 µF on the typical curve at 12 V and about 13–14 µF at 13 V. Applying −20% initial tolerance leaves roughly 10.4–11.2 µF at 13 V, close to TI’s recommendation of more than 10 µF local ceramic. Allowing a further 15% loss for temperature gives about 9 µF before aging. This is a conservative sensitivity calculation. The actual combined bias, temperature and lot minimum is unspecified. Verify effective capacitance at 13 V and the hottest measured C2 temperature, or qualify a part with a documented minimum above 10 µF there. Capture VIN at C2 and the 0.60 A load step at the high adapter limit. [Taiyo Yuden curve, p. 2](https://static6.arrow.com/aropdfconversion/390ef171f49858851c7ebe9f223658ce3b0cd44a/msast32mab5476mpndt1ss.pdf#page=2) · [TI §7.2.3.1](https://www.ti.com/lit/ds/symlink/tps54302.pdf#page=15) |
| U4 bypass, C10/C11/C29 and C36/C37/C38 | Silicon Labs calls for a nominal 100 nF and 4.7 µF at each of VIO, VDD and VREGIN. The three 16 V X7R small capacitors give about 96 nF each at 3.3 V. The three 16 V X5R bulk capacitors give about 3.27 µF each at 3.3 V and 3.19 µF at 3.437 V, before their ±10% tolerance. Figure 2.3 specifies nominal values without an effective-capacitance minimum. Measure 3.0–3.6 V at all three pins during USB traffic and simultaneous rail load steps. Samsung also lists the fitted bulk MPN as NRND and names CL10A475KO8NQN as the replacement family. Check its own bias curve before substitution. [Silicon Labs fig. 2.3 and table 3.1](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=6) · [Samsung 100 nF](https://product.samsungsem.com/mlcc/CL05B104KO5NNN.do) · [Samsung 4.7 µF](https://product.samsungsem.com/mlcc/CL10A475KO8NNN.do) |

**Power, motor and logic components**

| Fitted references | Fit at the design load |
| --- | --- |
| C1, C15, C22 | Each Nichicon UHV is 220 µF ±20%, 35 V, with 59 mΩ maximum impedance at 100 kHz and 20 °C. C15 and C22 each retain at least 176 µF at initial tolerance versus ADI’s 100 µF local recommendation. Ripple ratings are 0.99 A RMS at 100 kHz and 105 °C and 0.495 A at 120 Hz. Verify the ripple current in each can against its frequency-corrected rating during combined motion, braking and PWM. Motor winding RMS current does not give capacitor ripple current. [Nichicon UHV](https://www.nichicon.com/en-us/part/uhv1v221mpd/6030/) · [ADI §3.1][TMC2209 datasheet] |
| F1, R1 and D1/D2 | F1 is 5 A / 32 V at a 2.5 A continuous design load. A 3 A current-limited adapter can sustain a fault without opening F1. R1 (100 kΩ) biases Q1 and D1 clamps its gate to source at nominally 12 V. D2 has 13 V standoff and a 21.5 V specified clamp at 28 A for its 10/1000 µs pulse. Cable ringing and motor regeneration require a local measurement. Require C2 below 25 V and both drivers’ VS below 29 V with rising slew below 1 V/µs. [Littelfuse 467](https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d) · [Littelfuse SMBJ](https://www.littelfuse.com/assetdocs/tvs-diode-catalog?assetguid=5e26c1d4-63ea-4a4a-b528-cff4330cd7ff) · [ADI §3.1][TMC2209 datasheet] |
| L1, C3, C4, C5, C35, R43, R44 | L1 is 6.8 µH ±20%, 28.6 mΩ max DCR, 7.8 A typical saturation and 4.8 A typical for 20 °C rise. The estimated nominal 1.04 A peak at full board load has ample margin. C3 is 100 nF X7R / 50 V between BOOT and SW. TI’s 3.3 V example uses 6.8 µH and 47 pF feed-forward. C35 is 47 pF ±5%, C0G / 50 V. The 102 kΩ / 22.1 kΩ divider uses 0.1%, 25 ppm/°C parts. At 12 V the static 3.257–3.437 V range leaves 68 mV at the low corner for supervisor release. C4/C5 are 47 µF ±20%, 10 V X5R, about 44 µF combined at 3.3 V. Including C6 and the three USB bulk caps gives roughly 69 µF typical, or about 22 kHz by TI Eq. 14 if lumped together. Confirm settling and rail limits on the populated board. [TI table 7-2 and Eq. 14](https://www.ti.com/lit/ds/symlink/tps54302.pdf#page=17) · [Cjiang FEXL](https://datasheet.lcsc.com/datasheet/pdf/f40adaf039c1475297db7da23c31da4d.pdf) · [Murata C4/C5 curve](https://prod-parts-data.s3.amazonaws.com/GRM21BR61A476ME15K/datasheet/1_GRM21BR61A476ME15K-Murata-datasheet-141278181.pdf) · [Yageo RT](https://yageogroup.com/component-documentation/download/specsheet/RT0603BRD07102KL) |
| C6, C7, C8, R3, R4, R5, R6, R7, R8, R28 | U2 has 22 µF ±20% X5R / 10 V (about 15 µF at 3.3 V) plus 100 nF X7R / 50 V. The 10 kΩ EN pull-up and 1 µF ±10% X5R / 16 V give the Espressif reference 10 ms nominal RC. R4 pulls GPIO0 high through 10 kΩ. R5/R6 are 10 kΩ base resistors, R7/R8 are 100 kΩ modem-line pull-ups. R28 is 499 Ω, giving about 998 Ω with the module’s internal TX resistor. Verify reset as above and UART highs at U4 RXD ≥ VIO − 0.6 V. [Espressif supply and reset guidance](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32/schematic-checklist.html) · [Murata C6 curve](https://datasheet.octopart.com/GRM21BR61A226ME44L-Murata-datasheet-138744833.pdf) · [Silicon Labs table 3.7](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=13) |
| R12, R13, R29, R30, R47, C12 | CC1/CC2 each have an independent 5.1 kΩ ±1% Rd. R47 matches the 1 kΩ bridge reset pull-up. At 4.4 V VBUS and opposing 1% tolerances, the 22.1 kΩ / 47.5 kΩ divider gives 2.984 V. Allowing 1.1 µA input leakage below VIO gives 2.967 V, above the 2.837 V threshold at the high VIO corner. C12 is 100 nF / 50 V on connector VBUS. U3 is a ground-referenced ESD array and the U4 data pins connect directly. [USB Type-C table 4-28](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/USB-Type_2D00_C-Spec-R2.4-_2D00_-October-2024.pdf) · [Silicon Labs figs. 2.3, 2.6 and table 3.7](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf) · [TI U3](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf) |
| C13, C14, C20, C21, C16, C23, C18, C25, C19, C26, C17, C24 | Each TMC2209 VS pin has 100 nF X7R / 50 V (about 93 nF at 12 V), each VCC_IO has 100 nF, and each pump has 22 nF / 50 V across CPI–CPO and 100 nF / 50 V from VCP to VS. These ceramics are ±10%. Each 5VOUT has 4.7 µF ±10%, 25 V X7R. At 5.25 V its typical 3.26 µF becomes about 2.49 µF with −10% initial tolerance and a further 15% temperature allowance, above ADI’s 2.2 µF lower recommendation. Check both 5VOUT waveforms at startup and under load. [ADI §§2–3][TMC2209 datasheet] · [Samsung VS capacitor](https://product.samsungsem.com/mlcc/CL10B104KB8NNN.do) · [Samsung pump capacitor](https://product.samsungsem.com/mlcc/CL10B223KB8NNN.do) · [Samsung 5VOUT capacitor](https://product.samsungsem.com/mlcc/CL21B475KAFNNN.do) |
| R17, R18, R19, R20 | Each Yageo RL1206 is 0.100 Ω ±1%, 0.5 W at 70 °C, matching the firmware sense value and ADI’s recommended package and power class. At 0.80 A RMS the sine-cycle dissipation is at most 64 mW per shunt and the crest is 128 mW. TCR is ±600 ppm/°C, permitting another ±2.7% resistance change from 25 to 70 °C. Including only the estimated 3.6 mΩ series sense trace in the current equation moves the nominal 0.796 A to about 0.772 A RMS. Verify winding current hot and cold. [Yageo RL tables 1–2](https://yageogroup.com/content/Resource%20Library/Datasheet/PYU-RL_GROUP_521_ROHS_L.pdf) · [ADI §§8–9, 20][TMC2209 datasheet] |
| R9, R10, R11, R31, R32, R35, R36, R37, R38, C31, C32, C33, C39 | The shared TMC UART uses 1 kΩ on TX and a 0 Ω link on RX. R31/R32 pull STEP low. R35/R38 pull ARM and SOL_CMD low. R36/R37 pull OE and disable-command high. R9 holds both ENN pins high when U9 releases them. Each 10 kΩ pull loads an actively opposing output by at most 0.37 mA at 3.6 V. Each buffer, NAND and supervisor has its own 100 nF ±10%, 50 V X7R bypass. [ADI §§2, 4][TMC2209 datasheet] · [TI buffers](https://www.ti.com/lit/ds/symlink/sn74lvc1g125.pdf) · [TI Schmitt NAND](https://www.ti.com/lit/ds/symlink/sn74lvc1g132.pdf) |
| R21, R22, R33, R45, C28, C34, D4 | U12 drives Q7 through 2.2 kΩ with 47 kΩ base to ground. R33 (2.2 kΩ) and R45 (1 kΩ) dissipate about 30 and 14 mW at steady 12 V ON, below their 100 mW ratings. The network gives Q6 about −8.1 V gate drive. C28 is 100 nF / 50 V. C34 is 10 µF ±10%, 50 V X7R and supplies about 4.65 µF at 12 V. The SS34 flyback diode is rated 40 V / 3 A for the 0.8 A coil. Verify its temperature and the 1 kHz switching edges with the fitted coil. [Samsung C34](https://product.samsungsem.com/mlcc/CL31B106KBHNNN.do) · [MDD SS34](https://yibeiic-shop.oss-cn-hangzhou.aliyuncs.com/media/collection/ss34-Re3GARDep-dqR6AGM1q.pdf) · [Q6 switching margins](#q6-switching-margins) |
| R2, R23, R24, R25, R26, R27, R46 and D3/D6/D7/D8/D9 | Each logic indicator has 2.2 kΩ in series. Even assuming zero LED forward drop, each draws under 1.66 mA at 3.6 V with −1% resistance. R26/R27 add 100 kΩ status pull-downs. R46 (5.1 kΩ) limits D9 to less than 2.58 mA at 13 V, with resistor dissipation below 34 mW. The ordinary UniOhm resistors are ±1% (except the zero-ohm link), rated 100 mW in 0603 and 62.5 mW in 0402. [UniOhm thick-film ratings](https://www.uni-royal.cn/en/product.php?id=19) |

### Operating margins

| Circuit | Fit and operating margin |
| --- | --- |
| 12 V input | J1 is rated 5 A at the 2.5 A design load. Q1 has its drains on the fused input and sources on V12. F1 is 5 A. A 3 A current-limited adapter can sustain a fault below F1's opening current, so fault recovery depends on the adapter's overload behavior. [J1 drawing](https://jp.sameskydevices.com/product/resource/pj-102bh.pdf) · [UMW Q1 datasheet][UMW AO4407A] · [F1 opening times](https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d) |
| 3.3 V buck | At 12 V in, 3.347 V out and 0.60 A load, 6.8 µH at 400 kHz gives 0.89 A peak-to-peak ripple and 1.04 A nominal peak in L1. With −20% inductance, the 290 kHz minimum center frequency and −6% dither, the continuous-conduction estimate is 1.41 A peak and 0.76 A RMS. U1 can skip pulses at light load. Cjiang lists 7.8 A typical saturation current for L1, above U1’s 6 A maximum high-side current-limit threshold. Its typical 20 °C-rise current is 4.8 A. The 0.1% divider and TI’s FB limits give 3.257–3.437 V static at 12 V, before divider temperature drift, distribution drop and transients. U11’s maximum rising threshold is 3.08 × 1.02 × 1.015 = 3.189 V, leaving 68 mV of static release margin. The high corner is 163 mV below the 3.6 V logic limit. C2 provides about 15 µF typical at 12 V bias, or about 12 µF with −20% initial tolerance applied to that curve. TI recommends over 10 µF local ceramic input capacitance. C1 adds 220 µF of bulk storage. At 3.3 V, C4/C5 contribute about 44 µF typical near U1 and C6 adds about 15 µF. With 59 µF, TI’s Equation 14 estimates 26 kHz crossover before feed-forward. Check transient response and hot fault recovery on the first article. [TI datasheet, §§5.5, 7.2 and 7.4](https://www.ti.com/lit/ds/symlink/tps54302.pdf) · [Cjiang FEXL0550A land pattern and ratings](https://datasheet.lcsc.com/datasheet/pdf/f40adaf039c1475297db7da23c31da4d.pdf) · [Taiyo Yuden C2 bias curve, p. 2](https://static6.arrow.com/aropdfconversion/390ef171f49858851c7ebe9f223658ce3b0cd44a/msast32mab5476mpndt1ss.pdf) · [Murata C4/C5 bias data](https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR61A476ME15%22%5D) |
| Motor current and layout | U5/U6 have the specified 5 mm QFN, 0.50 mm pitch, nominal 3.7 mm grounded pad and 22 nF / 50 V pump capacitors. ADI recommends short, equal sense paths. Both X pin-to-shunt traces are 3.00 mm long and have the same length at each width. The Y traces measure 2.37 and 2.41 mm. For 35 µm copper at 20 °C, the estimated trace resistance is 3.59 mΩ on both X phases and 3.56/3.61 mΩ on Y, excluding pads and ground returns. With 0.100 Ω shunts and a 0.800 A RMS request, TMCStepper selects the 180 mV sense range and IRUN = 23. The nominal winding current is 0.7955 A RMS per phase (1.125 A sine peak). Measure the winding current with the intended motors. Under standard reset settings with open VREF, an enabled driver can request about 1.40 A RMS. These figures exclude resistor tolerance, copper resistance and IC variation. [ADI datasheet, §§6, 9, 21–22][TMC2209 datasheet] · [TMCStepper current calculation](https://github.com/teemuatlut/TMCStepper/blob/v0.7.3/src/source/TMCStepper.cpp#L18-L41) |
| Solenoid | U12 drives Q7 through 2.2 kΩ R21. R22 pulls the base to ground during reset or disarm, and R33 returns Q6's gate to its source. The 5 A input fuse and adapter are shared by the board. The solenoid branch has no dedicated current limit or fault feedback. |

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
| U3 | TPD4E05U06DQAR | [C138714 listing](https://jlcpcb.com/partdetail/TexasInstruments-TPD4E05U06DQAR/C138714) |
| U4 | CP2102N-A02-GQFN24R | [C969151 listing](https://jlcpcb.com/partdetail/C969151) |
| U5/U6 | TMC2209-LA-T, two per board | [21,405](https://jlcpcb.com/partdetail/C2150710) |
| U9/U12 | SN74LVC1G125DBVR, two per board | [C23654 listing](https://jlcpcb.com/partdetail/C23654) |
| U10 | SN74LVC1G132DBVR | [25,652](https://jlcpcb.com/partdetail/C403723) |
| U11 | TLV803EA30DBZR | [6,912](https://jlcpcb.com/partdetail/C5218924) |

Check available stock for U3, U4 and the two C23654 buffers against the assembly quantity when ordering.

## Layout and enclosure

In `build/view/`, read `top-routing.svg` (L1) and `bottom-routing.svg` (L4) in
the same orientation, looking through the board from the component side.
J1 and J2 are on the right, J3 and J4 are along the lower edge, and J5 is
on the left. Use `component-reference.svg` to locate components by designator.

### Follow the outer-layer routes

| Board area | Top copper (L1) | Bottom copper (L4) |
| --- | --- | --- |
| 12 V input and buck | From J1 on the right, follow F1 and Q1 to the 12 V plane. Pick up the supply at C2 beside U1 in the upper left. U1 feeds the inductor, then C4 and C5. | Power distribution uses the inner planes. |
| USB-C and serial | Follow J2 D+/D− past the U3 shunt pads to the south edge of U4. The UART leaves the west side of U4. R28 sits beside the ESP32 TX pad. | TX and RX each make one 45° turn on L4 between their two vias. The A7–B7 crossover runs on L4 to the left of J2. A6–B6 uses L1 on the right. |
| Reset and interlock | In the upper left, follow U11 through R40 and down between the pads of C33 and R2. The diagonal meets the switch trace, passes through TP9 and heads east toward the ESP32. From the ESP32 EN trace, a branch runs south to U10. | BOOT_N crosses beneath the LED feeds between Q4 and GPIO0 and also reaches rear probe TP1. |
| Status lights | U2 pin 30 runs to R26 and R24 for D7 (IDLE). Pin 31 runs to R27 and R25 for D8 (ALARM). Both rows sit below and to the left of U4. | Both LED signals use L1 throughout. |
| Solenoid | Follow U2 pin 8 through the interlock at U12, then R21, Q7 and Q6. From the Q6 drain bank, the wide trace runs left to D4 and J5 pin 1. From pin 1, the indicator trace angles down and right, then runs straight into R46. It continues left to D9 and straight up to J5 pin 2. | The command and switched output stay on L1. |
| Shared motor controls | From R10/R11, the UART runs to U6 on the right. From U9 pin 4, the disable line branches left to U5 and right past R9 and TP5 to U6. | The UART branch to U5 crosses the board horizontally and returns to L1 in line with pin 14. |
| X driver and J3 | From the two control vias, follow STEP through R31 to U5 pin 16 and DIR to pin 19. X_B2 runs from the driver to J3 pin 4 on top. | STEP and DIR each run south, then diagonally toward U5. Three winding traces run to J3 pins 1–3. |
| Y driver and J4 | DIR leaves U2 pin 36 toward the module center. STEP leaves pin 33 toward the board edge. At U6, STEP passes through R32 to pin 16 and DIR enters pin 19. | Both controls run south and turn once toward U6. DIR passes just west of the rear IO0 probe. All four winding traces reach J4 in pin order. |

### Copper details

- **Power input and buck.** The input runs from J1 through F1 and Q1 on L1.
  F1 provides overcurrent protection, Q1 blocks reverse polarity, and
  D1 clamps Q1's gate-to-source voltage. Its cathode shares the L1 feed
  from Q1 pin 2. Its anode connects straight across to the gate at pin 4,
  where the trace turns down to R1. D2 (Littelfuse SMBJ13A) has 13 V standoff and clamps to at most 21.5 V at the specified 28 A, 10/1000 µs pulse at 25 °C. This leaves 3.5 V to C2’s 25 V rating under that test condition. Qualify local peaks with the shipped adapter and harness. [Littelfuse SMBJ data](https://datasheet.lcsc.com/lcsc/Littelfuse-SMBJ11A_C224004.pdf)
  TP10 connects straight to the D2 cathode over 3.70 mm of top copper.
  The cathode reaches C1 through the
  L3 12 V plane, and two vias tie its anode to L2 ground. At U1, C2's
  positive pad feeds VIN directly. C2 ground and U1 ground each have two
  vias to L2. From U1 pin 2, a straight 2.18 mm trace, 0.55 mm wide, reaches
  L1. From the inductor's switch-side land, the C3 branch turns once
  onto a 45° diagonal to the capacitor. On the other side of L1,
  a wide 3.3 V trace feeds C4 and C5. Two vias at
  C5 feed the 3.3 V plane. A separate sense trace runs from C5 to R43 and
  C35. Below U1, a straight trace joins the feedback ends of R44, R43 and
  C35. The 6.62 mm ground return leaves R44 vertically and reaches U1 pin 1 on the top layer. A copper-pour keepout
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
  The production Gerbers show continuous L3 ground under all 31 L4 digital
  and motor winding segments outside their own via and connector-pad clearances.
  All 26 routed vias and seven motor connector pins have a plated connection
  from the local L3 ground region to L2 within 2.0 mm, measured centre to
  centre. The largest spacing is 1.913 mm at the ESP32 end of ESP_RX.
- **USB and reset.** The main pair runs from A6/A7 through U3 to U4 on L1.
  The D+ contacts join on L1 to the right of J2. The 1.49 mm D− crossover
  runs on L4 to the left of the contact row in component-side view.
  On the right, a 7.72 mm top-layer VBUS trace joins A9/B4 to A4/B9.
  Both ends approach the straight section at 45°. From A4/B9, VBUS passes
  between the R12 pads to U3 pin 5 in 4.77 mm. C12 is 1.25 mm from the clamp. U4 pin 8 reaches R30 and R29 on the
  same vertical sense trace, 8.47 mm from pin 8 to R29. The reset pull-up
  R47 is 1.51 mm from pin 9.

  U4 pin 5 feeds C10 on a single diagonal. Its ground pad has a
  dedicated via 0.60 mm away. Pin 7 feeds C11 and C29 horizontally.
  Their ground pads share a separate local L2 return. Two parallel
  0.40 mm top traces connect the power and ground pads of C36–C38.

  R5 and R6 sit below Q3. The DTR and RTS transistor branches stay on
  L1. DTR to Q4 has two bends. R8 sits below its branch point, 3.07 mm
  of top copper from pin 23. RTS to R6 has one bend. R8 has a 1.03 mm
  connection to its L3 supply via. The 0.22 mm ESP32 UART traces use
  4.85 mm of L4 for TX after R28 and 6.15 mm for RX. The RX trace meets
  U2 pin 34 horizontally on L1.

  From Q3, follow ESP_EN across the upper end of U2 to its EN pin. On
  the left, the reset supervisor U11 connects through R40 to the same
  trace as SW1 and TP9. The rear recovery pads TP1 (IO0) and TP2 (GND)
  are 2.50 mm apart.
- **Indicators.** The two GPIO signals leave U2 on L1 and turn south
  toward the rows below U4. The upper row runs from the R27 pull-down
  through R25 to D8 (ALARM). The lower row runs from R26 through R24
  to D7 (IDLE). From the GPIO pad to the series-resistor input the
  paths measure 6.68 mm and 9.09 mm, respectively. Both GPIO feeds run vertically into their pull-down pads. Each series
  resistor's output pad connects horizontally to its LED anode in 1.56 mm.
- **Interlock.** On L1, follow ACTUATOR_ARM from U2 pin 12 through the
  R35 pull-down junction to U10 pin 2. ESP_EN enters the adjacent pin 1.
  U10 pin 4 drives both buffers. West of U10, the 4.07 mm enable trace
  runs straight through TP12 to U12 pin 1. East of U10, it passes through
  the R36 pull-up pad on its way to U9 pin 1. All three ICs face the
  same way. The motor command runs 7.41 mm from U2 pin 16 through
  R37 pad 2 to U9 pin 2. The final 1.68 mm runs straight south from R37.
  The upper-left pad of U9 is pin 3. Its 0.75 mm trace runs left to the
  ground via that connects it to L2. The buffered output leaves pin 4
  toward the drivers’ shared ENN trace.
- **Solenoid.** On L1, SOL_CMD leaves U2 pin 8 (GPIO32) and angles toward
  R23. The LED branch runs straight west through R23 to D6. The main trace
  runs straight south past the R38 pull-down pad into U12 pin 2, a total
  of 15.63 mm from GPIO32. U12 pin 4 connects straight west to R21 pad 1
  in 1.65 mm. From R21 pad 2, SOL_ENABLE runs straight north through TP14
  to the Q7 base, with a short branch west to R22. The ground end of R22
  runs 1.77 mm diagonally to its via. The Q7 collector runs
  straight up to R45, whose
  other pad lines up with R33 pad 2 and Q6's gate. Between drain pins 7
  and 8, a 1.00 mm wide trace runs straight left to D4. Follow the wider
  trace down from D4 to J5 pin 1. A separate via beside the Q6 source bank connects directly
  to the continuous L3 12 V plane. C28 and C34 share a second local feed.
- **Motor control.** The motor UART receive line leaves U2 pin 27 on a
  45° diagonal and turns once into R11. The shared bus runs from R10 and R11 between D2's
  pads on L1, then turns diagonally toward U6. Its final straight run
  passes between the pads of C23 and ends at U6 pin 14.
  For U5, follow the L1 diagonal from R10 to its via. The branch then
  runs left across the interlock on L4 and continues on the same line
  on L1 into U5 pin 14.
  On L1, DRIVERS_DISABLE leaves U9 pin 4 diagonally down and left, then
  runs straight down to the horizontal trace below the drivers.
  Left leads to U5 pin 2. Right passes the R9
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
  (pin 15), then continues to the via beside MS1/AD0 (pin 9).
  C23 has a local ground via. All four Y motor
  outputs approach J4 in pin order on L4 over L3 ground. Y_A1 runs beside
  Y_A2, then turns once into J4 pin 1. Y_B1 passes
  between the two shunts on L1 before changing layers. Y_B2 leaves
  U6 pin 1 and passes below C20 on L1. Its via sits directly above J4
  pin 4, with a straight 7.42 mm run down to the connector on L4.
  Each shunt has two ground vias, and
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

J2 A6 (D+) and A7 (D−) run side by side on L1 to U3 and then to the
CP2102N at U4. In component-side view, the A6–B6 tie is to the right of
the J2 pads on L1. The A7–B7 crossover runs on L4 to their left.
Each CC pin has a 5.1 kΩ pull-down.

| J2 contact tie | Bottom copper | Contact-centre planar length | Length including nominal via barrels |
| --- | ---: | ---: | ---: |
| A6–B6, D+ | None | 3.01 mm | 3.01 mm |
| A7–B7, D− | 1.49 mm | 4.15 mm | 7.35 mm |

A7 runs straight to U3 on L1 at the full 0.28 mm width. A 0.35 mm
branch connects the trace to the via, leaving 0.06 mm between the nominal
drill edge and the trace edge. On L4 the crossover takes one 45° turn
to reach the B7 via. The D− tie exceeds the 3.5 mm USB Type-C
shorting-trace recommendation even before adding its two 1.6 mm barrels.
Qualification includes the device transmit waveform in both plug orientations
and an enclosure ESD test during USB traffic.
[Espressif ESP32-C6-DevKitC-1 PCB layout, pp. 1–2](https://dl.espressif.com/dl/schematics/esp32-c6-devkitc-1-pcb-layout_v1.2.pdf) ·
[TI ESD layout guide, §§2.1–2.4](https://www.ti.com/lit/an/slva680a/slva680a.pdf) ·
[USB Type-C Rev 2.4, Table 3-5, note 2] · [First-article USB tests](../manufacturing/process.md#first-article-acceptance)

Top copper joins U3 pads 9 and 10 to active shunt pins 2 and 1,
respectively. Pads 9 and 10 have no internal connection. Pin 5 protects
VBUS. Pins 3 and 8 have independent 0.88 mm and 0.73 mm copper paths
to plated ground vias. All four J2 shell slots connect to L2.

| J2 contacts | D+ to active U3 pin 2 | D− to active U3 pin 1 | D+ to U4 pin 3 | D− to U4 pin 4 |
| --- | ---: | ---: | ---: | ---: |
| A6 / A7 | 4.04 mm | 4.04 mm | 11.21 mm | 10.41 mm |
| B6 / B7 | 7.05 mm | 9.03 mm | 14.21 mm | 15.39 mm |

Lengths follow track centrelines and include the two nominal 1.6 mm
barrels on B7. The D+/D− length mismatch at U4 is 0.795 mm from A6/A7
and 1.181 mm from B6/B7. The board regression uses a 1.27 mm limit. The values exclude
connector and package internals. The top pair uses 45° changes of direction
over the L2 ground plane. TI recommends routing USB 2.0 D+/D−
together, controlling differential impedance to 90 Ω and minimizing
branches and changes of layer.
[TI USB 2.0 board guidelines, Table 1](https://www.ti.com/lit/an/swca124/swca124.pdf) ·
[TI high-speed interface layout guidelines, Appendix A](https://www.ti.com/lit/an/spraar7j/spraar7j.pdf)

The L2 Gerber covers the full width of D+ and the D− main trace through
the U4 fanout, apart from the A7 signal via’s own clearance on D−.
L3 ground covers the bottom crossover between its via clearances. Each
signal via has two plated connections between the local L3 ground and L2.
Their centre-to-centre distances are 0.78/0.79 mm at A7 and 0.79/0.86 mm at B7.

| Routed cross-section | PCB sample location in mm | Estimated differential impedance |
| --- | --- | ---: |
| L1 straight pair toward U4, 0.28 mm width / 0.22 mm gap | X = 154.10, 154.50, 154.90 at Y = 63.00 | 89.0–91.0 Ω |
| L1 through U3 and toward J2, same width and gap | X = 157.55, 158.36, 159.14, 159.60 at Y = 63.00 | 89.1–89.5 Ω |
| U3 data lands, including their mask openings | X = 157.9525, 158.7875 at Y = 63.00 | 89.0 Ω |
| L1 approaching the D− junction, before the via move | X = 159.95, 160.12 at Y = 63.00 | 89.2–89.3 Ω |
| U4 diagonal fanout | Normal to the pair at (153.10, 62.23) | 89.5–89.7 Ω |
| U4 pad approach, including the QFN mask openings | Across the pads at (152.40, 61.26) | 89.9–91.1 Ω |

The 2D quasi-static estimates use the routed copper and refilled ground. For the specified JLC04161H-7628 stackup, both outer layers have 0.2104 mm of 7628 prepreg (Dk 4.4) to their reference plane. The JLC China calculation uses 40.64 µm finished outer copper and a trace top 12.70 µm narrower than the base. The solder mask has Dk 3.8 and is 15.24 µm over copper and 25.40 µm over the laminate and between traces. [JLC stackup] · [JLC China calculation parameters](https://www.jlc.com/portal/q7i37381.html)

The model removes solder mask at the openings in the production Gerbers and
assumes air above the bare board. Solder joints and component packages are
outside the model. The ranges span the sampled locations and two treatments
of nearby VBUS and 3.3 V copper, omitted or held at AC ground.
The two contact ties are on different layers. The isolated 0.364 mm D−
trace over L3 models at 45.0 Ω single-ended at Y = 63.16, 63.25 and
63.34 mm with 0.20 mm coplanar ground clearance. The A6–B6 tie leaves
the pads at 0.30 mm and widens to 0.39 mm around the right side. The
middle of that section at (163.145, 62.75) models at 43.9 Ω single-ended
with the adjacent D− land at AC ground. The pads, tees, vias
and shell form a three-dimensional connector launch. Qualify it with the
full-speed waveform in both orientations.
Request production TDR coupons for the L1 90 Ω differential pair and
the L4 45 Ω single-ended crossover, both at ±10%.
[Fabrication requirements](../manufacturing/process.md#bare-board-fabrication)

## JLC China manufacturing review, 26 November 2026

The 70 × 50 × 1.6 mm four-layer board fits JLC China’s published routing,
drilling and slot capabilities. **Hold assembly approval for the upper panel
rail, the USB-area mask and stencil, and the revised silkscreen.** The archived
Gerber ZIP (SHA-256 `7dd88fbe8401e4d78bf56343b62aa45f51de25e63909bcb47cdbd9687da0f5ad`)
matches the PCB identified in the IC audit. A subsequent working-tree edit
changed the legends on both sides. Factory approval and first-article inspection
are pending.

| Check | Result on the current order files |
| --- | --- |
| Copper and vias | Narrowest routed track 0.150 mm, project clearance 0.150 mm, copper edge setback 0.50 mm. The smallest routed via has a 0.30 mm drill and 0.60 mm land. The closest two drill edges are 0.264 mm apart. JLC lists 0.09/0.09 mm track/space for 1 oz multilayer copper and 0.20 mm between via drills. [JLC China fabrication limits](https://www.jlc.com/portal/vtechnology.html) |
| Drills and outline | Closed single-board outline, 243 plated holes including seven slots, and two non-plated locating holes. The narrowest plated slots are J2’s 0.60 × 1.20 mm slots with a 0.20 mm nominal ring. JLC’s multilayer slot minima are 0.35 × 0.70 mm. [JLC China fabrication limits](https://www.jlc.com/portal/vtechnology.html) |
| Assembly files | All 100 top-side placement references match the SMT BOM. All 384 front paste apertures match the PCB. The smallest chip is 0402 imperial and the finest IC pitch is 0.50 mm. Both fit Standard SMT. The proposed 70 × 70 mm panel meets its minimum dimensions. [JLC China SMT capabilities](https://www.jlc-smt.com/vtechnology) |
| Fabrication options | The fill layer, drill file and coordinate list agree on all 44 thermal holes. Quote epoxy fill, planarization and copper caps on both faces at U2 (12), U5 (16) and U6 (16). Confirm the JLC04161H-7628 stack and production impedance coupons for 90 Ω differential on L1 and 45 Ω single-ended on L4, both ±10%. [Fabrication requirements](../manufacturing/process.md#bare-board-fabrication) |

**Panel separation.** JLC China specifies 5 mm from a V-score to a component.
Fourteen nominal SMT body outlines fall inside that band along the upper rail.
U2 is 0.500 mm from the score, L1 is 0.550 mm away and ceramic capacitor C4
is 0.625 mm away. The other eleven are C6, R40, C7, C5, Q3, R29, R7, U11,
C38, R3 and C8. All SMT bodies clear the lower score by at least 5 mm.
Request a routed upper edge with temporary tabs in clear areas and verify
tool access and the finished outline on the revised panel drawing.
[JLC China SMT design rules, V-cut](https://www.jlc.com/portal/q7i64042.html)

**USB solder mask and stencil.** At U4, the mask between adjacent pads is
0.080 mm along each row and 0.057 mm at all four corners. The copper gap
along a row is 0.200 mm. JLC’s published mask table uses copper-pad spacing.
Review the finished mask artwork with CAM and retain Silicon Labs’ 0.060 mm
minimum clearance around the copper. U3 has eight 0.565 × 0.200 mm copper
lands with nominal 1:1 mask openings. TI shows a larger opening in its
preferred land pattern, and JLC’s international table lists a generic
0.25 × 0.25 mm minimum SMD pad. Confirm the narrow lands and their exposed
width with the domestic factory. The U3 stencil aperture area ratio is
0.768 with 0.100 mm foil, 0.640 with 0.120 mm and 0.614 with 0.125 mm.
TI gives 0.66 for laser-cut foil, while Silicon Labs specifies 0.125 mm for
U4. Agree on a local step or qualified print process and check paste deposits
on the first article. The nearest R12 aperture is only 0.511 mm from U3.
[Silicon Labs QFN24, table 7.2](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=40) ·
[TI DQA land and stencil drawings](https://www.ti.com/lit/ds/symlink/tpd4e05u06.pdf#page=29) ·
[TI stencil guidance](https://www.ti.com/lit/an/slua271c/slua271c.pdf#page=11) ·
[JLCPCB international capabilities](https://jlcpcb.com/capabilities/pcb-capabilities)

**Placement and secondary soldering.** The closest passive bodies, C11/C29,
are 0.50 mm apart. U9/U10 are 2.78 mm apart. Both are below the domestic
guide’s respective 1 mm passive and 3 mm IC spacing guidance. C10 and R47
are 0.87 and 0.91 mm from U4, below JLC’s package-specific 1 mm recommendation
for a 0402 next to a QFN. Have assembly engineering check nozzle and rework
access. J2 has paste on its 16 contacts and none on its four plated shell
tabs. Assign all four tabs to the manual through-hole pass or quote secondary
soldering, and inspect their solder fill.
[JLC China SMT design rules](https://www.jlc.com/portal/q7i64042.html) ·
[JLC package spacing table](https://jlcpcb.com/help/article/minimum-spacing-for-smd-components)

**Silkscreen and release files.** The archived build passed KiCad 10.0.8 DRC
and all 52 tests. On the later PCB snapshot (SHA-256
`65827d8d63fd550256c1664499b3f1ded753a179843aab06a32ad1618ed37606`),
fresh Gerber plots matched the archived copper, mask, paste and outline
geometry. Both legend layers changed. A zone-refilled DRC found 39
silkscreen spacing warnings and eight instances of text clipped at exposed
pads, with zero unconnected items or schematic mismatches. For example,
`J2 USB DATA` overlaps C1’s outline, and the `COIL CMD` label crosses
pads on Q6, R33 and R45. The revised snapshot passed 51 of 52 tests.
The remaining test expects the former `SOL` indicator label. Resolve the
legend clearances, align the indicator test with the intended wording, and
regenerate the order package from the reviewed revision.

[USB Type-C Rev 2.4, Table 3-5, note 2]:
  https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/USB-Type_2D00_C-Spec-R2.4-_2D00_-October-2024.pdf
[JLC stackup]: https://jlcpcb.com/impedance
[TMC2209 datasheet]: https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf
[TI USB layout guidance]: https://www.ti.com/lit/an/slla414a/slla414a.pdf

[UMW AO4407A]: https://www.umw-ic.com/static/pdf/5e7bac0574bc94a52e928614220994e9.pdf
