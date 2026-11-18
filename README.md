# PhysiClaw-MC

PCW-MC-01 (hardware v1.0) is a 70 × 50 mm, four-layer ESP32 controller for two
bipolar stepper motors and a 12 V / 0.8 A solenoid.

- **Open the design.** Clone or download this repository and open
  [PCW-MC-01.kicad_pro](pcb/kicad/PCW-MC-01.kicad_pro) in KiCad 10.
- **Make a prototype.** [Generate the order files](#generate-the-manufacturing-files)
  and [upload them to JLC](#order-a-prototype-at-jlc).
- **Program an assembled board.**
  [Install FluidNC and the board configuration][Programming guide].

## Generate the manufacturing files

Install [KiCad 10] and [uv]. The build was verified with KiCad 10.0.8.

```sh
git clone https://github.com/physiclaw/PhysiClaw-MC.git
cd PhysiClaw-MC
uv run --locked tools/build.py
```

Each successful build replaces `dist/` with JLC order files and `build/` with
review drawings, checks, and `manifest.json`.

uv uses Python 3.13 and installs dependencies from `uv.lock`. The build finds
`kicad-cli` on `PATH` or in the standard macOS installation. Set `KICAD_CLI` to
select a different executable.

For offline builds, run `uv sync --locked` once while online, then use
`uv run --locked --offline tools/build.py`.

### Review the PCB

The views are in `build/view/`.

- **Copper.** The `L1-*` through `L4-*` SVGs show filled copper in top-view
  alignment. `L3-power.svg` distinguishes 12 V, 3.3 V, and ground pours.
- **Routing.** `top-routing.svg`, `bottom-routing.svg`, and
  `top-bottom-routing.svg` show traces, pads, and vias with pours hidden.
  `usb-routing.svg` is the D+/D− close-up.
- **Reference.** `component-reference.svg` maps designators to footprints.
  `probe-map.svg` locates test points on both sides.
- **Fabrication.** `drill-and-slot-map.svg` shows holes, slots, and capped vias.
  `mask-and-paste.svg` shows mask and stencil apertures.
- **3D.** `3d-assembly.png` is the tabletop view. `3d-top.png` and
  `3d-underside.png` show both faces straight on. Some component models use
  simplified bodies.

## Order a prototype at JLC

Factory approval and bench qualification are pending.

| JLC upload field | File |
| --- | --- |
| PCB (Gerbers and drills) | `dist/JLC-Gerbers.zip` |
| SMT bill of materials (BOM) | `dist/JLC-BOM.csv` |
| SMT placement file (CPL) | `dist/JLC-CPL-mm.csv` |

Check the outline, drills, mask, and silkscreen in a Gerber viewer, then upload
the ZIP. For top-side SMT assembly through JLC China, upload each CSV separately
and set placement units to millimetres.

Send JLC the [manufacturing guide](manufacturing/process.md) and both files in
`dist/fabrication/`. Confirm the stackup and via fill and cap with CAM before
ordering.

Approve the assembly preview against `build/assembly/top-assembly.pdf` and
`build/assembly/placement-review.csv`. Use `build/assembly/tht-bom.csv` for
through-hole assembly.

## Edit and verify the design

Edit parts and their MPN and LCSC fields in the schematic, then run
**Update PCB from Schematic**. For substitutions, verify the footprint and
update the [JLC part table](manufacturing/jlc-parts.csv). Rebuild after changes.

Run the placement geometry tests.

```sh
uv run --locked python -m unittest discover -s tests
```

## License

The original design files, tools, firmware configuration, and documentation are
under the [MIT License](LICENSE). Third-party assets retain their own terms.
[KiCad library sources](pcb/kicad/libraries/sources.json) ·
[KiCad library license](pcb/kicad/libraries/KICAD-LICENSE.md)

[KiCad 10]: https://www.kicad.org/download/
[uv]: https://docs.astral.sh/uv/getting-started/installation/
[Programming guide]: manufacturing/process.md#programming
