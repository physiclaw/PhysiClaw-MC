# PCW-MC-01

PCW-MC-01 is a 70 × 50 mm, four-layer ESP32 motion controller for two bipolar stepper motors and a 12 V / 0.8 A solenoid. The `01` suffix identifies hardware version 1.0. The release is for **first-article review**. JLC process approval and measurements on a populated board are pending.

## Build

Install **uv** and **KiCad 10**. The build uses the KiCad command-line tools and runs under uv-managed **Python 3.13**. On macOS it detects a standard KiCad installation. On other systems put `kicad-cli` on PATH, or set `KICAD_CLI` to the executable. This board was verified with KiCad 10.0.8. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

From the repository root, run

```sh
uv run --locked tools/build.py
```

uv selects Python 3.13 and installs the dependencies recorded in `uv.lock`. The build downloads the official FluidNC v4.1.1 archive with system `curl` and verifies its SHA-256. For an offline build, first provision Python and the locked dependencies with `uv sync --locked`, then supply the archive locally. [FluidNC release](https://github.com/bdring/FluidNC/releases/tag/v4.1.1)

```sh
uv run --locked --offline tools/build.py --firmware-archive /path/to/fluidnc-v4.1.1-posix.zip
```

Extract **`dist/PCW-MC-01-first-article.zip`** to access the order files. The build runs ERC, refills copper in a temporary copy, runs DRC with schematic parity, and checks the Gerbers, holes, stencil and placements. The ZIP also includes the schematics, assembly drawing, THT and purchasing lists, probe coordinates, firmware, programming instructions and SHA-256 manifest.

The placement geometry tests run with `uv run --locked python -m unittest discover -s tests`.

## Order at JLC

Use these files from the extracted package. The bare-board order uses the first file. For assembly on JLC China, add the second and third files and select **top side, millimetres**.

| JLC order field | File | What to expect |
|---|---|---|
| PCB / Gerber | `JLC/JLC-Gerbers.zip` | Four copper layers, both masks and silkscreens, top paste, one outline, separate plated and non-plated drills |
| SMT bill of materials | `JLC/JLC-BOM.csv` | 40 exact LCSC part numbers for 92 placements. The supplier-code column is `嘉立创元件编号`. |
| SMT coordinates / CPL | `JLC/JLC-CPL-mm.csv` | 92 top-side body centres and rotations corrected for the selected parts |

1. In the Gerber viewer verify one **70 × 50 mm** board and copper order **F.Cu → In1.Cu (GND) → In2.Cu (power) → B.Cu**. Send `fabrication/fill-and-cap.csv`, the IPC-D-356 netlist and `process.md` with the engineering instructions. Obtain JLC's acceptance of the stackup and the 50 filled and capped holes. [JLC Gerber and drill guide](https://jlcpcb.com/help/article/how-to-generate-gerber-and-drill-files-in-kicad-6)
2. For SMT, confirm 92 matched designators. Positions, drill coordinates and the board outline share KiCad's absolute origin, X right and Y up. Negative Y values are intentional. Rotation is in degrees counterclockwise, viewed from the top. Seven through-hole placements are listed in `assembly/tht-bom.csv` for a separate operation. [JLC BOM and CPL formats](https://www.jlc.com/portal/server_guide_48022.html)
3. In the JLC placement preview, compare pin 1, cathodes, the USB opening and the ESP32 antenna connector with `assembly/top-assembly.pdf` and `assembly/placement-review.csv`. The CSV gives the board coordinates of the named pads and the angle actually uploaded. For example, **U4 (CH340C) is 0°**, **U9 is 180°**, and **J2's opening faces the right board edge**. Confirm the actual JLC models and reflow profile before authorizing assembly. [JLC placement FAQ](https://jlcpcb.com/help/article/pcb-assembly-faqs-part-2)

## Change the design

| Source | Edit here |
|---|---|
| [KiCad project](pcb/kicad/PCW-MC-01.kicad_pro) | Schematic, PCB, design rules and project-local libraries. Edit MPN and LCSC fields in the schematic, then update the board. |
| [JLC part table](manufacturing/jlc-parts.csv) | Supplier package and orientation basis for each fitted part. Recheck the matching catalog footprint when substituting parts. |
| [Manufacturing instructions](manufacturing/process.md) | Stackup, assembly, orientation checks, programming and first-article acceptance |
| [FluidNC configuration](firmware/config.yaml) | Pin assignments, motor settings and solenoid control |

The design originated at `physiclaw-board` commit `6fc621a2d4e8174c19161d1886f545d6098b7343`. Library attribution is included with the design. [Library sources](pcb/kicad/libraries/sources.json) · [KiCad library license](pcb/kicad/libraries/KICAD-LICENSE.md)
