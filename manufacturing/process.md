# PCW-MC-01 manufacturing and first-article guide

Hardware v1.0 · Assembly PCW-MC-01-ASM

Factory acceptance and bench qualification are pending. Use the
[order files from one build]. All paths start at the repository root.

## Bare-board fabrication

Upload `dist/PHYSICLAW-JLC-Gerbers.zip`. Send CAM this guide and both files
in `dist/fabrication/`. The `PHYSICLAW-JLC-fill-and-cap.csv` file lists the
holes that need filling and capping. Use `PHYSICLAW-JLC.d356` for bare-board
electrical testing.

- **Construction.** 70 × 50 mm, 1.6 mm FR-4, four layers. Nominal copper weight
  is 1 oz on L1 and L4 and 0.5 oz on L2 and L3. L2 is ground. L3 carries power
  and local ground.
- **Stackup.** Use JLC04161H-7628 with 0.2104 mm nominal outer dielectric.
  Confirm the laminate, finished copper and barrel plating thicknesses, and
  dielectric tolerances with CAM. Check the 90 Ω differential L1 pair over L2 at 0.28 mm
  width / 0.18 mm edge gap and the L4 crossover's L3 ground and stitching.
  Recheck the routing if the stackup changes. Request a TDR coupon report
  when ordering impedance control. [JLC stackups]
- **Drills and slots.** Use the separate plated (PTH) and non-plated (NPTH)
  metric drill files and retain the G85 plated slots. The drill files specify
  three 1.0 × 1.6 mm slots at J1. J2 has two 0.60 × 1.20 mm slots, two
  0.60 × 1.70 mm slots, and two 0.65 mm non-plated locating holes. J3 and J4
  each have four 1.0 mm plated holes. Confirm finished dimensions against
  connector samples. Preserve the isolated plated M3 mounting rings.
- **Via clearances.** The smallest plated round drill is 0.30 mm. The four
  J2 data vias use 0.40 mm lands, giving a nominal 0.05 mm annular ring.
  Verify drill registration and clearance to the J2 solder lands in CAM.
  The general hole-to-copper DRC minimum is 0.25 mm, with a 0.21 mm
  exception from a J2 data via hole to copper on the opposite data net.
  JLC lists a 0.20 mm minimum from a via hole to a trace. [JLC PCB capabilities]
- **Filled and capped vias.** Resin-fill and planarize the 50 thermal vias
  identified by coordinate in `PHYSICLAW-JLC-fill-and-cap.csv`, then copper-cap
  both faces. The 0.30 mm drills are distributed across U2 (12), U5 (16),
  U6 (16), and U8 (6).
- **Finish and mask.** Confirm a flat finish, solder-mask registration, and
  fine-pitch mask dams in CAM. Preserve the supplied paste and mask geometry.

Keep the absolute origin across the Gerber, drill, via-list, and placement
files. Coordinates are in millimetres with X to the right and Y up.

## Assembly

Select **Standard SMT assembly (标准型)** at JLC China. The supplied Gerbers
and CPL use single-board coordinates. For the 70 × 50 mm board, confirm a
panel layout with JLC that meets the 70 × 70 mm minimum assembly size and
includes tooling rails and fiducials. [JLC panel guidelines]

Upload `dist/PHYSICLAW-JLC-BOM.csv` and
`dist/PHYSICLAW-JLC-CPL-mm.csv` separately. Verify all 92 top-side placements.
Confirm MPNs, LCSC codes, and stock including feeder losses. Fit Littelfuse `0467005.NRHF` (5 A, LCSC
`C151140`) at F1.

### Reflow and stencil

Agree on the lead-free reflow profile and moisture handling with JLC before
ordering. Verify the temperatures at the U2 and F1 package bodies on the
first article and retain the measured profile with the lot records.

- **U2.** Espressif specifies a single reflow pass with a 235–250 °C peak.
  [Espressif reflow profile]
- **F1.** Littelfuse specifies a 245–250 °C lead-free peak in its recommended
  profile. [Littelfuse 467 datasheet]

