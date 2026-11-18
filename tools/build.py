"""Build the Rev A first-article package with KiCad 10 and Python 3."""

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
BOARD = "PCW-MC-01"
NAME = BOARD + "-RevA-first-article"
MAC = Path("/Applications/KiCad/KiCad.app/Contents")
ASSET = "fluidnc-v4.1.1-posix.zip"
URL = "https://github.com/bdring/FluidNC/releases/download/v4.1.1/" + ASSET
DIGEST = "9012318d5c9f46319a92648b68ad7c2da4d11645280e9d5c4b290740111a31b0"
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
                output.write(
                    path,
                    path.relative_to(folder),
                    ZIP_STORED if path.suffix == ".zip" else ZIP_DEFLATED,
                )


def file_list(folder):
    return {
        p.relative_to(folder).as_posix(): digest(p)
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


def verify_gerbers(cam):
    from board_data import require

    require(
        sorted(p.suffix[1:] for p in cam.iterdir()) == sorted(GERBERS),
        "Unexpected Gerber layer set",
    )
    for layer, function in GERBERS.items():
        plot = next(cam.glob("*." + layer)).read_text()
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
    outline = next(cam.glob("*.gm1")).read_text()
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
        "Incorrect Rev A outline or plot origin",
    )


def assembly_drawing(pcb, work, out, run):
    import pcbnew

    board = pcbnew.LoadBoard(str(pcb))
    # Room for labels beside the switch, connector slots and polarity symbols.
    label_offsets = {
        "J1": (5, -2.4),
        "J3": (-3.75, -1.8),
        "J4": (-3.75, -1.8),
        "SW1": (0, 0),
        "D4": (-4, 0),
        "D1": (0, -2.6),
        "D2": (0, -4),
    }
    for footprint in board.GetFootprints():
        labels = [
            item
            for item in footprint.GraphicalItems()
            if isinstance(item, pcbnew.PCB_TEXT)
            and item.GetLayer() == pcbnew.F_Fab
            and item.GetText() == "${REFERENCE}"
        ]
        board_only = footprint.GetAttributes() & pcbnew.FP_BOARD_ONLY
        if labels or board_only:
            footprint.Reference().SetVisible(False)
        if footprint.GetReference() in label_offsets:
            offset = label_offsets[footprint.GetReference()]
            for item in labels:
                item.SetPosition(
                    footprint.GetPosition()
                    + pcbnew.VECTOR2I(*(pcbnew.FromMM(v) for v in offset))
                )
                item.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
        if board_only:
            for item in labels:
                item.SetLayer(pcbnew.Dwgs_User)
    board.GetTitleBlock().SetTitle("PCW-MC-01 Rev A | Top assembly")
    board.GetTitleBlock().SetRevision("A")
    drawing = work / "assembly-drawing.kicad_pcb"
    pcbnew.SaveBoard(str(drawing), board)
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


