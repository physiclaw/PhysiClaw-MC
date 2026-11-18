# PCW-MC-01 Rev A · Fabrication and first-article instructions

Assembly PCW-MC-01-ASM, revision A. Use the Gerbers, NC drills, electrical test netlist and fill-and-cap table from the same build. Record the package manifest and serial or lot number on the traveler.

## Bare board

| Item | Rev A requirement |
|---|---|
| Construction | 70 × 50 mm, 1.6 mm FR-4, four copper layers. L1/L4 nominal 1 oz, L2/L3 nominal 0.5 oz. L2 is ground. L3 carries power and local ground. |
| Stackup | Supply the laminate code, finished copper and barrel plating, outer dielectric thickness, material and tolerances. Review the USB paths against the proposed 90 Ω differential construction before ordering. The fabrication ZIP omits KiCad's default stackup metadata. |
| Holes | Separate metric PTH and NPTH files, absolute origin and G85 plated slots. Confirm J1's three 1.0 × 1.6 mm finished slots, J2's four 0.60 mm wide shell slots and two 0.65 mm NPTH locating holes, and the eight 1.0 mm finished J3/J4 holes against actual connector samples. Preserve the isolated plated M3 mounting rings. |
| Thermal pads | Resin-fill, planarize and copper-cap the 50 holes in `fabrication/fill-and-cap.csv` on both faces. Counts are U2 × 12, U5 × 16, U6 × 16, U8 × 6. The fill/cap CSV, Gerbers, Excellon and CPL all use millimetres, X right and Y up, in the same absolute coordinate system. |
| Finish and electrical test | Confirm flat finish, mask registration and fine-pitch dams in CAM. Preserve supplied paste and mask geometries. Use the IPC-D-356 netlist for bare-board electrical test. |

## Assembly

Populate 92 front SMT and seven THT references. Use the exact MPN and supplier code, including **F1 Littelfuse 0467005.NRHF (5 A), C151140**. Confirm stock allocation for the order quantity and feeder losses. The SMT BOM and CPL use the JLC China importer. Use the seven-reference THT list for the separate soldering operation.

