# PCW-MC-01 manufacturing and first-article guide

Hardware v1.0 · Assembly PCW-MC-01-ASM

Factory and bench approval are pending. Use the [order files from one build].

## Bare-board fabrication

Upload `dist/PHYSICLAW-JLC-Gerbers.zip`. Send CAM this guide, the fill-and-cap
CSV and `PHYSICLAW-JLC.d356` from `dist/fabrication/`. Use the D-356 file for
bare-board electrical testing.

- **Construction.** 70 × 50 mm, 1.6 mm, four-layer FR-4. Nominal copper is
  1 oz on L1/L4 and 0.5 oz on L2/L3. L2 is GND. L3 carries power and GND.
- **Stackup.** JLC04161H-7628, 0.2104 mm nominal outer dielectric. Confirm
  laminate, dielectric tolerances, finished copper and barrel plating with
  CAM. Specify **90 Ω differential ±10%** on L1 over L2 GND and L4 over
  L3 GND. Request TDR results for coupons on both layers. Use 0.28 mm
  traces, a 0.18 mm edge gap and production copper, mask and reference
  planes. Preserve the local necks at U3 and the L4 via fanouts. Recheck
  routing for stackup changes.
  [JLC stackups] · [JLC impedance control]
- **Drills and slots.** Use the separate metric PTH/NPTH files and retain G85
  plated slots. J1 has three 1.00 × 2.05 mm slots with PJ-102BH terminal
  centres and 0.275 mm nominal copper at the ends. J2 has two
  0.60 × 1.20 mm slots, two 0.60 × 1.70 mm slots and two 0.65 mm NPTH
  locating holes. J3/J4 each have four 1.0 mm plated holes. Confirm finished
  dimensions with CAM and connector samples. Preserve the isolated plated
  M3 rings.
  [Jack drawing] · [JLC China process limits]
- **Via clearances.** Allow 0.25 mm from drill edge to other-net copper on the
  outer layers and 0.30 mm on the inner layers.
  Tent both faces of the four 0.30 mm USB signal vias beside J2 and U3.
  Their 0.60 mm lands have 0.15 mm nominal rings. Keep the USB via drills clear of the connector and clamp pad openings.
  [JLC PCB capabilities]
- **Filled and capped vias.** Specify epoxy fill, planarization and copper
  caps on both faces (IPC-4761 Type VII) for the **44 thermal holes** marked
  in `sk.gbr` and `PHYSICLAW-JLC-fill-and-cap.csv`. Each uses a 0.32 mm drill
  and a 0.62 mm land. There are 12 at U2, 16 each at U5 and U6.
  Confirm all locations, flush thermal-pad caps and the supplied mask in CAM.
  下单时请仅对 `sk.gbr` 标出的 44 个 Ø0.32 mm 散热孔做环氧树脂塞孔、磨平及双面电镀铜盖帽。
  J2 和 U3 旁的 4 个 Ø0.30 mm USB 信号过孔仅做双面盖油。阻焊按原稿。
  [JLC Gerber preparation] · [JLC via treatment]
- **Finish and mask.** Confirm a flat finish, mask registration and
  fine-pitch dams. Preserve the paste and mask geometry. Put the
  `sk.gbr` treatment and dam requirements in the order remarks.
  [JLC order instructions]

Keep the absolute origin across the Gerber, drill, via-list, and placement
files. Coordinates are in millimetres with X to the right and Y up.

## Assembly

Select **Standard SMT assembly (标准型)** at JLC China. Gerbers and CPL use
single-board coordinates. Supply `dist/PHYSICLAW-JLC-panel.jpg` to CAM as the
proposed 70 × 70 mm assembly panel. Ask CAM to add the two 10 mm rails,
four top-side MARK points and four 2 mm non-plated tooling holes shown in the
drawing. Dimensions are in millimetres. Each MARK has a 1 mm copper diameter
and a 2 mm mask opening. Its centre is 3.85 mm from the outer rail edge, leaving
3.35 mm to the edge of the copper. One MARK and one hole are staggered by 5 mm.
The dashed lines show the proposed V-scores. Before payment, confirm the CAM
panel preview, including V-scores, connector overhangs and tool clearance. The
board has a 0.50 mm copper setback. JLC's V-score minimum is 70 × 70 mm.
[JLC panel guidelines]

Upload `dist/PHYSICLAW-JLC-BOM.csv` and
`dist/PHYSICLAW-JLC-CPL-mm.csv` separately. Verify all 98 top-side placements.
Confirm MPNs, LCSC codes and stock including feeder losses. Fit Littelfuse
`0467005.NRHF` (5 A, LCSC `C151140`) at F1.

