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
  planes. Keep the 0.26 mm U7 entry and 0.34–0.38 mm L4 fanouts. Recheck
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
  Their 0.60 mm lands have 0.15 mm nominal rings. Drill-to-mask gaps are
  0.220 mm at both J2 vias, 0.250 mm at U3.1 and 0.227 mm at U3.3.
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
`dist/PHYSICLAW-JLC-CPL-mm.csv` separately. Verify all 96 top-side placements.
Confirm MPNs, LCSC codes and stock including feeder losses. Fit Littelfuse
`0467005.NRHF` (5 A, LCSC `C151140`) at F1.

### Reflow and stencil

Agree on lead-free reflow and moisture handling with JLC. Measure U2 and F1
body temperatures on the first article and keep the profile with the lot.

- **U2.** Espressif specifies a single reflow pass with a 235–250 °C peak.
  [Espressif reflow profile]
- **F1.** Littelfuse specifies a 245–250 °C lead-free peak in its recommended
  profile. [Littelfuse 467 datasheet]

Use the front paste Gerber and 0.10 mm foil at U7. The four
0.55 × 0.20 mm rounded apertures have area ratios of 0.763 on 0.10 mm foil
and 0.636 on 0.12 mm foil. Review paste transfer with JLC for foil or
aperture changes. [TI stencil area-ratio guidance]

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
- **ICs.** Check pin 1 at U4, U5, U6, U7, and U9. The expected CPL angles
  are U4 0°, U5 0°, U6 0°, U7 0°, and U9 90°.
- **Q1 and Q6.** Fit UMW AO4407A (`C2841482`) at both positions. The
  alternate is AOS AO4407A (`C16072`). If using the alternate, select its
  exact code for both positions in the assembly order and record it with
  the lot. Both catalog footprints use the same pin 1 to pin 4 axis.
  Check pin 1 (source) at Q1 (270°) and Q6 (90°) against the assembly
  drawing. Q6 pins 5–8 connect to J5 pin 1.
