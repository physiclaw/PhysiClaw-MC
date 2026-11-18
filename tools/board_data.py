"""Build the assembly tables and verify Rev A's plotted manufacturing geometry."""

import csv
import math
import re
from collections import Counter, defaultdict
import xml.etree.ElementTree as ET

import pcbnew as pcb


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(rows)


def ref_key(ref):
    prefix, number = re.fullmatch(r"([A-Z]+)([0-9]+)", ref).groups()
    return prefix, int(number)


def xy(item):
    pos = item.GetPosition()
    return pcb.ToMM(pos.x), pcb.ToMM(pos.y)


def pad_center(footprint, number):
    points = [
        xy(p)
        for p in footprint.Pads()
        if p.GetNumber() == number and p.IsOnLayer(pcb.F_Cu)
    ]
    require(points, f"{footprint.GetReference()} has no copper pad {number}")
    # SW1 uses two lands per electrical terminal. Their midpoint identifies the row.
    return tuple(sum(axis) / len(points) for axis in zip(*points))


def placement(footprint, part, row):
    ref = footprint.GetReference()
    x, y = xy(footprint)
    native = footprint.GetOrientation().AsDegrees()
    require(
        row["Side"] == "top"
        and footprint.GetLayer() == pcb.F_Cu
        and abs(float(row["PosX"]) - x) < 0.00001
        and abs(float(row["PosY"]) + y) < 0.00001
        and abs(math.remainder(float(row["Rot"]) - native, 360)) < 0.00001,
        "Native placement readback failed at " + ref,
    )
    start, end = (pad_center(footprint, part[key]) for key in ("From pad", "To pad"))
    dx, dy = end[0] - start[0], start[1] - end[1]  # CAD Y down to Gerber Y up
    require(math.hypot(dx, dy) > 0.1, "Coincident orientation pads at " + ref)
    require(
        part["Catalog footprint ID"]
        and part["Catalog axis CCW deg"] in {"0", "90", "180", "270"},
        "Missing catalog orientation for " + ref,
    )
    axis = math.degrees(math.atan2(dy, dx))
    angle = round(axis - float(part["Catalog axis CCW deg"]), 3) % 360
    cpl = (ref, f"{x:.3f}", f"{-y:.3f}", "Top", f"{angle:.3f}")
    audit = (
        ref,
        part["LCSC"],
        *cpl[1:3],
        native,
        angle,
        part["From pad"],
        f"{start[0]:.3f}",
        f"{-start[1]:.3f}",
        part["To pad"],
        f"{end[0]:.3f}",
        f"{-end[1]:.3f}",
    )
    return cpl, audit


