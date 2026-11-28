# Changelog

## Unreleased

- Bring R29 beside the USB bridge. The two top-layer traces from J2 through
  R29 to the VBUS sense pin total 6.88 mm, down from 19.64 mm. Run ALARM on
  one diagonal through R27, take both interlock inputs into U10 on parallel
  diagonals, and straighten the rear BOOT crossover over its ground return.
  Align the Y direction via with the driver input.

- Move U11 and R40 beside the reset switch SW1. Align U11 pin 2 and both
  R40 pads with the landing on SW1. The top-layer reset branch now runs
  straight for 3.08 mm of copper, down from 15.76 mm. Move the PWR LED and its
  resistor west to make room and keep C33 beside U11's supply pin.

- Straighten the U1 and C29 ground returns and the ESP32 UART RX escape.
  Run the Q6 drain branch horizontally to D4 and take the motor-disable
  line from U9 to the shared driver trace in one turn. Connect U9 pin 3
  straight to its ground via. Align the Y_B2 via with J4 pin 4 for a
  straight bottom-layer run.

- Rotate U3 and route the J2 data pair through its clamp pads to U4 on L1.
  Tie A6 to B6 on the right with 3.01 mm of top copper. Branch the A7 via
  off the straight 0.28 mm D− trace to keep its drill clear of the pair.
  The A7–B7 tie uses 1.49 mm of bottom copper and measures 4.15 mm
  in-plane and 7.35 mm with barrels.
  Two ground stitches connect L2 and L3 within 0.91 mm of each signal via.
  Give the U4 VIO bypass its own ground via.

- Remove 18 bends across the nine PCB areas. Align TP10 with the input
  TVS, R29 with the USB VBUS feed, and R37 with U9 pin 2. Straighten the
  buck feedback return, ESP32 boot escape, both status LED feeds, motor
  bypass returns, and the solenoid flyback and pull-down returns.

- Correct seven off-angle top-layer traces in the USB and reset circuits.
  Check all routed layers for horizontal, vertical and 45° segments.

- Split the actuator buffer into two SN74LVC1G125DBVR devices (C23654).
  U9 gates motor disable and U12 gates solenoid PWM. Both enables share
  ACT_OE_N and each device has its own 100 nF bypass capacitor. Route
  the motor command through R37 directly into U9 beside the ESP32.
  Orient U12 like U9. Put the command LED branch beside GPIO32 and run
  PWM straight from that branch to U12, with the R38 pull-down at the
  input. U12 drives R21 over 1.65 mm of top copper. R21, TP14 and the
  Q7 base line up. Rotate U10 to match both buffers and exchange its
  two NAND inputs. The enable runs straight from U10 through TP12 to
  U12, with R36 on the trace from U10 to U9.

- Replace the CH340C and USB data switch with a self-powered CP2102N-A02
  and TI TPD4E05U06DQAR ground clamps on D−, D+ and VBUS. Move U3 and
  U4 north by 0.40 mm to align the connector and clamp data pads. Route
  the bottom D− crossover straight between its vias and the top
  pair horizontally through U3. Route J2 VBUS between the R12 pads to
  the U3/C12 branch and connect U4 directly to reset pull-up R47.
  Route the UART on L4 and the DTR/RTS branches on L1. Place
  the IDLE and ALARM LEDs below the bridge with top-layer GPIO feeds. Group
  the three 4.7 µF bridge capacitors on parallel L1 power and ground traces.

- Route Y STEP and DIR with one turn each on the bottom, and take X_A2
  directly off its via toward J3.

- Straighten the reset-supervisor branch through TP9, the USB bridge reset
  controls, the buck bootstrap branch and the solenoid drain bus on L1.
  Give X STEP and DIR one bend each on L4 and carry STEP diagonally through
  R31. Align the Y driver's charge-pump capacitors below U6.

- Enable CoreXY in the PCW-MC-01 FluidNC profile. J3 (X MOTOR) drives right motor B
  and J4 (Y MOTOR) drives left motor A. Set gantry travel to 110 × 200 mm,
  maximum speed to 10000 mm/min and acceleration to 1000 mm/s² on both axes.
