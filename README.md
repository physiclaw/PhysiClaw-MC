# PhysiClaw-MC

PCW-MC-01 v1.0 is a 70 × 50 mm, four-layer ESP32 controller for two bipolar
stepper motors and one 12 V / 0.8 A solenoid. Factory acceptance and bench
qualification are pending.

## Repository layout

| Directory | Start here |
| --- | --- |
| `pcb/kicad/` | [Editable KiCad project](pcb/kicad/PCW-MC-01.kicad_pro) with local libraries |
| `docs/` | [Design notes](docs/design.md) |
| `firmware/` | [FluidNC configuration and operation](firmware/README.md) |
| `manufacturing/` | [Fabrication, assembly, and first-article guide](manufacturing/process.md) |
| `tools/`, `tests/` | [Build](#generate-the-manufacturing-files) and [verification](#edit-and-verify-the-design) |

## Generate the manufacturing files

Install [KiCad 10 or newer], [uv], and GNU Make. On Windows, install GNU Make with
`choco install make` if it is missing, then open a new terminal.

The build checks `PATH` and the standard KiCad 10 installation paths on macOS
and Windows. For a different installation, set `KICAD_CLI` to the executable's
full path. On headless Linux, install Xvfb and run `xvfb-run -a make build` to
generate the 3D renders.

```sh
git clone https://github.com/physiclaw/PhysiClaw-MC.git
cd PhysiClaw-MC
make build
```

Each successful build replaces `dist/` (JLC order files) and `build/`
(review files). The review files include `build/schematic.pdf`, the assembly
BOM at `build/assembly/assembly.csv`, the FluidNC configuration in
`build/firmware/config.yaml`, the bare-board STEP model and
`build/manifest.json` with source and output checksums. Use
`make build VERBOSE=1` to show KiCad output.

`uv` uses Python 3.12 and installs dependencies from `uv.lock`.

For offline builds, run `uv sync --locked` once while online, then use
`make UV_OFFLINE=1 build`.

### Review the PCB

Open the [中文互动图解](docs/pcb-guide/index.html) in a browser to explore the
nine circuit areas. Select a component label to compare its routed footprint
with the same part in the KiCad schematic. Each area has a standalone SVG
with signal directions and fitted-part specifications. All 105 references
are covered, and the guide works offline from the checkout. To refresh the
illustrations after a build, run `uv run --locked python tools/guide_illustrations.py`.

The views are in `build/view/`.

- **Copper.** The `L1-*` through `L4-*` SVGs show filled copper in top-view
  alignment. `L3-power.svg` distinguishes 12 V, 3.3 V, and ground pours, plus the two short DTR/RTS crossings.
- **Routing.** `top-routing.svg`, `bottom-routing.svg`, and
  `top-bottom-routing.svg` show traces, pads, and vias with pours hidden.
  `usb-routing.svg` is the D+/D− close-up.
- **Reference.** `component-reference.svg` maps designators to footprints.
  `probe-map.svg` locates test points on both sides.
- **Fabrication.** `drill-and-slot-map.svg` shows holes, slots, and capped vias.
  `mask-and-paste.svg` shows mask and stencil apertures.
- **3D renders.** `3d-assembly.png` shows the populated board in perspective.
  `3d-top.png` and `3d-underside.png` show the two faces directly. Some package
  models use simplified geometry.

## Order a prototype at JLC

Run `make build` from the checkout you intend to order. Use the Gerbers, BOM,
and CPL from that build together.

| JLC upload field | File |
| --- | --- |
| PCB (Gerbers and drills) | `dist/PHYSICLAW-JLC-Gerbers.zip` |
| Proposed assembly panel (拼板示意图) | `dist/PHYSICLAW-JLC-panel.jpg` |
| SMT bill of materials (BOM) | `dist/PHYSICLAW-JLC-BOM.csv` |
| SMT placement file (CPL) | `dist/PHYSICLAW-JLC-CPL-mm.csv` |

Check the outline, drills, mask, and silkscreen in a Gerber viewer, then upload
the ZIP. Select **Standard SMT assembly (标准型)** at JLC China for the top
side. Upload each CSV separately and set placement units to millimetres.

Send JLC the [manufacturing guide](manufacturing/process.md) and both files in
`dist/fabrication/`. Before ordering, confirm the stackup, via fill and cap,
and assembly panel with CAM.

Approve the assembly preview against `build/assembly/top-assembly.pdf` and
`build/assembly/placement-review.csv`. Use `build/assembly/tht-bom.csv` for
through-hole assembly.

## Edit and verify the design

Update the schematic's MPN, LCSC code, datasheet and manufacturer (when
specified), then run **Update PCB from Schematic**. For substitutions, verify the
footprint and update the [JLC part table](manufacturing/jlc-parts.csv).
Run the placement geometry checks and regenerate the outputs. The build also
runs KiCad ERC and DRC.

```sh
make check
make build
```

The [CI workflow](.github/workflows/ci.yml) runs both commands on GitHub's
latest Linux, Windows, and macOS runners with KiCad 10.0.8. It also tests
newer stable releases as their installers and Linux images become available.

## Contributing and releases

See [contribution and release instructions](CONTRIBUTING.md) and the
[changelog](CHANGELOG.md). [OSHWA sharing best practices](https://oshwa.org/resources/sharing-best-practices/)

## License

Copyright © 2026 QiaoQian

The original hardware design and its source files, documentation, firmware
configuration, and tools use the [MIT License](LICENSE). The KiCad libraries
and upstream FluidNC firmware retain their respective licenses.
[KiCad library sources](pcb/kicad/libraries/sources.json) ·
[KiCad library license](pcb/kicad/libraries/KICAD-LICENSE.md)

[KiCad 10 or newer]: https://www.kicad.org/download/
[uv]: https://docs.astral.sh/uv/getting-started/installation/
