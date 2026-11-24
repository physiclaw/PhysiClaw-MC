"""Build the assembly tables and verify v1.0's plotted manufacturing geometry."""

import csv
import math
import re
from collections import Counter, defaultdict
import xml.etree.ElementTree as ET


THERMAL_DRILL_MM = 0.32


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


def pad_center(footprint, number):
    points = [p.xy for p in footprint.pads if p.number == number and p.on_layer("F.Cu")]
    require(points, f"{footprint.ref} has no copper pad {number}")
    # SW1 uses two lands per electrical terminal. Their midpoint identifies the row.
    return tuple(sum(axis) / len(points) for axis in zip(*points))


def placement(footprint, part, row):
    ref = footprint.ref
    x, y = footprint.xy
    native = footprint.angle
    require(
        row["Side"] == "top"
        and footprint.layer == "F.Cu"
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


def assembly(board, netlist, native_positions, package_table, out, *, bom_path, cpl_path):
    parts = {
        f.ref: f
        for f in board.footprints
        if not f.attributes.intersection({"board_only", "dnp"})
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
    smt = {r for r, f in parts.items() if "smd" in f.attributes}
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
        land = f.land
        require(
            all(f.fields[k] == fields[k] for k in ("MPN", "LCSC"))
            and f.fields.get("Manufacturer", "") == (fields.get("Manufacturer") or "")
            and f.fields.get("Datasheet", "") == c.findtext("datasheet", "")
            and f.fields["Value"] == c.findtext("value")
            and land == c.findtext("footprint"),
            "PCB/schematic identity mismatch at " + ref,
        )
        part = names[code]
        require(
            part["MPN"] == mpn and part["KiCad footprint"] == land.split(":", 1)[1],
            "Catalog identity or footprint mismatch at " + ref,
        )
        if ref in smt:
            cpl, evidence = placement(f, part, native[ref])
            placements.append(cpl)
            audit.append(evidence)
        process = "SMT" if ref in smt else "THT"
        require(
            process == "SMT" or "through_hole" in f.attributes,
            "Undefined assembly process at " + ref,
        )
        grouped[(process, mpn, code, part["Package"])].append(ref)
        lines.append((ref, mpn, code, f.fields["Value"], land, process))
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
        cpl_path,
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
            bom_path if process == "SMT" else out / "tht-bom.csv",
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
    text = path.read_text(encoding="utf-8")
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


def write_via_fill_layer(path, holes):
    lines = [
        "G04 IPC-4761 Type VII - epoxy resin fill and copper cap both sides*",
        "G04 Preserve the supplied solder mask layers*",
        "%TF.SameCoordinates,Original*%",
        "%TF.FileFunction,Viafill*%",
        "%TF.FilePolarity,Positive*%",
        "%FSLAX46Y46*%",
        "%MOMM*%",
    ]
    by_drill = defaultdict(list)
    for _, _, x, y, diameter in holes:
        by_drill[diameter].append((x, y))
    apertures = list(enumerate(sorted(by_drill), start=10))
    for code, diameter in apertures:
        lines.append(f"%ADD{code}C,{diameter:.3f}*%")
    lines.append("%LPD*%")
    for code, diameter in apertures:
        lines.append(f"D{code}*")
        lines.extend(
            f"X{round(x * 1_000_000)}Y{round(y * 1_000_000)}D03*"
            for x, y in by_drill[diameter]
        )
    lines.append("M02*")
    path.write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def geometry(board, cam, fill_and_cap, out):
    expected = {
        "PTH": [(x, y, drill, drill, 0) for x, y, drill in board.vias],
        "NPTH": [],
    }
    thermal_counts = {"U2": 12, "U5": 16, "U6": 16}
    require(not board.capped_vias, "Only the footprint thermal holes may be filled and capped")
    thermals, probes = [], []
    for f in board.footprints:
        ref = f.ref
        for pad in f.pads:
            x, y = pad.xy
            if ref.startswith("TP"):
                probes.append(
                    (
                        ref,
                        pad.net,
                        "Top" if pad.on_layer("F.Cu") else "Bottom",
                        x,
                        y,
                    )
                )
            w, h = pad.drill
            if not w:
                continue
            kind = "NPTH" if pad.kind == "np_thru_hole" else "PTH"
            diameter, length = sorted(pad.drill)
            if kind == "PTH" and length != diameter:
                require(
                    length >= 2 * diameter,
                    f"{ref}.{pad.number}: JLC plated slot length must be at least twice its width",
                )
            angle = (pad.angle + (90 if h > w else 0)) % 180 if h != w else 0
            expected[kind].append((x, y, diameter, length, angle))
            if ref in thermal_counts:
                require(
                    kind == "PTH" and pad.net == "GND" and w == h == THERMAL_DRILL_MM,
                    "Unexpected exposed-pad drill",
                )
                thermals.append((ref, pad.number, x, -y, w))
    require(
        Counter(row[0] for row in thermals) == thermal_counts,
        "Thermal-hole counts differ from the v1.0 process specification",
    )
    observed = {
        kind: read_drill(next(cam.glob(f"*-{kind}.drl"))) for kind in expected
    }
    require(
        sum(row[2] == THERMAL_DRILL_MM for drills in observed.values() for row in drills)
        == len(thermals),
        "The 0.32 mm drill is reserved for the filled and capped thermal holes",
    )

    def rounded(rows):
        return Counter(tuple(round(n, 3) for n in row) for row in rows)

    for kind, native in expected.items():
        require(
            rounded(observed[kind]) == rounded(native),
            kind + " drill geometry differs from CAD",
        )
    holes = sorted(thermals)
    fill_drills = Counter((x, -y, d, d, 0) for _, _, x, y, d in holes)
    plated_drills = Counter(observed["PTH"])
    require(
        all(count == plated_drills[drill] == 1 for drill, count in fill_drills.items()),
        "Via-fill locations must match unique plated drills",
    )
    write_csv(
        fill_and_cap,
        ["Reference", "Pad", "Gerber_X_mm", "Gerber_Y_mm", "Drill_mm"],
        holes,
    )
    write_via_fill_layer(cam / "sk.gbr", holes)
    write_csv(
        out / "probe-points.csv",
        ["Reference", "Net", "Side", "CAD_X_mm", "CAD_Y_down_mm"],
        sorted(probes, key=lambda row: ref_key(row[0])),
    )
    return {
        "PTH_including_slots": len(expected["PTH"]),
        "NPTH": len(expected["NPTH"]),
        "plated_slots": sum(w != h for _, _, w, h, _ in expected["PTH"]),
        "filled_and_capped": len(holes),
        "test_pads": len(probes),
    }


def check_paste(board, path):
    """Compare KiCad's plotted flashes with native paste land shapes at 1 µm."""
    text = path.read_text(encoding="utf-8")
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
    for f in board.footprints:
        for pad in f.pads:
            if not pad.on_layer("F.Paste"):
                continue
            a = pad.angle % 180
            require(
                min(abs(a - n) for n in (0, 90, 180)) < 0.00001,
                "Non-orthogonal paste aperture",
            )
            require(
                pad.shape in {"rect", "roundrect", "circle", "oval"},
                "Unsupported paste shape: " + pad.shape,
            )
            w, h = pad.size
            r = pad.radius
            if abs(a - 90) < 0.00001:
                w, h = h, w
            expected.append((*pad.xy, w, h, r))

    def shapes(rows):
        return Counter(tuple(round(v, 3) for v in row) for row in rows)

    require(
        shapes(observed) == shapes(expected), "Stencil apertures differ from native CAD"
    )
    return len(observed)