def build(work, firmware):
    import pcbnew
    from board_data import assembly, geometry, check_paste, require

    cli = (
        os.environ.get("KICAD_CLI")
        or shutil.which("kicad-cli")
        or str(MAC / "MacOS/kicad-cli")
    )
    version = subprocess.check_output([cli, "version"], text=True).strip()
    require(
        version.startswith("10.") and pcbnew.Version() == version,
        "Use matching KiCad 10 CLI and pcbnew versions",
    )

    if firmware is None:
        firmware = work / ASSET
        # System curl uses the host's trust store, including on KiCad's bundled macOS Python.
        subprocess.run(
            [
                "curl",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--retry",
                "2",
                "--connect-timeout",
                "20",
                "--max-time",
                "180",
                "--output",
                str(firmware),
                URL,
            ],
            check=True,
        )
    require(
        firmware.is_file() and digest(firmware) == DIGEST,
        "FluidNC release archive SHA-256 mismatch",
    )

    # Refill a private copy so every export uses the same checked copper.
    cad = work / "hardware"
    shutil.copytree(
        ROOT / "hardware",
        cad,
        ignore=shutil.ignore_patterns(
            "*.kicad_prl",
            "*.lck",
            "*-backups",
            "fp-info-cache",
            ".DS_Store",
            "_autosave-*",
        ),
    )
    source_cad = file_list(cad)
    pcb = cad / (BOARD + ".kicad_pcb")
    sch = cad / (BOARD + ".kicad_sch")
    kit, cam = work / "kit", work / "cam"
    assy, checks, flash = kit / "assembly", kit / "checks", kit / "programming"
    jlc, fabrication = kit / "JLC", kit / "fabrication"
    for directory in (cam, assy, checks, flash, jlc, fabrication):
        directory.mkdir(parents=True)

    def run(*args):
        subprocess.run([cli, *map(str, args)], check=True)

    run(
        "sch",
        "erc",
        "--format",
        "json",
        "--severity-all",
        "--exit-code-violations",
        "-o",
        checks / "erc.json",
        sch,
    )
    run(
        "pcb",
        "drc",
        "--refill-zones",
        "--save-board",
        "--schematic-parity",
        "--all-track-errors",
        "--format",
        "json",
        "--severity-all",
        "--exit-code-violations",
        "-o",
        checks / "drc.json",
        pcb,
    )
    run("sch", "export", "netlist", "--format", "kicadxml", "-o", work / "net.xml", sch)
    run("sch", "export", "pdf", "--black-and-white", "-o", kit / "schematic.pdf", sch)
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
    # KiCad synthesizes an unapproved default material stack in this optional file.
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
    run("pcb", "export", "ipcd356", "-o", fabrication / (BOARD + ".d356"), pcb)
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
    assembly_drawing(pcb, work, assy / "top-assembly.pdf", run)
    board = pcbnew.LoadBoard(str(pcb))
    counts = assembly(
        board,
        work / "net.xml",
        work / "native-pos.csv",
        ROOT / "manufacturing/jlc-parts.csv",
        assy,
        jlc,
    )
    counts.update(geometry(board, cam, fabrication, assy))
    counts["stencil_apertures"] = check_paste(board, next(cam.glob("*.gtp")))
    process = ROOT / "manufacturing/process.md"
    shutil.copyfile(process, kit / "process.md")
    archive(cam, jlc / "JLC-Gerbers.zip")

    shutil.copyfile(firmware, flash / ASSET)
    shutil.copyfile(ROOT / "firmware/config.yaml", flash / "config.yaml")

    sources = {"hardware/" + k: v for k, v in source_cad.items()}
    for item in [
        "tools/build.py",
        "tools/board_data.py",
        "manufacturing/jlc-parts.csv",
        "manufacturing/process.md",
        "firmware/config.yaml",
    ]:
        sources[item] = digest(ROOT / item)
    manifest = {
        "board": BOARD,
        "revision": "A",
        "status": "first article pending factory and bench approval",
        "kicad": version,
        "counts": counts,
        "firmware_url": URL,
        "firmware_sha256": DIGEST,
        "source_sha256": sources,
        "fabrication_sha256": file_list(cam),
        "files_sha256": file_list(kit),
    }
    write_json(kit / "manifest.json", manifest)
    candidate = work / (NAME + ".zip")
    archive(kit, candidate)
    with ZipFile(candidate) as check:
        require(check.testzip() is None, "Archive integrity check failed")
    return candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--firmware-archive", type=Path, help="Use the pinned official ZIP from disk"
    )
    args = parser.parse_args()
    try:
        __import__("pcbnew")
    except ImportError:
        interpreter = os.environ.get("KICAD_PYTHON") or str(
            MAC / "Frameworks/Python.framework/Versions/Current/bin/python3"
        )
        if not Path(interpreter).is_file() or os.getenv("PCW_KICAD_REEXEC"):
            parser.exit(
                1,
                "Use KiCad 10 Python with pcbnew, or set KICAD_PYTHON to its executable.\n",
            )
        os.environ["PCW_KICAD_REEXEC"] = "1"
        os.execv(
            interpreter, [interpreter, str(Path(__file__).resolve()), *sys.argv[1:]]
        )
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".build-", dir=output) as temp:
        result = build(Path(temp), args.firmware_archive)
        destination = output / result.name
        os.replace(result, destination)
    print(destination)


if __name__ == "__main__":
    main()