- Set the solenoid PWM frequency to 1 kHz.
- Set both axes to 0.800 A RMS in stock FluidNC with 0.100 Ω motor shunts
  and specify a regulated 12 V / 3 A adapter.
- Accept normal motion and solenoid commands after a power cycle. Both
  outputs stay off until commanded.
- Increase buck startup margin with 102 kΩ at R43. Fit a 13 V standoff
  Littelfuse SMBJ13A at D2 and qualify C2 peaks and both drivers’ supply
  slopes with the production adapter.

- Add a blue output indicator across the J5 solenoid terminals. A single
  bend feeds R46 from pin 1. D9 returns directly to pin 2, with SOL
  printed above the LED. The yellow SOL CMD indicator shows the command.
- Center the front crab and PHYSICLAW wordmark between the motor drivers.
- Move the rear crab to the former board ID position and center PHYSICLAW
  and PCW-MC-01 beneath it.
- Straighten the Q7 base and collector routes on the top layer. TP14
  sits at the base branch between R21 and R22. R45 and R33 share a
  straight gate trace to Q6.
- Use UMW AO4407A (C2841482) as the primary part at Q1 and Q6, with
  AOS AO4407A (C16072) as the pin-compatible alternate.
- Drive the 12 V solenoid with an AO4407A and MMBT3904. Retain hardware
  inhibit, PWM and flyback at J5. The discrete output has no branch current
  limit or fault feedback. Retire the fault probe TP7 and use the matching
  FluidNC configuration.

- Reserve the 0.32 mm drill for the 44 filled and capped thermal holes at
  U2, U5 and U6. Use 0.62 mm lands for a 0.15 mm annular ring.
  Tent both faces of the two 0.30 mm D− vias beside J2.
- Increase inner-layer hole clearance to 0.30 mm and open the same-net
  gaps at the VBUS-detect and interlock-enable branches.

- Route the two VBUS branches from U3 pin 5 as a symmetric 0.30 mm
  pair of traces before they turn toward J2.
- Place the CC1 pull-down beside J2 and shorten its route from 8.79 to
  3.34 mm. Align the driver-disable pull-up with the command trace and
  feed it from C32, removing one 3.3 V via.
- Straighten the ESP32 and motor UART receive traces, the L4 Y STEP
  route and the 12 V feed between the solenoid bypass capacitors.
- Move C4 to the feedback-pin side of the inductor and route its sense
  connection to U1 entirely on L1, removing both feedback vias.
- Give J2 and U3 a dedicated L3 ground pour tied to L2 through six
  local ground vias. The 3.3 V plane fills the former ground bridge
  between USB and the eastern controls.
- Widen the L3 3.3 V connection above the indicators from 0.49 to
  4.04 mm. Bring IDLE and ALARM up to L1 beside R27 and move the LED
  ground stitch beside D8.
- Bring 3.3 V directly to U6 on a rounded L3 plane branch and remove
  13.96 mm of L4 trace and two supply vias. Reshape the L3 ground and supply boundaries
  around the remaining USB, control and motor routes.
- Align the motor UART crossing with U5 pin 14 and bring the 3.3 V plane
  feed directly between C16 and U5 pin 15. Shorten the X A2 and Y B2
  winding routes while keeping the connector pin order.
- Bring Y STEP through R32 on its approach to U6.
- Turn the reverse-polarity clamp D1 so both ends connect directly to Q1
  on L1. Shorten the motor UART branch from R11 to U6 from 20.6 to
  17.6 mm and bring the 3.3 V feed onto the C23 bypass trace.
- Route the DTR and RTS branches to both auto-reset transistors on L1.
  Place R6 between the bridge and Q4 and feed C11 beside U4 pin 4.
- Route X STEP and DIR out of the ESP32 toward U5. Put R31 on the
  straight STEP trace to the driver and move its ground return alongside.
- Route both USB-C VBUS contact groups to U3 on L1, remove two VBUS vias
  and shorten CC2 from 8.0 mm to 2.1 mm.
- Match the X motor shunt traces at each width and give the power LED
  its own 3.3 V plane feed beside the buck feedback circuit.

