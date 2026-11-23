"""Generate v1.0 JLC order files and first-article review outputs."""

import argparse
import hashlib
import json
import os
import platform
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from time import perf_counter
import tomllib
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from board_data import assembly, check_paste, geometry, require
from inspection_views import (
    COPPER_COLOURS, PAPER, SVG, append_artwork, board_bounds, board_edges,
    component_reference, draw, drill_map, mask_and_paste, probe_map, save,
    shapes, text, usb_review,
)
from kicad_board import Board

ROOT = Path(__file__).resolve().parents[1]
BOARD = "PCW-MC-01"
DIST_PREFIX = "PHYSICLAW-JLC"
VERSION = (
    "v"
    + tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
)
LAYERS = (
    "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts"
)
GERBERS = {
    "gtl": "Copper,L1,Top",
    "g1": "Copper,L2,Inr",
    "g2": "Copper,L3,Inr",
    "gbl": "Copper,L4,Bot",
    "gts": "Soldermask,Top",
    "gbs": "Soldermask,Bot",
    "gtp": "Paste,Top",
    "gto": "Legend,Top",
    "gbo": "Legend,Bot",
    "gm1": "Profile,NP",
}


def styled(label, colour):
    if (sys.stdout.isatty() and "NO_COLOR" not in os.environ
            and os.environ.get("TERM") not in (None, "dumb")):
        return f"\033[{colour}m{label}\033[0m"
    return label


def stage(number, description):
    print(f"{styled(f'[{number}/5]', '36')} {description}", flush=True)


def kicad_environment(cli, work):
    env = os.environ.copy()
    if platform.system() != "Darwin":
        return env

    # KiCad CLI instances otherwise share the same wxWidgets lock file.
    scratch = work / "tmp"
    scratch.mkdir()
    env["TMPDIR"] = str(scratch)

    # The macOS bundle's Fontconfig can choke on newer system Fontconfig rules.
    in_bundle = Path(cli).resolve().parts[-3:-1] == ("Contents", "MacOS")
    if in_bundle and not {"FONTCONFIG_FILE", "FONTCONFIG_PATH"}.intersection(env):
        config = ET.Element("fontconfig")
        for path in ("/System/Library/Fonts", "/Library/Fonts", "~/Library/Fonts"):
            ET.SubElement(config, "dir").text = path
        ET.SubElement(config, "cachedir").text = str(scratch / "font-cache")
        fonts = scratch / "fonts.conf"
        ET.ElementTree(config).write(fonts, encoding="utf-8", xml_declaration=True)
        env["FONTCONFIG_FILE"] = str(fonts)
    return env


def check_design(run, editor, check, report, source, *options):
    try:
        run(
            editor, check, *options, "--format", "json", "--severity-all",
            "--exit-code-violations", "-o", report, source,
        )
    except subprocess.CalledProcessError:
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        sections = (data, *data.get("sheets", []))
        issues = (
            issue for section in sections
            for key in ("violations", "unconnected_items", "schematic_parity")
            for issue in section.get(key, [])
        )
        for issue in issues:
            print(f"  {issue['severity'].upper()}  {issue['description']}", file=sys.stderr)
            for item in issue.get("items", []):
                print(f"      {item['description']}", file=sys.stderr)
        raise


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def archive(folder, target):
    with ZipFile(target, "w", ZIP_DEFLATED) as output:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(folder))