- **Reflow.** The selected JLC China economy process lists 255 ±5 °C. Obtain a compatible measured component-body profile. U2 calls for one pass at 235–250 °C peak. F1 recommends 245–250 °C. Agree on moisture handling and the actual assembly route before placing the order. [JLC process](https://www.jlc-smt.com/vtechnology) · [Espressif §12.3](https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.html) · [Littelfuse 467](https://www.littelfuse.com/assetdocs/fuse-467-datasheet?assetguid=4a59f034-1cca-460e-a5ba-e1e66247c76d)
- **Stencil.** Use the front paste Gerber with the proposed 0.10 mm foil. Verify U7's 0.55 × 0.20 mm openings and U8's 1.76 × 2.11 mm opening in stencil CAM. Arrange first-article hidden-joint inspection, including U5/U6 voiding and at least 85% actual U8 exposed-pad solder coverage. [TI layout and package drawing](https://www.ti.com/lit/ds/symlink/tps1h200a-q1.pdf)
- **Through-hole work.** Fit J1, J3, J4, J5 and C1/C15/C22. Inspect hole fill at solid plane connections, USB shell anchors and capacitor polarity. Verify insertion, solder fill and retention with the actual parts.

### Placement review at JLC

The CPL uses the physical body centres of the Rev A footprints. J2 uses the centre of its 8.94 × 7.30 mm shell at (166.040, −63.000) mm. U2 uses the centre of its 18.0 × 19.2 mm module at (134.000, −60.100) mm. Both are top-side coordinates in the Gerber frame. The PCB outline runs from (100, −100) to (170, −50) mm. Keep the same origin on all order files. [JLC coordinate fields](https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly) · [EasyEDA centre and origin definitions](https://docs.easyeda.com/en/PCB/Export-Coordinate/index.html)

The part table records the direction between two named pads on each catalog footprint at 0°. The exporter measures the same directed line on the placed PCB, subtracts the catalog direction and wraps the result to 0–360° (360° becomes 0°). Both directions are measured counterclockwise in top view. This applies each correction once. The 39 available footprint records were matched to the local lands by geometry. For the four-contact SW1, the two electrically common lands in each row form one terminal. C859927 is a nonpolar 1206 resistor without an EasyEDA footprint record in this lookup. Its two-terminal long axis is used, with 180° symmetry. [JLCEDA / EasyEDA Official Library](https://lceda.cn/) · [EasyEDA](https://easyeda.com/) · [JLC C859927](https://jlcpcb.com/partdetail/YAGEO-RL1206FR7W0R1L/C859927)

Use the package marks in JLC's preview. A red dot can denote another orientation feature. Compare the actual package, the drawing and the two named pads in `assembly/placement-review.csv`. Save the approved preview for this assembly lot. [JLC placement FAQ](https://jlcpcb.com/help/article/pcb-assembly-faqs-part-2)

| Component | Top-view check |
|---|---|
| U4 CH340C, U5/U6 TMC2209, U7 USB mux, U8 protected switch | Pin 1 matches the first pad in the review CSV. Rev A CPL angles are 0°, 90°/0°, 0° and 90° respectively. |
| D1–D4 and D6–D8 | Align the part's cathode mark with pad 1. Inspect each LED color and diode package in the preview. |
| J2 USB-C | Opening faces +X at the right board edge. The signal contact row sits inboard of the shell centre. Check the two locating holes and all four shell slots. |
| U2 ESP32 | RF connector end faces the top board edge (+Y in Gerber coordinates). Pin 1 is at (125.250, −51.690) mm. Use the 32UE external-antenna module. |
| SW1 RESET | Switch terminals run in two horizontal rows. JLC footprint pins 1/2 form the upper row and 3/4 the lower row in the zero-angle view. Check that RESET opens at rest. |
| C1, C15, C22 | These are THT electrolytics. Install the positive lead at pad 1. Check the polarity band against the negative terminal before soldering. |

## Programming

1. Keep actuator loads disconnected. Attach the external antenna, regulated **12 V / 3 A, 5.5/2.5 mm centre-positive** adapter and a USB-C data cable. USB supplies the data interface only.
2. Extract the verified FluidNC v4.1.1 POSIX archive supplied in `programming/`. From its extracted directory run `sh install-wifi.sh` for the classic ESP32. Leave its serial terminal, then run `sh install-fs.sh` on a new module. Installing the filesystem replaces its contents.
3. Upload the supplied `config.yaml` to the local filesystem, select it with `$Config/Filename=config.yaml`, then restart. Save the 115200-baud boot log. Confirm UART1 reports both TMC2209s at addresses 0 and 1 and startup leaves the actuators disarmed. For manual download, bridge rear TP1 (IO0) to TP2 (GND), press and release RESET, then release the bridge once the installer connects.

## First-article acceptance

| Test | Evidence to record |
|---|---|
| Passive inspection and startup | Check supply resistance, polarity, solder joints and fit before power. Use a current-limited supply initially. Capture V12 at TP10, 3V3 at TP3, ESP_EN at TP9, OE_N at TP12, ENN at TP5 and U8 IN at TP14 with local grounds. Verify inhibition through cold start, slow ramp, brownout, RESET and bootloader entry. |
| Motor and coil wiring | J3/J4 use JST XH, 2.50 mm. Pins 1/2 are winding A and 3/4 are winding B. With the component side up and USB at right, J5 **upper pin 1 = switched positive**, **lower pin 2 = GND**. Verify winding pairs before connecting with power off. |
| Combined load | Confirm motor ratings before using the initial 0.400 A RMS run / 0.150 A hold settings. Record input, Wi-Fi load, motor acceleration/braking and 3.3 V transients. The total steady input target is 2.5 A. D2 is the SMBJ15A on V12. Measure hot-plug and braking peaks and verify actual adapter overload recovery. |
| Solenoid and faults | Rated 12 V / 0.8 A, maximum 10 s on followed by at least 60 s off, operator controlled. After deliberate ARM (`$RM=0`), `M3 S1000` at 100% override requests full duty, `M5` requests off and `$RM=1` disarms. Use a limited-energy fault fixture to check FAULT at TP7, shutoff latency and re-arm. Subsequent PWM edges can restart U8 after per-pulse latch-off. |
| Thermal and communications | Record temperatures to equilibrium at 40 °C still air and 50 °C enclosure air using permitted coil pulses. Check J1, F1, Q1, U1/L1, both drivers and U8/D4. Verify USB enumeration, flashing and streaming in both orientations, USB-only isolation, external antenna performance and cable fit in the enclosure. |

Before batch release, retain the approved factory stackup, placement preview, thermal profile, hidden-joint inspection and first-article measurements with the corresponding manifest. Record firmware/config identity and the agreed functional-test result for each shipped board.