- Move U10 below the ESP32 and U11 beside the reset circuit. Route
  ACTUATOR_ARM, ESP_EN and SOL_CMD entirely on L1, removing six signal
  vias and 35.3 mm of L4 trace. Bring the motor-disable pull-up and TP5
  onto one horizontal trace between U5 and U6.
- Move the ESP32 reset transistor Q3 beside the USB bridge. With Q4
  and R6 also repositioned, DTR and RTS together use 35.9 mm of trace
  and zero vias, down from 98.0 mm and ten vias. With U10 and U11
  relocated, ESP_EN uses 15.7 mm more trace than before the Q3 move.
- Route the X motor outputs into J3 on three parallel L4 diagonals and remove
  a bend at J4 pin 1. Simplify the indicator and USB CC1 routes.
- Route J1 through F1 to Q1 entirely on L1 and remove nine power vias.
  Straighten the nearby gate, Y_STEP and U6 bypass routes.
- Consolidate the L3 power and ground pours. Improve the 12 V path to D2,
  simplify the 3.3 V feeds and add local ground returns at layer changes.
- Straighten the buck switch trace and simplify DTR, RTS and motor routing.
  Shorten the shared motor UART from 69.6 to 46.4 mm and route Y_A1 and Y_A2
  directly to J4 on L4.
- Shorten the rear boot recovery trace and label the IO0 and GND pads.
- Use 1.00 × 2.05 mm plated slots at J1, 0.15 mm component-outline
  silkscreen strokes and 0.50 mm copper-to-edge clearance.
- Move 16 vias away from SMT lands and add thermal relief to four 0603
  ground pads.
- Group the solenoid indicator and reset supervisor parts below U2. Route
  SOL_SAFE and DRV_DISABLE_CMD directly into U9 on L1 and cross them with
  one straight motor UART trace on L4. Run X_STEP and X_DIR in parallel
  to U5 and move the RTS pull-up next to Q3. Move TP9, TP12, TP5 and TP14
  onto their traces. The seven interlock nets now use 6 vias and 182.1 mm of
  trace, down from 26 vias and 243.7 mm.
- Place C6 and C7 together at the ESP32 supply pin and group its reset circuit
  on L1. Extend L3 ground beneath the revised DTR and RTS routes on L4.
- Route Y_STEP beside Y_DIR and group the idle and alarm traces on L4 over
  L3 ground. Shorten the alarm trace from 22.8 to 14.1 mm and remove three
  DTR vias by routing from the USB bridge to the boot transistor on L1.
- Align U6's current shunts and their ground returns. Route all four Y motor
  outputs into J4 in pin order on L4 over L3 ground, and route the driver
  disable signal entirely on L1.
- Rotate U5 to match U6. Route X_B2 directly to J3 pin 4 on L1 and run
  the other three X windings over L3 ground. Shorten STEP and DIR and
  give each current shunt two ground vias.
- Tie the reversible USB-C contacts on L1 and extend L3 ground under VBUS.
  Move the U3 data vias off-pad.
- Add two 49.9 Ω shunts to U7 port 1 and move C29 and its 3.3 V via.
- Use 4.7 µF 0805 capacitors on both TMC2209 5VOUT rails.
- Move the solenoid flyback diode D4, rotate it 180°, and reroute the
  solenoid output and ground return.
- Shorten the USB-C D− tie, tune USB routing for JLC04161H-7628, and stitch
  ground near the J2 crossover.
- Remove the checked-in schematic PDF, bill of materials, and board renders.
  Use the files generated by `make build` for the current checkout.
- Include the bare-board STEP model and FluidNC configuration in `build/`.
- Prefix the JLC manufacturing files with `PHYSICLAW-JLC`.
- Use Python 3.12 and run build and placement checks in CI on Linux, Windows,
  and macOS.
- Document contribution and hardware release steps.

## Hardware v1.0 engineering baseline

The four-layer PCW-MC-01 has two TMC2209 drivers, a protected solenoid output,
USB-C programming, and 15 test pads. The board uses FluidNC v4.1.1. Factory
acceptance and bench qualification are pending.
