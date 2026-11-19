# PCW-MC-01 v1.0 reference files

The schematic, BOM, and renders below document the v1.0 engineering baseline.

- [Nine-sheet schematic PDF](schematic.pdf)
- [Bill of materials for all 99 fitted reference designators](bom.csv)
- [KiCad project for this checkout](../../pcb/kicad/PCW-MC-01.kicad_pro)

Run `make build` for current exports and board views. The build records
their checksums and the source checksums in `build/manifest.json`.
[Build instructions](../../README.md#generate-the-manufacturing-files)

![KiCad render of the component side](board-assembly.png)

*Component side with both motor connectors along the front edge. Some package
models use simplified geometry.*

![KiCad render of the solder side](board-underside.png)

*Solder side with the board ID and bootloader recovery pads TP1 (IO0) and
TP2 (GND) near the centre.*
