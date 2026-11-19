# Contributing

Open an issue with the hardware version, source commit or tag, KiCad or
FluidNC version, and steps to reproduce the problem. For a fault on an
assembled board, include the supply, loads, component substitutions, and
relevant measurements.

Follow the [design and verification instructions](README.md#edit-and-verify-the-design).
Update the firmware configuration and wiring instructions when an interface
changes. Keep the license and attribution for imported library items. Include
test results and before-and-after board views for layout changes.

## Release a hardware revision

1. Update the [changelog](CHANGELOG.md). Run `make check` and `make build` from the
   exact commit you intend to tag. Use a prerelease tag such as `v1.0-rc.1` while
   factory acceptance or bench qualification is pending.
2. Publish the tagged source and the `dist/` and `build/` outputs from that
   commit. Include the manufacturing guide, license, and build manifest.
   Link to the [required FluidNC release](firmware/README.md).
3. Record the board ID, hardware version, lot or serial number, and source
   commit or tag. Put the hardware version and URL for that source revision
   on the board, packaging, or assembly documentation.
