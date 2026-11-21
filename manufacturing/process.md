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
- **Via clearances.** Allow 0.25 mm from drill edge to other-net copper.
  USB signal vias use 0.30 mm drills, 0.60 mm lands and 0.15 mm nominal
  rings. Drill-to-mask gaps are 0.220 mm at
  both J2 vias, 0.250 mm at U3.1 and 0.227 mm at U3.3.
  [JLC PCB capabilities]
- **Filled and capped vias.** Specify epoxy fill, planarization and copper
  caps on both faces (IPC-4761 Type VII) for the **54** 0.30 mm holes in
  `sk.gbr` and `PHYSICLAW-JLC-fill-and-cap.csv`. The list covers four off-pad
  USB vias (two each at J2 and U3) and 50 thermal holes (U2: 12, U5/U6: 16
  each, U8: 6 including four mask-covered corners). Confirm all locations,
  flush thermal-pad caps and mask coverage of the USB vias in CAM.
  [JLC Gerber preparation] · [JLC via treatment]
- **Finish and mask.** Confirm a flat finish, mask registration and
  fine-pitch dams. Preserve the paste and mask geometry. Put the
  `sk.gbr` treatment and dam requirements in the order remarks.
  [JLC order instructions]

Keep the absolute origin across the Gerber, drill, via-list, and placement
files. Coordinates are in millimetres with X to the right and Y up.

## Assembly

Select **Standard SMT assembly (标准型)** at JLC China. Gerbers and CPL use
single-board coordinates. Confirm tooling rails, fiducials, separation,
connector overhangs and tool clearance on the panel drawing. The board has
a 0.50 mm copper setback. JLC's V-score minimum is 70 × 70 mm.
[JLC panel guidelines]

Upload `dist/PHYSICLAW-JLC-BOM.csv` and
`dist/PHYSICLAW-JLC-CPL-mm.csv` separately. Verify all 94 top-side placements.
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

Check U8's 1.76 × 2.11 mm exposed-pad aperture. On the first article,
inspect the hidden joints, record voiding at U5 and U6, and verify at
least 85% exposed-pad solder coverage at U8.
[TI layout and stencil guidance]

### Placement approval

Compare package marks and pin 1 in the JLC preview with
`build/assembly/top-assembly.pdf` and `build/assembly/placement-review.csv`.
The CSV records two reference pads and the JLC angle after applying the
catalog orientation in `manufacturing/jlc-parts.csv`. Save the approved
preview with the lot.
[JLC placement FAQ]

- **ICs.** Check pin 1 at U4, U5, U6, U7, U8, and U9. The expected CPL angles
  are U4 0°, U5 90°, U6 0°, U7 0°, U8 90°, and U9 90°.
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
- **Solenoid and faults.** Use a 12 V / 0.8 A coil. After deliberate arming
  with `$RM=0`, `M3 S1000` at 100% override requests full
  duty. Use `M5` to switch off and `$RM=1` to disarm. With a limited-energy
  fault fixture, monitor SOL_FAULT_N at TP7 and check current limit, shutoff
  latency, coil decay at 200 Hz and re-arm behaviour. A later PWM edge can
  restart U8 after per-pulse latch-off.
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
  coil. Check J1, F1, Q1, U1/L1, both drivers, and U8/D4. Verify
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
[TI layout and stencil guidance]:
  https://www.ti.com/lit/ds/symlink/tps1h200a-q1.pdf
[JLC placement FAQ]: https://jlcpcb.com/help/article/pcb-assembly-faqs-part-2
[JLC coordinate fields]:
  https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
[FluidNC v4.1.1 release]: https://github.com/bdring/FluidNC/releases/tag/v4.1.1
[FluidNC installation guide]:
  https://github.com/bdring/fluidnc-wiki-content/blob/main/installation.md