def assembly(board, netlist, native_positions, package_table, out, jlc):
    parts = {
        f.GetReference(): f
        for f in board.GetFootprints()
        if not f.GetAttributes() & (pcb.FP_BOARD_ONLY | pcb.FP_DNP)
    }
    schematic = {
        c.get("ref"): c
        for c in ET.parse(netlist).findall("./components/comp")
        if not c.get("ref").startswith("#") and c.find("property[@name='dnp']") is None
    }
    require(
        parts.keys() == schematic.keys(),
        "Fitted references differ between the board and schematic",
    )
    with package_table.open(encoding="utf-8") as stream:
        catalog = list(csv.DictReader(stream))
        names = {r["LCSC"]: r for r in catalog}
        require(len(names) == len(catalog), "Duplicate LCSC code in package table")
    with native_positions.open(encoding="utf-8") as stream:
        positions = list(csv.DictReader(stream))
    smt = {r for r, f in parts.items() if f.GetAttributes() & pcb.FP_SMD}
    require(
        len(positions) == len(smt) and {r["Ref"] for r in positions} == smt,
        "KiCad placement export does not cover the fitted SMT parts",
    )
    native = {row["Ref"]: row for row in positions}
    placements, audit = [], []
    grouped = defaultdict(list)
    lines = []
    for ref in sorted(parts, key=ref_key):
        f = parts[ref]
        c = schematic[ref]
        fields = {field.get("name"): field.text for field in c.findall("fields/field")}
        mpn, code = fields["MPN"], fields["LCSC"]
        lib_id = f.GetFPID()
        land = f"{lib_id.GetLibNickname()}:{lib_id.GetLibItemName()}"
        require(
            all(f.GetFieldText(k) == fields[k] for k in ("MPN", "LCSC"))
            and f.GetValue() == c.findtext("value")
            and land == c.findtext("footprint"),
            "PCB/schematic identity mismatch at " + ref,
        )
        part = names[code]
        require(
            part["MPN"] == mpn
            and part["KiCad footprint"] == str(lib_id.GetLibItemName()),
            "Catalog identity or footprint mismatch at " + ref,
        )
        if ref in smt:
            cpl, evidence = placement(f, part, native[ref])
            placements.append(cpl)
            audit.append(evidence)
        process = "SMT" if ref in smt else "THT"
        require(
            process == "SMT" or f.GetAttributes() & pcb.FP_THROUGH_HOLE,
            "Undefined assembly process at " + ref,
        )
        grouped[(process, mpn, code, part["Package"])].append(ref)
        lines.append((ref, mpn, code, f.GetValue(), land, process))
    require(
        set(names) == {r[2] for r in lines},
        "Supplier package table contains unused codes",
    )
    write_csv(
        out / "assembly.csv",
        ["Reference", "MPN", "LCSC", "Value", "Footprint", "Process"],
        lines,
    )
    write_csv(
        jlc / "JLC-CPL-mm.csv",
        ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"],
        placements,
    )
    write_csv(
        out / "placement-review.csv",
        [
            "Designator",
            "LCSC",
            "Mid X mm",
            "Mid Y mm",
            "KiCad deg",
            "JLC deg",
            "From pad",
            "From X mm",
            "From Y mm",
            "To pad",
            "To X mm",
            "To Y mm",
        ],
        audit,
    )
    handles = {"SMT": [], "THT": []}
    purchase = []
    for (process, mpn, code, package), refs in sorted(grouped.items()):
        handles[process].append((mpn, ",".join(refs), package, len(refs), code))
        purchase.append((mpn, code, len(refs), ",".join(refs), package, process))
    for process, rows in handles.items():
        write_csv(
            jlc / "JLC-BOM.csv" if process == "SMT" else out / "tht-bom.csv",
            ["Comment", "Designator", "Footprint", "Quantity", "嘉立创元件编号"],
            rows,
        )
    write_csv(
        out / "purchase.csv",
        ["MPN", "LCSC", "Quantity", "Designators", "Package", "Process"],
        purchase,
    )
    return {
        "fitted": len(parts),
        "SMT": len(smt),
        "THT": len(parts) - len(smt),
        "MPNs": len(names),
        "SMT_MPNs": len(handles["SMT"]),
        "placements_with_rotation_correction": sum(
            abs(math.remainder(row[5] - row[4], 360)) > 0.001 for row in audit
        ),
    }


def read_drill(path):
    """Read KiCad's absolute metric Excellon, including two-endpoint G85 slots."""
    text = path.read_text()
    require("METRIC" in text and "G90" in text, "Unexpected drill format")
    tools = dict(re.findall(r"^T(\d+)C([\d.]+)$", text, re.M))
    result = []
    point = r"X(-?[\d.]+)Y(-?[\d.]+)"
    for line in text.splitlines():
        selection = re.fullmatch(r"T(\d+)", line)
        if selection:
            diameter = float(tools[selection[1]])
        if not line.startswith("X"):
            continue
        match = re.fullmatch(point + "(?:G85" + point + ")?", line)
        require(match, "Unsupported drill record: " + line)
        x, y = float(match[1]), -float(match[2])
        if match[3] is None:
            result.append((x, y, diameter, diameter, 0))
            continue
        end_x, end_y = float(match[3]), -float(match[4])
        dx, dy = end_x - x, end_y - y
        result.append(
            (
                (x + end_x) / 2,
                (y + end_y) / 2,
                diameter,
                diameter + math.hypot(dx, dy),
                math.degrees(math.atan2(dy, dx)) % 180,
            )
        )
    return result