### Reflow and stencil

Agree on lead-free reflow and moisture handling with JLC. Measure U2 and F1
body temperatures on the first article and keep the profile with the lot.

- **U2.** Espressif specifies a single reflow pass with a 235–250 °C peak.
  [Espressif reflow profile]
- **F1.** Littelfuse specifies a 245–250 °C lead-free peak in its recommended
  profile. [Littelfuse 467 datasheet]

For U4, Silicon Labs recommends a 0.125 mm stencil. The front paste Gerber has four 0.90 × 0.90 mm centre openings on 1.20 mm pitch and 1:1 perimeter apertures. Confirm the stencil with assembly and inspect the centre joint on the first article. [CP2102N, §7.2](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=39)

Inspect both F1 terminations and the J2 contact row after reflow. Inspect R12,
R13, R26 and R27 for skew or tombstoning. Their ground lands use 0.20 mm
thermal spokes across a 0.25 mm copper gap. [JLC SMT thermal-relief guidance]

Inspect the hidden joints and record exposed-pad voiding at U5 and U6 on the first article.

### Placement approval

Compare package marks and pin 1 in the JLC preview with
`build/assembly/top-assembly.pdf` and `build/assembly/placement-review.csv`.
The CSV records two reference pads and the JLC angle after applying the
catalog orientation in `manufacturing/jlc-parts.csv`. Save the approved
preview with the lot.
[JLC placement FAQ]

- **U1 TPS54302DDCR.** In the board top view, pin 1 is the upper-right land
  at (116.400, −57.000) mm. The C311983 catalog pad axis gives 180° in
  the CPL. Confirm the pin-1 mark in the assembly preview. The six copper
  and paste lands measure 1.10 × 0.60 mm. The 1.20 × 0.70 mm mask openings
  give 0.05 mm clearance per edge and a 0.25 mm mask web between pins.
- **L1 and C2.** The CPL places L1 at 90° and C2 at 270°. From above,
  L1’s two wide terminations run left-to-right and C2’s long body axis
  runs top-to-bottom. Allow 5.0 mm height above the PCB for L1.
- **ICs.** Check U3 pin 1 (common ground, 180° CPL) and the U4 QFN24 pin-1 mark (90° CPL) against the placement review. Check U5 and U6 at 0° and U9 at 90°.

- **Q1 and Q6.** Fit UMW AO4407A (`C2841482`) at both positions. The
  alternate is AOS AO4407A (`C16072`). If using the alternate, select its
  exact code for both positions in the assembly order and record it with
  the lot. Both catalog footprints use the same pin 1 to pin 4 axis.
  Check pin 1 (source) at Q1 (270°) and Q6 (90°) against the assembly
  drawing. Q6 pins 5–8 connect to J5 pin 1.
- **Q7.** Check pin 1 (base) at 270° in the CPL.
- **U4 lands.** Confirm 0.30 × 0.85 mm perimeter lands, the 2.55 mm square ground pad and 0.06 mm solder-mask expansion at U4. [Silicon Labs, table 7.2](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=39)

- **Diodes and LEDs.** Align the cathode with pad 1 on D1–D4 and D6–D9. D4
  uses a 180° CPL rotation, with its cathode facing +X. Check LED colour
  and diode package against the BOM.
- **J2 USB-C.** The 8.94 × 7.30 mm shell is centred at (166.040, −63.000) mm.
  The opening faces +X at the right edge, with the contact row inboard.
  Check both locating holes and all four shell slots.
- **U2 ESP32.** Use the `ESP32-WROOM-32UE-N4` external-antenna module. Its
  18.0 × 19.2 mm body is centred at (134.000, −60.100) mm. Pin 1 is at
  (125.250, −51.690) mm. The antenna connector faces +Y at the top board edge.
- **SW1 RESET.** In the catalog’s zero-angle view, pins 1 and 2 form the upper
  terminal and pins 3 and 4 form the lower terminal. Verify open at rest.
- **C859927 shunt resistors.** Fit 0.100 Ω, 0.5 W at R17–R20 and align the long axis. A 180° rotation is
  electrically equivalent.

The CPL uses physical body centres and counterclockwise angles in top view.
The board outline spans X = 100–170 mm and Y = −100 to −50 mm.
[JLC coordinate fields]

### Through-hole assembly

Fit the seven parts in `build/assembly/tht-bom.csv` in a separate pass.
Check fit and retention at J1, J3, J4 and J5. Seat all three J1 tabs and
square the jack before soldering. Check solder fill at plane-connected
holes and USB shell anchors. Fit C1, C15 and C22 with the positive lead
in pad 1.