Use the front paste Gerber with the proposed 0.10 mm stencil. Check the
0.55 × 0.20 mm apertures at U7 and the 1.76 × 2.11 mm exposed-pad aperture at U8.
Inspect hidden joints on the first article. Record voiding at U5 and U6 and
verify at least 85% exposed-pad solder coverage at U8.
[TI layout and stencil guidance]

### Placement approval

Check package marks in JLC’s preview against `build/assembly/top-assembly.pdf`
and `build/assembly/placement-review.csv`. Verify pin 1 from the package
marking. The CSV records two reference pads and the final JLC angle after any
correction in `manufacturing/jlc-parts.csv`. Save the approved preview for the
lot. [JLC placement FAQ]

- **ICs.** Check pin 1 at U4, U5, U6, U7, U8, and U9. The expected CPL angles
  are U4 0°, U5 90°, U6 0°, U7 0°, U8 90°, and U9 180°.
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

Fit the seven references in `build/assembly/tht-bom.csv` in a separate pass.
Check fit and retention at J1, J3, J4, and J5. Check solder fill at
plane-connected holes and USB shell anchors. Verify polarity and fit C1, C15,
and C22 with the positive lead in pad 1.

## Equipment and accessories

Use a Gerber viewer for fabrication review. For bench testing, have a
current-limited supply, a multimeter, an oscilloscope with short probe
grounds, and a USB-C data cable. Arrange X-ray inspection of the exposed-pad
solder joints with the assembler.

The assembled machine needs an external antenna with a U.FL/MHF-I cable,
two JST XH motor harnesses, a 12 V / 0.8 A solenoid, and the DC adapter
specified below. [Mounting and clearance](../docs/design.md#layout-and-enclosure)

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

## First-article acceptance

- **Startup.** Before power-up, measure input resistance and check polarity,
  joints, and fit. Use a current-limited supply. Capture V12 (TP10), V3V3 (TP3),
  ESP_EN (TP9), ACT_OE_N (TP12), DRIVERS_DISABLE (TP5), and SOL_ENABLE (TP14)
  against local ground. Verify the actuators stay inhibited during cold start,
  a slow supply ramp, brownout, RESET, and bootloader entry.
- **Motor and coil wiring.** J3 and J4 are JST XH, 2.50 mm. Pins 1 and 2
  connect to winding A, and pins 3 and 4 to winding B. With the component
  side up and USB at right, J5's upper pin 1 is switched positive and
  lower pin 2 is ground. Verify winding pairs and connect with power off.
- **Combined load.** Confirm motor ratings before using 0.400 A RMS run and
  0.150 A hold. Record input current, Wi-Fi activity, acceleration, braking,
  and 3.3 V transients. The steady input target is 2.5 A. With the SMBJ15A at D2
  on V12, measure hot-plug and braking peaks and verify adapter overload recovery.
- **Solenoid and faults.** Use a 12 V / 0.8 A coil. After deliberate arming
  with `$RM=0`, `M3 S1000` at 100% override requests full
  duty. Use `M5` to switch off and `$RM=1` to disarm. With a limited-energy
  fault fixture, monitor SOL_FAULT_N at TP7 and verify shutoff latency and
  re-arm behaviour. A later PWM edge can restart U8 after per-pulse latch-off.
- **USB.** With USB alone, verify that the 3.3 V rail stays off and the host
  detects no USB device. Apply 12 V and verify enumeration, flashing, and
  streaming in both plug orientations with A-to-C and C-to-C data cables.
  Repeat after cycling 12 V with USB connected and during normal motor and
  solenoid operation.
- **Thermal and communications.** Record steady-state temperatures at 40 °C
  in still air and at 50 °C enclosure air temperature while pulsing the
  coil. Check J1, F1, Q1, U1/L1, both drivers, and U8/D4. Verify
  external antenna performance and cable fit.

Before batch release, file the approved stackup, placement preview, thermal
profile, hidden-joint inspection, and bench results with `build/manifest.json`.
For each shipped board, record the firmware version, configuration revision,
and functional test result with the [board and source identifiers](../CONTRIBUTING.md#release-a-hardware-revision).

[First-article acceptance]: #first-article-acceptance
[JLC stackups]: https://jlcpcb.com/impedance
[JLC PCB capabilities]: https://jlcpcb.com/capabilities/Capabilities?type=1
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