- **Q7.** Check pin 1 (base) at 270° in the CPL.
- **U7 lands.** Confirm the four 0.20 × 0.55 mm copper lands on pins 2, 3,
  7 and 8 with JLC CAM and assembly. TI specifies this land pattern, and the
  smaller dimension is below JLC’s generic SMD-pad guideline.
  [TI RSE0010A land pattern](https://www.ti.com/lit/ds/symlink/ts3usb221a.pdf) · [JLC PCB capabilities]
- **U7 termination resistors.** Confirm the 0.96 mm nominal body gap to
  R41/R42 with JLC. The QFN-to-0402 recommendation is 1.00 mm.
  [JLC SMT component spacing]
- **Diodes and LEDs.** Align the cathode with pad 1 on D1–D4 and D6–D8. D4
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
- **C859927 shunt resistors.** Align the long axis. A 180° rotation is
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
Any pair spanning the two windings should read open. Plug in both
harnesses with board power off.

## Programming

Complete the unpowered checks in [First-article acceptance] before power-up.

1. Keep the motors and solenoid disconnected. Attach the external antenna
   and a USB-C data cable. Power J1 with a regulated 12 V / 3 A adapter.
   Use a centre-positive barrel plug with a 5.5 mm outer diameter and a
   2.5 mm inner diameter.
2. On macOS or Linux, extract `fluidnc-v4.1.1-posix.zip`. From the extracted
   directory, run `sh install-wifi.sh` for the ESP32. On a new module, close
   FluidTerm and run `sh install-fs.sh` to initialize the filesystem. This
   replaces its contents. [FluidNC v4.1.1 release] · [FluidNC installation guide]
3. Upload this revision’s `firmware/config.yaml` to the board. Set
   `$Config/Filename=config.yaml` and restart. Save the 115200-baud boot log.
   Verify both TMC2209s respond on UART1 at addresses 0 and 1 and the actuators
   remain disarmed at startup.

If automatic bootloader entry fails, bridge rear TP1 (IO0) to TP2 (GND),
press and release RESET, and remove the bridge once the installer connects.
Use `build/assembly/probe-points.csv` for fixture coordinates.

## First-article acceptance

- **Startup.** Before power-up, measure input resistance and check polarity,
  joints, and fit. Use a current-limited supply. Capture V12 (TP10), V3V3 (TP3),
  ESP_EN (TP9), ACT_OE_N (TP12), DRIVERS_DISABLE (TP5), and SOL_ENABLE (TP14)
  against local ground. Verify the actuators stay inhibited during cold start,
  a slow supply ramp, brownout, RESET, and bootloader entry.
- **3.3 V buck.** At 12 V input, probe across C2 and simultaneously
  measure TP3 against TP4 using short probe grounds. Capture cold start,
  a logic-rail load step up to 0.60 A total and back down, and simultaneous
  stepping, Wi-Fi and solenoid switching. Record input peaks, rail ripple,
  overshoot, settling and U1/L1 temperatures at thermal equilibrium. After
  startup, verify V3V3 stays within 3.0–3.6 V and ESP_EN remains released
  during the load changes. Check that input peaks stay below C2’s 25 V
  rating. With actuators disconnected, use a current-limited bench supply
  and a controlled output short. Verify recovery without a power cycle at
  room temperature and after warm-up.
- **Motor and solenoid wiring.** Verify both winding pairs as described in
  [Motor harnesses](#motor-harnesses). With the component side up and USB at
  right, J5's upper pin 1 is switched positive and lower pin 2 is ground.
  Connect with power off.
- **Motor driver supplies.** Fit C17 and C24 as 4.7 µF, 25 V, X7R, 0805
  (C98195). For a substitution, review the manufacturer's DC-bias curve
  at 5.0–5.25 V. Probe directly across each capacitor during startup and
  simultaneous stepping. Record the DC level and ripple, and check for
  sustained oscillation. The datasheet's 4.80–5.25 V range applies at
  24 V supply, 25 °C junction temperature and zero external 5VOUT load.
  [TMC2209 datasheet, §20.2]
- **Combined load.** Confirm motor ratings before using 0.400 A RMS run
  and 0.150 A hold. Record winding and input current and 3.3 V transients
  during simultaneous stepping, Wi-Fi, acceleration and braking. The steady
  input target is 2.5 A. With the SMBJ15A at D2 on V12, measure hot-plug and
  braking peaks and verify adapter overload recovery.
- **Solenoid.** Use the rated 12 V / 0.8 A coil and a current-limited supply.
  Check J5 stays off at power-up and during reset. Arm with `$RM=0` and
  measure Q6 gate-to-source voltage, J5 voltage and coil current at 200 Hz
  with `M3 S10`, `M3 S500` and `M3 S1000` at 100% override. At full
  duty expect roughly −8 V gate-to-source. Verify flyback decay and release
  after `M5` and `$RM=1`. Check Q6, Q7 and D4 temperature under load.
  J5 has no branch short-circuit trip or GPIO fault indication.
- **USB.** With USB alone, verify that the 3.3 V rail stays off and the host
  detects no USB device. Apply 12 V and verify enumeration, flashing, and
  streaming in both plug orientations with A-to-C and C-to-C data cables.
  Capture full-speed D+ and D− at the connector with a USB 2.0 fixture and
  check the applicable device transmit waveform limits in each orientation.
  Repeat the functional checks after cycling 12 V with USB connected,
  during motor and solenoid operation, and after the assembled enclosure's
  ESD test.
- **Thermal and communications.** Record steady-state temperatures at 40 °C
  in still air and at 50 °C enclosure air temperature while pulsing the
  coil. Check J1, F1, Q1, U1/L1, both drivers, and Q6/D4. Verify
  external antenna performance and cable fit.

Before batch release, file the approved stackup, placement preview, thermal
profile, hidden-joint inspection, and bench results with `build/manifest.json`.
For each shipped board, record the firmware version, configuration revision,
and functional test result with the [board and source identifiers](../CONTRIBUTING.md#release-a-hardware-revision).

[First-article acceptance]: #first-article-acceptance
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