## Equipment and accessories

Review fabrication files in a Gerber viewer. For bench testing, use a
current-limited supply, multimeter, oscilloscope with short probe grounds and
USB-C data cable. Arrange X-ray inspection of the exposed-pad joints.

The assembled machine needs an external antenna with a U.FL/MHF-I cable,
two [motor harnesses](#motor-harnesses), a 12 V / 0.8 A solenoid, and the DC
adapter specified below. [Mounting and clearance](../docs/design.md#layout-and-enclosure)

### Motor harnesses

J3 (X) and J4 (Y) use the same four-pin JST XH header (B4B-XH-A, 2.50 mm
pitch) and mate with XHP-4 cable housings. With the component side up, USB-C
on the right, and the motor headers along the near edge, pin 1 is the
rightmost pin on each header. [JST XH datasheet]

Use this map for four-wire bipolar motors with a six-pin JST PH connector
when pins 1 and 4 form one winding and pins 3 and 6 form the other. The PH
cable housing is PHR-6 (2.00 mm pitch). [JST PH datasheet]

| Motor PH pin | PCB XH pin on J3 or J4 | Driver output |
| --- | --- | --- |
| 1 | 1 | OA1 |
| 4 | 2 | OA2 |
| 3 | 3 | OB1 |
| 6 | 4 | OB2 |

Leave PH positions 2 and 5 empty for this pinout. With the harness
disconnected from the board, check the motor windings at the XH plug.
Measure one winding across pins 1–2 and the other across pins 3–4.
Any pair spanning the two windings should read open. With power off, plug
in both harnesses and check continuity from each metal motor case and the
conductive frame to board GND (J1 pin 2). This bond drains belt static.
All four J3/J4 contacts are winding outputs. [TMC2209 datasheet, §3.7](https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf#page=17)

## Programming

Complete the unpowered checks in [First-article acceptance] before power-up.

1. Keep the motors and solenoid disconnected. Attach the external antenna
   and a USB-C data cable. Power J1 with a regulated 12 V / 3 A adapter.
   Including tolerance and ripple, the steady adapter output must stay at or
   below D2’s 13 V standoff. Use a centre-positive barrel plug with a
   5.5 mm outer diameter and a 2.5 mm inner diameter.
2. On macOS or Linux, extract `fluidnc-v4.1.1-posix.zip`. From the extracted
   directory, run `sh install-wifi.sh` for the ESP32. On a new module, close
   FluidTerm and run `sh install-fs.sh` to initialize the filesystem. This
   replaces its contents. [FluidNC v4.1.1 release] · [FluidNC installation guide]
3. Verify the rear `PCW-MC-01` legend and confirm the assembly matches the
   BOM, including the 0.100 Ω shunts at R17–R20. Upload this revision’s
   `firmware/config.yaml`. Set
   `$Config/Filename=config.yaml` and restart. Save the 115200-baud boot log.
   Confirm the log reports `Kinematic system: CoreXY` and both TMC2209s
   pass their UART1 checks at addresses 0 (J3, right motor B) and 1
   (J4, left motor A).

If automatic bootloader entry fails, bridge rear TP1 (IO0) to TP2 (GND),
press and release RESET, and remove the bridge once the installer connects.
Use `build/assembly/probe-points.csv` for fixture coordinates.

## First-article acceptance

- **Startup.** Before power-up, measure input resistance and check polarity,
  joints, and fit. Use a current-limited supply. Capture V12 (TP10), V3V3 (TP3),
  ESP_EN (TP9), ACT_OE_N (TP12), DRIVERS_DISABLE (TP5), and SOL_ENABLE (TP14)
  against local ground. Verify the actuators stay off during cold start,
  a slow supply ramp, brownout, RESET, and bootloader entry.
- **3.3 V buck.** At 12 V input, probe across C2 and simultaneously
  measure TP3 against TP4 using short probe grounds. Capture cold start,
  a logic-rail load step up to 0.60 A total and back down, and simultaneous
  stepping, Wi-Fi and solenoid switching. Record input peaks, rail ripple,
  overshoot, settling and U1/L1 temperatures at thermal equilibrium. After
  warm-up, repeat power cycling and the load steps. Probe C33 at U11 VDD
  (pin 3) and U11 RESET (pin 2) together. Verify VDD exceeds 3.189 V
  continuously through the reset delay, RESET releases once and ESP_EN
  stays high through Wi-Fi transmission and dual-axis load changes. Probe
  U4 pins 5, 6 and 7 against local ground during USB traffic. Include ripple and transient excursions in the 3.0–3.6 V acceptance range. Verify enumeration and sustained serial traffic through the load steps. [Silicon Labs, table 3.1](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=10)

  With actuators disconnected, use a current-limited bench supply
  and a controlled output short. Verify recovery without a power cycle at
  room temperature and after warm-up.
- **Motor and solenoid wiring.** Verify both winding pairs as described in
  [Motor harnesses](#motor-harnesses). With the component side up and USB at
  right, J5's upper pin 1 is switched positive and lower pin 2 is ground.
  Connect with power off.
- **Motor driver supplies.** Fit C17 and C24 as 4.7 µF, 25 V, X7R, 0805
  (C98195). For a substitution, review the manufacturer's DC-bias curve
  at 5.0–5.25 V. Probe directly across each capacitor during startup and
  simultaneous acceleration with the solenoid switching. Using the production
  adapter and harness, capture the lowest VS and VCC_IO at each driver
  during motion. Require VS to stay above 4.75 V and VCC_IO (C16/C23)
  within the board's 3.1–3.6 V range. Record the 5VOUT level and ripple
  and check for dips or sustained oscillation. The datasheet's 4.80–5.25 V
  range applies at 24 V supply, 25 °C junction temperature and zero external
  5VOUT load.
  [TMC2209 datasheet, §20.2]
- **Power-cycle operation and motor current.** With the motors connected and
  solenoid disconnected, cycle 12 V. Verify TP12 (ACT_OE_N) starts high and
  goes low automatically after normal boot. TP5 (DRIVERS_DISABLE) must stay
  high and J5 off until commanded. Run the [four CoreXY jogs](../firmware/README.md#first-jogs)
  to verify the belt assignments, toolhead direction and travel scale. Turn J5 on with
  `M3 S1000`, cycle 12 V again, and verify J5 stays off until a new command.
  Use the supplied [0.800 A RMS setting](../firmware/README.md#motor-current-and-outputs)
  for both motors. Verify the intended motors support the configured phase current.
  Use a pure X or Y move to keep both motors stepping at steady low speed.
  Probe one winding of each motor. Measure
  RMS over complete electrical cycles and capture sine peaks. Compare each
  motor with the nominal 0.7955 A RMS and 1.125 A peak for this setting,
  allowing for driver, shunt and probe tolerances. Check both motors against
  the motor's ratings. Verify the 500 ms idle disable.
- **Combined load.** Run the actual payload through repeated loaded moves
  and reversals at the specified top speed and acceleration with both motors
  stepping, Wi-Fi active, and the solenoid at its highest rated duty. Include
  slow continuous stepping for driver heating. Verify repeatable return
  to a physical reference and sufficient torque throughout the speed range.
  Log J1 input current and the 3.3 V rail. Require steady input at or below
  2.5 A and peak demand within the production adapter's specification.
  Verify adapter overload recovery.
- **12 V transients.** Use the production adapter and longest supported power
  lead. Capture plug-in at J1 with the adapter already live, hot restart and
  worst-case dual-axis braking. Repeat cold and after warm-up. Probe directly
  across C2 and at both VS pins (22 and 28) of each driver, using the adjacent
  bypass capacitor and a short ground spring. Record peak voltage and the
  fastest resolved rising slope at each VS pin, including ringing. Require
  less than 1 V/µs and less than 29 V at each VS pin, and less than 25 V at
  C2 including measurement uncertainty. Record headroom and investigate any C2 peak above
  the 22.5 V board qualification target before release. With the Littelfuse
  SMBJ13A, the specified clamp at the TVS is 21.5 V at 28 A (10/1000 µs,
  25 °C). [TMC2209 datasheet, §3.1](https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf)
- **Solenoid PWM.** Use the intended harness, rated 12 V / 0.8 A coil and a
  current-limited supply. Verify J5 and blue SOL (D9) stay off at
  power-up and during reset. Compare D9 with the voltage across J5 at
  zero and full duty. Repeat with the coil unplugged. Yellow SOL CMD (D6)
  follows the command before the interlock.
  At 100% spindle override, capture J5 voltage and coil current at
  `M3 S10`, `M3 S500`, `M3 S990` and `M3 S1000`. Verify a 1.00 ms PWM
  period (1 kHz) at S500. Compare the commanded 10 µs on-interval at S10
  and off-interval at S990 with the measured intervals at J5. Record the
  usable duty range and verify it covers the intended operating range.
- **Q6 voltage stress.** Probe differentially at the package with short leads.
  Use pin 3 as the source reference for gate pin 4 and drain pin 5. Expect
  about 0 V gate-to-source when off and −8.1 V at full duty with 12 V applied.
  Capture the most negative drain-to-source voltage and both gate-to-source
  peaks during coil turn-off, adapter hot-plug and motor braking with the coil
  connected. Record headroom to the UMW absolute limits of −30 V and ±25 V,
  respectively. Verify current decay and mechanical release after `M5` and
  `$RM=1`, and check Q6, Q7 and D4 temperatures under load. [UMW AO4407A][Q6 datasheet]
  J5 has no branch short-circuit trip or GPIO fault indication.
- **USB.** With USB alone, verify that the 3.3 V rail stays off and the host
  detects no USB device. Apply 12 V and verify enumeration, flashing, and
  streaming in both plug orientations with A-to-C and C-to-C data cables.
  Capture full-speed D+ and D− at the connector with a USB 2.0 fixture and
  check the applicable device transmit waveform limits in each orientation.
  Repeat the functional checks after cycling 12 V with USB connected,
  during motor and solenoid operation, and after the assembled enclosure's
  ESD test.
  Program the CP2102N self-powered configuration and set Max Power for the actual VBUS draw. Read back the USB configuration descriptor after a power cycle. With J1 still powered, transfer the enumerated board to the back-voltage fixture and record VBUS, D+ and D− (each ≤0.4 V). Then reconnect and check automatic download using DTR/RTS. [CP2102N, §4.5](https://www.silabs.com/documents/public/data-sheets/cp2102n-datasheet.pdf#page=26) · [USB-IF Appendix F](https://www.usb.org/sites/default/files/USB-IFTestProc1_3.pdf)
- **Thermal and communications.** Run both axes at the qualified current to
  thermal equilibrium at 40 °C in still air and at 50 °C enclosure air
  temperature. Check J1, F1, Q1, U1/L1, U5/U6, R17–R20, J3/J4, the motor
  plugs and Q6/D4 during the combined-load test. Log both drivers' OTPW/OT
  flags throughout the test and require both to stay clear. Check the shunt
  loads against the manufacturer's temperature derating curve and motor
  winding temperatures against the motor rating. Qualify continuous
  dual-axis operation only at the load and ambient that pass. Verify
  external antenna performance and cable fit.

Before batch release, file the approved stackup, placement preview, thermal
profile, hidden-joint inspection, and bench results with `build/manifest.json`.
For each shipped board, record the firmware version, configuration revision,
and functional test result with the [board and source identifiers](../CONTRIBUTING.md#release-a-hardware-revision).

[First-article acceptance]: #first-article-acceptance
[Q6 datasheet]: https://www.umw-ic.com/static/pdf/5e7bac0574bc94a52e928614220994e9.pdf
[JST XH datasheet]: https://www.jst-mfg.com/product/pdf/eng/eXH.pdf
[JST PH datasheet]: https://www.jst-mfg.com/product/pdf/eng/ePH.pdf
[JLC stackups]: https://jlcpcb.com/impedance
[JLC PCB capabilities]: https://jlcpcb.com/capabilities/pcb-capabilities
[JLC impedance control]: https://jlcpcb.com/blog/impedance-controlled-routing
[JLC China process limits]: https://www.jlc.com/portal/vtechnology.html
[JLC order instructions]: https://jlcpcb.com/help/article/instructions-for-ordering
[JLC SMT component spacing]: https://jlcpcb.com/help/article/minimum-spacing-for-smd-components
[Jack drawing]: https://jp.sameskydevices.com/product/resource/pj-102bh.pdf
[JLC via treatment]: https://www.jlc.com/portal/q7i38630.html
[JLC SMT thermal-relief guidance]: https://www.jlc-smt.com/technology/detail/62751.html
[TI stencil area-ratio guidance]: https://www.ti.com/lit/an/slua271c/slua271c.pdf
[TMC2209 datasheet, §20.2]:
  https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf
[JLC Gerber preparation]: https://jlcpcb.com/help/article/gerber-files-preparation
[order files from one build]: ../README.md#generate-the-manufacturing-files
[JLC panel guidelines]: https://www.jlc.com/portal/server_guide_51514.html
[Espressif reflow profile]:
  https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.html
[Littelfuse 467 datasheet]:
  https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d
[JLC placement FAQ]: https://jlcpcb.com/help/article/pcb-assembly-faqs-part-2
[JLC coordinate fields]:
  https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
[FluidNC v4.1.1 release]: https://github.com/bdring/FluidNC/releases/tag/v4.1.1
[FluidNC installation guide]:
  https://github.com/bdring/fluidnc-wiki-content/blob/main/installation.md