def geometry(board, cam, fabrication, out):
    expected = {"PTH": [], "NPTH": []}
    thermals, probes = [], []
    for track in board.GetTracks():
        if isinstance(track, pcb.PCB_VIA):
            d = pcb.ToMM(track.GetDrill())
            expected["PTH"].append((*xy(track), d, d, 0))
    for f in board.GetFootprints():
        ref = f.GetReference()
        for pad in f.Pads():
            x, y = xy(pad)
            if ref.startswith("TP"):
                probes.append(
                    (
                        ref,
                        pad.GetNetname(),
                        "Top" if pad.IsOnLayer(pcb.F_Cu) else "Bottom",
                        x,
                        y,
                    )
                )
            size = pad.GetDrillSize()
            w, h = pcb.ToMM(size.x), pcb.ToMM(size.y)
            if not w:
                continue
            kind = "NPTH" if pad.GetAttribute() == pcb.PAD_ATTRIB_NPTH else "PTH"
            angle = (
                (pad.GetOrientation().AsDegrees() + (90 if h > w else 0)) % 180
                if h != w
                else 0
            )
            expected[kind].append((x, y, min(w, h), max(w, h), angle))
            if ref in {"U2", "U5", "U6", "U8"}:
                require(
                    pad.GetNetname() == "GND" and w == h == 0.2,
                    "Unexpected exposed-pad drill",
                )
                thermals.append((ref, pad.GetNumber(), x, -y, w))
    require(
        Counter(row[0] for row in thermals) == {"U2": 12, "U5": 16, "U6": 16, "U8": 6},
        "Thermal-hole counts differ from the Rev A process specification",
    )
    for kind, native in expected.items():
        observed = read_drill(next(cam.glob("*-" + kind + ".drl")))

        def rounded(rows):
            return Counter(tuple(round(n, 3) for n in row) for row in rows)

        require(
            rounded(observed) == rounded(native),
            kind + " drill geometry differs from CAD",
        )
    write_csv(
        fabrication / "fill-and-cap.csv",
        ["Reference", "Pad", "Gerber_X_mm", "Gerber_Y_mm", "Drill_mm"],
        sorted(thermals),
    )
    write_csv(
        out / "probe-points.csv",
        ["Reference", "Net", "Side", "CAD_X_mm", "CAD_Y_down_mm"],
        sorted(probes, key=lambda row: ref_key(row[0])),
    )
    return {
        "PTH_including_slots": len(expected["PTH"]),
        "NPTH": len(expected["NPTH"]),
        "plated_slots": sum(w != h for _, _, w, h, _ in expected["PTH"]),
        "filled_and_capped": len(thermals),
        "test_pads": len(probes),
    }


def check_paste(board, path):
    """Compare KiCad's plotted flashes with native paste land shapes at 1 µm."""
    text = path.read_text()
    require(
        "%MOMM*%" in text and "%FSLAX46Y46*%" in text and "G36*" not in text,
        "Unsupported stencil format",
    )
    apertures = {}
    for num, kind, args in re.findall(r"%ADD(\d+)(RoundRect|R|C|O),([^*]+)\*%", text):
        a = list(map(float, args.split("X")))
        if kind == "RoundRect":
            r = a[0]
            xs, ys = a[1:9:2], a[2:9:2]
            w, h = max(xs) - min(xs) + 2 * r, max(ys) - min(ys) + 2 * r
        else:
            w, h = a[0], a[0] if kind == "C" else a[1]
            r = min(w, h) / 2 if kind in {"C", "O"} else 0
        apertures[num] = (w, h, r)
    observed, expected = [], []
    for line in text.splitlines():
        m = re.fullmatch(r"D(\d+)\*", line)
        if m:
            tool = m[1]
        if line.endswith("D03*"):
            m = re.fullmatch(r"X(-?\d+)Y(-?\d+)D03\*", line)
            require(m, "Unsupported paste flash")
            observed.append((int(m[1]) / 1e6, -int(m[2]) / 1e6, *apertures[tool]))
    for f in board.GetFootprints():
        for pad in f.Pads():
            if not pad.IsOnLayer(pcb.F_Paste):
                continue
            a = pad.GetOrientation().AsDegrees() % 180
            require(
                min(abs(a - n) for n in (0, 90, 180)) < 0.00001,
                "Non-orthogonal paste aperture",
            )
            w, h = pcb.ToMM(pad.GetSize().x), pcb.ToMM(pad.GetSize().y)
            r = (
                pcb.ToMM(pad.GetRoundRectCornerRadius())
                if pad.GetShape() == pcb.PAD_SHAPE_ROUNDRECT
                else 0
            )
            if pad.GetShape() in (pcb.PAD_SHAPE_CIRCLE, pcb.PAD_SHAPE_OVAL):
                r = min(w, h) / 2
            if abs(a - 90) < 0.00001:
                w, h = h, w
            expected.append((*xy(pad), w, h, r))

    def shapes(rows):
        return Counter(tuple(round(v, 3) for v in row) for row in rows)

    require(
        shapes(observed) == shapes(expected), "Stencil apertures differ from native CAD"
    )
    return len(observed)