def file_list(folder):
    return {
        p.relative_to(folder).as_posix(): digest(p)
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def verify_gerbers(cam):
    require(
        sorted(p.suffix[1:] for p in cam.iterdir()) == sorted(GERBERS),
        "Unexpected Gerber layer set",
    )
    for layer, function in GERBERS.items():
        plot = next(cam.glob("*." + layer)).read_text(encoding="utf-8")
        require(
            all(
                record in plot
                for record in (
                    "%TF.SameCoordinates,Original*%",
                    "%MOMM*%",
                    "%FSLAX46Y46*%",
                    f"%TF.FileFunction,{function}*%",
                )
            ),
            "Incorrect Gerber layer or origin: " + layer,
        )
    outline = next(cam.glob("*.gm1")).read_text(encoding="utf-8")
    edges = []
    previous = None
    for x, y, mode in re.findall(r"^X(-?\d+)Y(-?\d+)D0([12])\*$", outline, re.M):
        point = (int(x) / 1e6, int(y) / 1e6)
        if mode == "1":
            require(previous is not None, "Outline starts without a move")
            edges.append(frozenset((previous, point)))
        previous = point
    corners = [(100, -50), (170, -50), (170, -100), (100, -100)]
    require(
        len(edges) == 4
        and set(edges)
        == {frozenset((corners[i - 1], corner)) for i, corner in enumerate(corners)},
        "Incorrect v1.0 outline or plot origin",
    )


def assembly_drawing(board, work, out, run):
    drawing = work / "assembly-drawing.kicad_pcb"
    board.write_assembly_view(drawing, BOARD, VERSION)
    run(
        "pcb",
        "export",
        "pdf",
        "--mode-single",
        "--layers",
        "F.Fab,Edge.Cuts",
        "--black-and-white",
        "--exclude-value",
        "--scale",
        "2",
        "--include-border-title",
        "-o",
        out,
        drawing,
    )


L3_REGIONS = {
    "V12": ("12 V", COPPER_COLOURS["In2.Cu"]),
    "V3V3": ("3.3 V", "#74479b"),
    "GND": ("GND", "#477484"),
}


def overlay_routes(svg, bottom):
    require(svg.get("viewBox") == bottom.get("viewBox"), "Routing plots are misaligned")
    x, y, width, height = svg.attrib["viewBox"].split()
    bounds = dict(x=x, y=y, width=width, height=height)
    top_shapes = shapes(svg)
    for node in top_shapes:
        svg.remove(node)

    defs = draw(svg, "defs")
    for name, colour, artwork in (
        ("l4", COPPER_COLOURS["B.Cu"], shapes(bottom)),
        ("l1", COPPER_COLOURS["F.Cu"], top_shapes),
    ):
        mask = draw(defs, "mask", id=name, maskUnits="userSpaceOnUse", **bounds)
        mask.extend(artwork)
        for node in mask.iter():
            if style := node.get("style"):
                # Clearances and drill marks are black in the luminance mask.
                node.set("style", style.replace("#000000", "#ffffff").replace("#FFFFFF", "#000000"))
        draw(svg, "rect", **bounds, fill=colour, mask=f"url(#{name})")


def style_copper_plot(path, label, colour, show_pours, *, bottom=None, zone_colours=None, outlines=None):
    svg = ET.parse(path).getroot()
    ET.register_namespace("", SVG[1:-1])
    if bottom is not None:
        overlay_routes(svg, ET.parse(bottom).getroot())

    x, y, width, height = map(float, svg.attrib["viewBox"].split())
    left, top = x - 4, y - 12
    page_width, page_height = width + 8, height + 16
    svg.set("width", f"{page_width:g}mm")
    svg.set("height", f"{page_height:g}mm")
    svg.set("viewBox", f"{left:g} {top:g} {page_width:g} {page_height:g}")

    if bottom is None:
        zones = zone_colours or {}
        for element in svg.iter():
            ink = zones.get(element.get("d"), colour)
            if style := element.get("style"):
                element.set("style", style.replace("#000000", ink).replace("#FFFFFF", PAPER))
            elif element.get("d") in zones:
                # KiCad's trace paths inherit their stroke from a group.
                element.set("stroke", ink)

    svg.find(SVG+"title").text = f"{BOARD} · {label}"
    svg.insert(0, ET.Element(SVG+"rect", {
        "x": str(left), "y": str(top), "width": str(page_width),
        "height": str(page_height), "fill": PAPER,
    }))
    if outlines is not None:
        group = ET.Element(SVG+"g", {"opacity": "0.48"})
        svg.insert(1, group)
        append_artwork(group, ET.parse(outlines).getroot(), "#34465b")

    header = draw(svg, "g", font_family="sans-serif")
    text(header, x, y-7, label, size=2.8, font_weight="bold")
    mode = "Filled copper" if show_pours else "Board pours hidden"
    text(header, x, y-3.6, f"{BOARD} · {VERSION} · Top view · {mode}",
         size=1.55, colour="#475569")
    if zone_colours is not None:
        offsets, legend = (33, 24, 14, 6), (*L3_REGIONS.values(), ("Other", colour))
    elif bottom is not None:
        offsets, legend = (23, 11), (("L1 Top", COPPER_COLOURS["F.Cu"]),
                                     ("L4 Bottom", COPPER_COLOURS["B.Cu"]))
    else:
        offsets, legend = (), ()
        draw(header, "rect", x=x+width-3, y=y-9, width=3, height=3, rx=.5, fill=colour)
    for offset, (caption, hue) in zip(offsets, legend, strict=True):
        text(header, x+width-offset, y-7, caption, size=1.65, colour=hue, font_weight="bold")
    save(svg, path)


def plot_board_svg(source, layer, plot, run, *, drills="2"):
    run(
        "pcb",
        "export",
        "svg",
        "--mode-single",
        "--layers",
        f"{layer},Edge.Cuts",
        "--fit-page-to-board",
        "--exclude-drawing-sheet",
        "--black-and-white",
        "--drill-shape-opt",
        drills,
        "-o",
        plot,
        source,
    )


def l3_copper_colours(board, work, complete, run):
    def paths(file):
        return {p.attrib["d"] for p in ET.parse(file).iter(SVG+"path")}

    layer = "In2.Cu"
    baseline = work / "l3-lands.svg"
    region = work / "l3-region.kicad_pcb"
    board.write_layer_net_view(region, layer, None)
    plot_board_svg(region, layer, baseline, run)
    common = paths(baseline)
    zones = {}
    plotted = work / "l3-region.svg"
    for net, (_, colour) in L3_REGIONS.items():
        board.write_layer_net_view(region, layer, net)
        plot_board_svg(region, layer, plotted, run)
        for path in paths(plotted) - common:
            require(path not in zones, f"Ambiguous L3 copper on {net}")
            zones[path] = colour
    require(zones.keys() == paths(complete) - common,
            "L3 net colours do not cover the plotted pours and traces")
    return zones


def pcb_views(board, pcb, work, out, cam, fill_and_cap, assy, run):
    routing = work / "routing-view.kicad_pcb"
    board.write_routing_view(routing)

    outline_pcb = work / "component-outlines.kicad_pcb"
    board.write_outline_view(outline_pcb)
    fab = work / "component-outlines.svg"
    plot_board_svg(outline_pcb, "F.Fab,B.Fab", fab, run, drills="0")
    edges = board_edges(board)
    bounds = board_bounds(edges)

    plots = (
        (pcb, "F.Cu", "L1-top-copper.svg", "L1 · Top copper"),
        (pcb, "In1.Cu", "L2-ground.svg", "L2 · Ground"),
        (pcb, "In2.Cu", "L3-power.svg", "L3 · Power regions"),
        (pcb, "B.Cu", "L4-bottom-copper.svg", "L4 · Bottom copper"),
        (routing, "F.Cu", "top-routing.svg", "L1 · Top routing"),
        (routing, "B.Cu", "bottom-routing.svg", "L4 · Bottom routing"),
    )
    for source, layer, filename, _ in plots:
        plot_board_svg(source, layer, out / filename, run)
    overlay = out / "top-bottom-routing.svg"
    shutil.copyfile(out / "top-routing.svg", overlay)
    style_copper_plot(
        overlay, "Top and bottom routing", COPPER_COLOURS["F.Cu"], False,
        bottom=out / "bottom-routing.svg", outlines=fab,
    )
    for source, layer, filename, label in plots:
        plot = out / filename
        if layer == "In2.Cu":
            zones = l3_copper_colours(board, work, plot, run)
            style_copper_plot(plot, label, "#526071", True, zone_colours=zones)
        else:
            style_copper_plot(
                plot, label, COPPER_COLOURS[layer], source == pcb,
                outlines=fab if source == routing else None,
            )

    component_reference(out, board, bounds, fab, BOARD, VERSION)
    drill_map(out, cam, fill_and_cap, edges, bounds, board)
    mask_and_paste(out, pcb, work, board, bounds,
                   lambda source, layer, path: plot_board_svg(source, layer, path, run, drills="0"))
    usb_review(out, board, bounds, fab)
    probe_map(out, assy / "probe-points.csv", bounds, fab, board)

    print("      Rendering assembly, top and underside views…", flush=True)
    for side, rotation, zoom, filename, quality, background_options in (
        (
            "top",
            "-20,0,0",
            "1.02",
            "3d-assembly.png",
            "high",
            ("opaque", "--floor", "--perspective"),
        ),
        ("top", "0,0,0", "1.1", "3d-top.png", "basic", ("transparent",)),
        ("bottom", "0,0,0", "1.1", "3d-underside.png", "basic", ("transparent",)),
    ):
        run(
            "pcb",
            "render",
            "--side",
            side,
            "--rotate",
            rotation,
            "--zoom",
            zoom,
            "--width",
            "1600",
            "--height",
            "1200",
            "--quality",
            quality,
            "--background",
            *background_options,
            "-o",
            out / filename,
            pcb,
        )


def build(work, *, verbose=False):
    cli = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
    if not cli:
        default_paths = {
            "Darwin": Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
            "Windows": Path(os.environ.get("ProgramFiles", "C:/Program Files"))
            / "KiCad/10.0/bin/kicad-cli.exe",
        }
        default_cli = default_paths.get(platform.system())
        if default_cli and default_cli.is_file():
            cli = str(default_cli)
    require(cli, "Put KiCad 10 or newer on PATH, or set KICAD_CLI to its executable.")
    env = kicad_environment(shutil.which(cli) or cli, work)

    def run(*args, capture=False):
        result = subprocess.run(
            [cli, *map(str, args)], env=env, text=True, errors="replace",
            stdout=subprocess.PIPE if capture or not verbose else None,
        )
        if result.stdout and (result.returncode or re.search(
            r"\b(?:warning|error|fatal)\s*:|^\s*(?:warning|error|fatal)\b",
            result.stdout, re.IGNORECASE | re.MULTILINE,
        )):
            print(result.stdout.rstrip(), file=sys.stderr)
        result.check_returncode()
        return result.stdout

    version = run("version", capture=True).strip()
    major = re.match(r"(\d+)\.", version)
    require(major and int(major[1]) >= 10, "Use KiCad CLI 10 or newer for this board")
    print(f"{styled(f'{BOARD} {VERSION}', '1')}  |  KiCad {version}\n", flush=True)

    stage(1, "Check the schematic and PCB")
    # Refill a private copy so every export uses the same checked copper.
    cad_source = ROOT / "pcb" / "kicad"
    cad = work / "kicad"
    shutil.copytree(
        cad_source,
        cad,
        ignore=shutil.ignore_patterns(
            "*.kicad_prl",
            "*.lck",
            ".history",
            "#auto_saved_files#",
            "*-save.kicad_pcb",
            "*.kicad_pcb-bak",
            "*.kicad_sch-bak",
            "*-backups",
            "fp-info-cache",
            ".DS_Store",
            "_autosave-*",
        ),
    )
    source_cad = file_list(cad)
    pcb = cad / (BOARD + ".kicad_pcb")
    sch = cad / (BOARD + ".kicad_sch")
    dist, review, cam = work / "dist", work / "build", work / "cam"
    assy, checks, fabrication = review / "assembly", review / "checks", dist / "fabrication"
    view = review / "view"
    fill_and_cap = fabrication / f"{DIST_PREFIX}-fill-and-cap.csv"
    firmware_config = Path("firmware/config.yaml")
    for directory in (cam, assy, checks, fabrication, view, review / firmware_config.parent):
        directory.mkdir(parents=True)

    check_design(run, "sch", "erc", checks / "erc.json", sch)
    print(f"      {styled('PASS', '32')}  Schematic electrical rules (ERC)", flush=True)
    check_design(
        run, "pcb", "drc", checks / "drc.json", pcb,
        "--refill-zones",
        "--save-board",
        "--schematic-parity",
        "--all-track-errors",
    )
    print(f"      {styled('PASS', '32')}  Board design rules and schematic match (DRC)", flush=True)

    stage(2, "Export fabrication and assembly files")
    run("sch", "export", "netlist", "--format", "kicadxml", "-o", work / "net.xml", sch)
    run(
        "pcb",
        "export",
        "gerbers",
        "--subtract-soldermask",
        "--layers",
        LAYERS,
        "--precision",
        "6",
        "-o",
        cam,
        pcb,
    )
    # Use the manufacturing guide for the stackup submitted to CAM.
    for job in cam.glob("*.gbrjob"):
        job.unlink()
    verify_gerbers(cam)
    run(
        "pcb",
        "export",
        "drill",
        "--excellon-separate-th",
        "--excellon-units",
        "mm",
        "--excellon-oval-format",
        "alternate",
        "--drill-origin",
        "absolute",
        "--excellon-zeros-format",
        "decimal",
        "-o",
        cam,
        pcb,
    )
    run("pcb", "export", "ipcd356", "-o", fabrication / f"{DIST_PREFIX}.d356", pcb)
    run(
        "pcb",
        "export",
        "pos",
        "--smd-only",
        "--exclude-dnp",
        "--side",
        "front",
        "--units",
        "mm",
        "--format",
        "csv",
        "-o",
        work / "native-pos.csv",
        pcb,
    )
    board = Board(pcb)
    counts = assembly(
        board,
        work / "net.xml",
        work / "native-pos.csv",
        ROOT / "manufacturing/jlc-parts.csv",
        assy,
        bom_path=dist / f"{DIST_PREFIX}-BOM.csv",
        cpl_path=dist / f"{DIST_PREFIX}-CPL-mm.csv",
    )
    counts.update(geometry(board, cam, fill_and_cap, assy))
    counts["stencil_apertures"] = check_paste(board, next(cam.glob("*.gtp")))
    print(f"      {counts['SMT']} surface-mount parts, {counts['THT']} through-hole parts, "
          f"{counts['filled_and_capped']} filled and capped vias", flush=True)

    stage(3, "Generate review drawings and 3D views")
    run("sch", "export", "pdf", "--black-and-white", "-o", review / "schematic.pdf", sch)
    step = review / f"{BOARD}-bare-board.step"
    step_options = ()
    if platform.system() == "Darwin":
        # KiCad's macOS STEP exporter reads attributes of the destination before writing.
        step.touch()
        step_options = ("--force",)
    run("pcb", "export", "step", "--board-only", *step_options, "-o", step, pcb)
    require(step.stat().st_size > 0, "KiCad wrote an empty STEP model")
    assembly_drawing(board, work, assy / "top-assembly.pdf", run)
    pcb_views(board, pcb, work, view, cam, fill_and_cap, assy, run)
    shutil.copyfile(ROOT / "manufacturing/process.md", review / "process.md")
    shutil.copyfile(ROOT / firmware_config, review / firmware_config)
    shutil.copyfile(ROOT / "LICENSE", review / "LICENSE")

    stage(4, "Verify the Gerber archive and record file checksums")
    gerbers = dist / f"{DIST_PREFIX}-Gerbers.zip"
    archive(cam, gerbers)
    with ZipFile(gerbers) as check:
        require(check.testzip() is None, "Gerber archive integrity check failed")

    sources = {
        (cad_source / k).relative_to(ROOT).as_posix(): v for k, v in source_cad.items()
    }
    for item in [
        "Makefile",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
        "tools/kicad_board.py",
        "tools/build.py",
        "tools/board_data.py",
        "tools/inspection_views.py",
        "manufacturing/jlc-parts.csv",
        "manufacturing/process.md",
        firmware_config.as_posix(),
        "LICENSE",
    ]:
        sources[item] = digest(ROOT / item)
    manifest = {
        "board": BOARD,
        "version": VERSION,
        "python": platform.python_version(),
        "status": "first article pending factory and bench approval",
        "kicad": version,
        "counts": counts,
        "source_sha256": sources,
        "fabrication_sha256": file_list(cam),
        "files_sha256": file_list(dist),
        "review_sha256": file_list(review),
    }
    write_json(review / "manifest.json", manifest)
    return dist, review


def publish(work, outputs):
    previous = work / "previous"
    previous.mkdir()
    lock = ROOT / ".dist-publish"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise RuntimeError("Another build is publishing manufacturing files") from error

    try:
        for output in outputs:
            destination = ROOT / output.name
            if destination.exists():
                destination.rename(previous / output.name)
            output.rename(destination)
    except BaseException:
        for output in reversed(outputs):
            destination = ROOT / output.name
            backup = previous / output.name
            if not output.exists():
                destination.rename(output)
            if backup.exists():
                backup.rename(destination)
        raise
    finally:
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="show all KiCad output")
    args = parser.parse_args()
    start = perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix=".dist-", dir=ROOT) as temp:
            work = Path(temp)
            outputs = build(work, verbose=args.verbose)
            stage(5, "Publish the build outputs")
            publish(work, outputs)
    except subprocess.CalledProcessError as error:
        operation = " ".join(arg for arg in error.cmd[1:4] if not arg.startswith("-"))
        raise SystemExit(
            f"Build failed. KiCad {operation} exited with status {error.returncode}."
        ) from None
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(f"Build failed. {error}") from None

    print(f"\n{styled('BUILD COMPLETE', '1;32')}  {perf_counter() - start:.1f} s")
    print(f"Files in {ROOT}")
    for path, description in (
        ("dist/", "JLCPCB order files"),
        ("build/", "Schematic, assembly drawings and 3D views"),
        ("build/checks/", "KiCad check reports"),
        ("build/manifest.json", "Build details and file checksums"),
    ):
        print(f"  {path:<21} {description}")


if __name__ == "__main__":
    main()
