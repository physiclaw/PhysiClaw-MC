"""Generate board inspection drawings from the checked KiCad and CAM data."""

import csv
import math
import re
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

from board_data import read_drill, require
from kicad_board import children, rotate, values


SVG = "{http://www.w3.org/2000/svg}"
PAPER = "#f8fafc"
TEXT = "#172438"
COPPER_COLOURS = {
    "F.Cu": "#a23443",
    "In1.Cu": "#315783",
    "In2.Cu": "#89591c",
    "B.Cu": "#1b6b61",
}
LABEL_OFFSETS = sorted(
    ((i*.2, j*.2) for i in range(-22, 23) for j in range(-22, 23)),
    key=lambda point: point[0]**2 + point[1]**2,
)


def draw(parent, tag, **attributes):
    return ET.SubElement(parent, SVG + tag, {
        name.replace("_", "-"): str(value) for name, value in attributes.items()
    })


def text(parent, x, y, message, *, size=1.6, colour=TEXT, **attributes):
    draw(parent, "text", x=x, y=y, fill=colour, font_size=size,
         **attributes).text = message


def boxes_overlap(first, second, margin=0):
    a, b, c, d = first
    u, v, q, r = second
    return a-margin < q and c+margin > u and b-margin < r and d+margin > v


def lines_intersect(first, second):
    def side(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])

    a, b = first
    c, d = second
    for axis in (0, 1):
        first_min, first_max = sorted((a[axis], b[axis]))
        second_min, second_max = sorted((c[axis], d[axis]))
        if first_max < second_min or second_max < first_min:
            return False
    return side(a, b, c)*side(a, b, d) <= 0 and side(c, d, a)*side(c, d, b) <= 0


def line_intersects_box(line, box):
    a, b, c, d = box
    corners = ((a,b), (c,b), (c,d), (a,d))
    return (any(a <= x <= c and b <= y <= d for x, y in line)
            or any(lines_intersect(line, edge)
                   for edge in zip(corners, corners[1:]+corners[:1])))


def place_labels(panel, anchors, bounds, *, size, clearance, spacing,
                 artwork, leader_obstacles=None):
    """Place captions near their anchors with clearance from the supplied artwork."""
    left, top, width, height = bounds
    right, bottom = left+width, top+height
    leader_obstacles = leader_obstacles or {}
    placed = []
    placed_lines = []
    leaders = draw(panel, "g", stroke="#64748b", stroke_width=size * .1)
    labels = draw(panel, "g", font_weight="bold")
    occupied = [(x-clearance, y-clearance, x+clearance, y+clearance)
                for x, y, _ in anchors]

    layouts = []
    for x, y, label in anchors:
        w = size * (.70 * len(label) + .26 + .2*label.count("W"))
        h = size * 1.24
        nearby_bounds = x-6, y-6, x+6, y+6
        nearby = [box for box in artwork if boxes_overlap(box, nearby_bounds)]
        # Only anchors within reach of this label's candidate grid can block it.
        reach_x, reach_y = 4.4+w/2, 4.4+h/2
        extent = x-reach_x, y-reach_y, x+reach_x, y+reach_y
        anchor_boxes = [box for box in occupied if boxes_overlap(extent, box, spacing)]
        choices = []
        for dx, dy in LABEL_OFFSETS:
            a, b = x+dx-w/2, y+dy-h/2
            c, d = a+w, b+h
            box = a, b, c, d
            if not (left <= a and c <= right and top <= b and d <= bottom):
                continue
            if any(boxes_overlap(box, previous, spacing) for previous in anchor_boxes):
                continue
            if any(boxes_overlap(box, stroke) for stroke in nearby):
                continue
            choices.append(box)
        close = sum((a+w/2-x)**2 + (b+h/2-y)**2 < 6 for a, b, _, _ in choices)
        priority = (len(choices), close)
        layouts.append((priority, x, y, label, choices))

    # Place the most constrained label first. Break ties using the close candidates.
    layouts.sort(key=lambda layout: layout[0])
    for _, x, y, label, choices in layouts:
        # A pad callout may leave its own trace and marker.
        obstacles = (*leader_obstacles.get(label, ()), *occupied)
        blocked = [(a, b, c, d) for a, b, c, d in obstacles
                   if not (a <= x <= c and b <= y <= d)]
        blocked.extend(placed)
        for box in choices:
            a, b, c, d = box
            if any(boxes_overlap(box, previous, spacing) for previous in placed):
                continue
            end = min(max(x,a),c), min(max(y,b),d)
            line = (x, y), end
            if (
                any(line_intersects_box(line, obstacle) for obstacle in blocked)
                or any(lines_intersect(line, prior) or line_intersects_box(prior, box)
                       for prior in placed_lines)
            ):
                continue
            break
        else:
            raise ValueError(f"Could not place review label {label}")
        placed.append(box)
        placed_lines.append(line)
        draw(leaders, "line", x1=x, y1=y, x2=end[0], y2=end[1])
        draw(leaders, "circle", cx=x, cy=y, r=size*.12, fill="#64748b")
        item = draw(labels, "g", data_label=label, data_anchor=f"{x:g} {y:g}",
                    data_box=f"{a:.6f} {b:.6f} {c:.6f} {d:.6f}")
        text(item, (a+c)/2, b+size*.97, label, size=size, text_anchor="middle")


def component_anchors(board, bounds):
    x0, y0, _, _ = bounds
    return [(f.xy[0]-x0, f.xy[1]-y0, f.ref) for f in board.footprints
            if "board_only" not in f.attributes and not f.ref.startswith("TP")]


def sheet(title, detail, width, height):
    ET.register_namespace("", SVG[1:-1])
    svg = ET.Element(SVG + "svg", {
        "width": f"{width:g}mm", "height": f"{height:g}mm",
        "viewBox": f"0 0 {width:g} {height:g}", "font-family": "sans-serif",
    })
    draw(svg, "title").text = title
    draw(svg, "rect", width=width, height=height, fill=PAPER)
    text(svg, 4, 6, title, size=3, font_weight="bold")
    text(svg, 4, 9.5, detail, colour="#475569")
    return svg


def save(svg, path):
    ET.ElementTree(svg).write(path, encoding="utf-8", xml_declaration=True)


def shapes(svg):
    return [node for node in svg if node.tag not in {SVG+"title", SVG+"desc"}]


def board_edges(board):
    return [tuple(values(node, key) for key in ("start", "end"))
            for node in children(board.tree, "gr_line")
            if values(node, "layer") == ["Edge.Cuts"]]


def drill_map(out, cam, vias, edges, bounds, board):
    x0, y0, w, h = bounds
    with vias.open(newline="") as source:
        capped = {(round(float(r["Gerber_X_mm"]), 3),
                   round(-float(r["Gerber_Y_mm"]), 3))
                  for r in csv.DictReader(source)}
    svg = sheet("Drill and slot map", "Top view · Actual drill sizes · Millimetres",
                w+8, h+24)
    panel = draw(svg, "g", transform=f"translate({4-x0} {14-y0})")
    for (x1, y1), (x2, y2) in edges:
        draw(panel, "line", x1=x1, y1=y1, x2=x2, y2=y2,
             stroke="#64748b", stroke_width=.13)
    counts = {}
    slots = 0
    for kind, colour in (("PTH", "#315783"), ("NPTH", "#74479b")):
        holes = read_drill(next(cam.glob(f"*-{kind}.drl")))
        counts[kind] = len(holes)
        for x, y, diameter, length, angle in holes:
            ink = "#a65c13" if kind == "PTH" and (round(x,3), round(y,3)) in capped else colour
            slot = length != diameter
            slots += slot
            hole = draw(panel, "rect", x=x-length/2, y=y-diameter/2,
                        width=length, height=diameter, rx=diameter/2, fill=ink,
                        transform=f"rotate({angle} {x} {y})")
            draw(hole, "title").text = f"{kind} · {diameter:g} × {length:g} mm"
    for footprint in board.footprints:
        if footprint.ref in {"J1", "J2"}:
            slot_pads = [pad for pad in footprint.pads if pad.drill[0] != pad.drill[1]]
            if slot_pads:
                x,y = min((pad.xy for pad in slot_pads), key=lambda p: p[0])
                text(panel, x-1, y-.7, footprint.ref, size=1.25,
                     text_anchor="end", font_weight="bold")
    text(svg, 4, h+20, f"PTH {counts['PTH']} ({slots} slots)", colour="#315783")
    text(svg, 33, h+20, f"NPTH ({counts['NPTH']})", colour="#74479b")
    text(svg, 48, h+20, f"Fill and cap ({len(capped)})", colour="#a65c13")
    save(svg, out / "drill-and-slot-map.svg")


def append_artwork(panel, original, colour=None):
    for element in shapes(original):
        panel.append(element)
        if colour:
            for node in element.iter():
                if style := node.get("style"):
                    node.set("style", style.replace("#000000", colour))


def plot_panel(svg, source, x, y, width, height, viewbox=None, colour=None):
    original = ET.parse(source).getroot()
    panel = draw(svg, "svg", x=x, y=y, width=width, height=height,
                 viewBox=viewbox or original.get("viewBox"))
    append_artwork(panel, original, colour)
    return panel


def artwork_boxes(panel):
    """Reserve space for fabrication strokes, routing, and pad markers."""
    supported_shapes = {SVG+"circle", SVG+"line", SVG+"path"}
    for group in panel:
        for shape in group if group.tag == SVG+"g" else (group,):
            if shape.tag not in supported_shapes:
                continue
            style = shape.get("style", group.get("style", ""))
            stroke = re.search(r"stroke-width:\s*([\d.]+)", style)
            pad = .09 + float(stroke[1] if stroke else shape.get("stroke-width", 0))/2
            if shape.tag == SVG+"circle":
                x, y, radius = (float(shape.get(key)) for key in ("cx", "cy", "r"))
                if shape.get("fill", "none") != "none":
                    reach = radius + pad
                    yield x-reach, y-reach, x+reach, y+reach
                    continue
                samples = max(12, math.ceil(math.tau*radius/.2))
                points = [(x+radius*math.cos(angle), y+radius*math.sin(angle))
                          for angle in (math.tau*i/samples for i in range(samples))]
                points.append(points[0])
            elif shape.tag == SVG+"line":
                points = [tuple(float(shape.get(axis+end)) for axis in ("x", "y"))
                          for end in ("1", "2")]
            else:
                # KiCad emits straight strokes and polygons for these outlines.
                path = shape.get("d")
                coords = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", path)]
                points = list(zip(coords[::2], coords[1::2], strict=True))
                if "Z" in path:
                    points.append(points[0])
                if "fill:none" not in style:
                    xs, ys = zip(*points)
                    yield min(xs)-pad, min(ys)-pad, max(xs)+pad, max(ys)+pad
                    continue
            for (x, y), (u, v) in zip(points, points[1:]):
                steps = math.ceil(max(abs(x-u), abs(y-v))/.18) if x != u and y != v else 1
                for step in range(steps):
                    xs = [x+(u-x)*i/steps for i in (step, step+1)]
                    ys = [y+(v-y)*i/steps for i in (step, step+1)]
                    yield min(xs)-pad, min(ys)-pad, max(xs)+pad, max(ys)+pad


def mounting_pads(board):
    return (pad for footprint in board.footprints for pad in footprint.pads
            if min(pad.drill) >= 3)


def panel_drawing(path, board, bounds):
    """Draw the proposed one-board SMT panel for JLC CAM."""
    x0, y0, width, height = bounds
    scale, rail = 16, 10
    left, top = 128, 120
    panel_height = height + 2 * rail
    right = left + round(width * scale)
    bottom = top + round(panel_height * scale)
    image = Image.new("RGB", (right + 135, bottom + 96), "white")
    pen = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=26)
    ink = "#263840"
    score = "#4b6979"
    copper = "#9b571b"
    board_top = top + rail * scale
    board_bottom = bottom - rail * scale
    pen.rectangle((left, top, right, bottom), fill="#dce4e9")
    pen.rectangle((left, board_top, right, board_bottom), fill="#f4f8f7")
    for footprint in board.footprints:
        for pad in footprint.pads:
            if not pad.on_layer("F.Cu"):
                continue
            x = left + (pad.xy[0] - x0) * scale
            y = board_top + (pad.xy[1] - y0) * scale
            w, h = (v * scale / 2 for v in pad.size)
            corners = [rotate(u, v, pad.angle) for u, v in ((-w,-h), (w,-h), (w,h), (-w,h))]
            if pad.shape == "circle":
                pen.ellipse((x-w, y-h, x+w, y+h), fill="#91a49d")
            else:
                pen.polygon([(x+u, y+v) for u,v in corners], fill="#91a49d")

    for y in (board_top, board_bottom):
        for x in range(left, right, 22):
            pen.line((x, y, min(x + 13, right), y), fill=score, width=3)
    pen.rectangle((left, top, right, bottom), outline=ink, width=3)

    def panel_point(x, y):
        return left + x * scale, top + y * scale

    def rail_circle(centre, diameter, **style):
        cx, cy = centre
        radius = diameter * scale / 2
        pen.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), **style)

    mark_diameter = 1
    mask_diameter = 2
    mark_inset = 3.85
    stagger = 5
    mark_x = 13
    marks = ((mark_x, mark_inset), (width - mark_x, mark_inset),
             (mark_x + stagger, panel_height - mark_inset),
             (width - mark_x, panel_height - mark_inset))
    for x, y in marks:
        centre = panel_point(x, y)
        rail_circle(centre, mask_diameter, fill="#fff7df", outline=copper, width=2)
        rail_circle(centre, mark_diameter, fill=copper)

    hole_diameter = 2
    hole_x = 4
    holes = ((hole_x, rail / 2), (width - hole_x, rail / 2),
             (hole_x, panel_height - rail / 2),
             (width - hole_x - stagger, panel_height - rail / 2))
    for x, y in holes:
        rail_circle(panel_point(x, y), hole_diameter, fill="white", outline=ink, width=2)

    def tick(x, y):
        pen.line((x-5, y+5, x+5, y-5), fill=score, width=2)

    width_y = bottom + 56
    pen.line((left, width_y, right, width_y), fill=score, width=2)
    for x in (left, right):
        pen.line((x, bottom+8, x, width_y+8), fill=score, width=2)
        tick(x, width_y)
    pen.text(((left+right)/2, width_y-19), f"{width:g}", anchor="mm", fill=ink, font=font)

    overall_x = left - 44
    pen.line((overall_x, top, overall_x, bottom), fill=score, width=2)
    for y in (top, bottom):
        pen.line((overall_x-8, y, left-8, y), fill=score, width=2)
        tick(overall_x, y)
    pen.text((overall_x-13, (top+bottom)/2), f"{panel_height:g}", anchor="rm", fill=ink, font=font)

    chain_x = right + 44
    pen.line((chain_x, top, chain_x, bottom), fill=score, width=2)
    edges = (top, board_top, board_bottom, bottom)
    for y in edges:
        pen.line((right+8, y, chain_x+8, y), fill=score, width=2)
        tick(chain_x, y)
    for start, end, dimension in zip(edges, edges[1:], (rail, height, rail)):
        pen.text((chain_x+13, (start+end)/2), f"{dimension:g}", anchor="lm", fill=ink, font=font)

    image.save(path, quality=94, subsampling=0)


def component_reference(out, board, bounds, fab, board_name, version):
    """Draw the component references in the routing views' board orientation."""
    x0, y0, width, height = bounds
    svg = sheet("Component reference", f"{board_name} · {version} · Top view",
                width+10, height+18)
    panel = plot_panel(svg, fab, 3, 12, width+4, height+2,
                       f"-1 -1 {width+4:g} {height+2:g}", "#8a97a8")
    for pad in mounting_pads(board):
        x, y = pad.xy
        draw(panel, "circle", cx=x-x0, cy=y-y0, r=pad.drill[0]/2,
             fill="none", stroke="#8a97a8", stroke_width=.13)

    place_labels(panel, component_anchors(board, bounds),
                 (.35, .35, width-.7, height-.7),
                 size=1.04, clearance=.19, spacing=.12,
                 artwork=list(artwork_boxes(panel)))
    save(svg, out/"component-reference.svg")


def mask_and_paste(out, pcb, work, board, bounds, plot):
    detail_rows = (("U7", 77), ("U8", 110))
    paste_colour = "#74479b"
    top_colour = COPPER_COLOURS["F.Cu"]
    detail_columns = (("F.Paste", 80, "Paste", paste_colour),
                      ("F.Mask", 113, "Mask", top_colour))
    detail_pcb = work / "aperture-detail.kicad_pcb"
    board.write_aperture_view(detail_pcb, {ref for ref, _ in detail_rows})
    svg = sheet("Solder mask and paste",
                "All panels use the top-view orientation · Colored areas are openings",
                158, 141)
    for layer, label, x, y, colour in (
        ("F.Mask", "Top solder mask", 4, 16, top_colour),
        ("B.Mask", "Bottom solder mask", 80, 16, COPPER_COLOURS["B.Cu"]),
        ("F.Paste", "Top paste stencil", 4, 73, paste_colour),
    ):
        path = work / f"{layer}.svg"
        plot(pcb, layer, path)
        text(svg, x, y, label, font_weight="bold")
        plot_panel(svg, path, x, y+2, 70, 50, colour=colour)
    detail_plots = {layer: work / f"detail-{layer}.svg" for layer, *_ in detail_columns}
    for layer, path in detail_plots.items():
        plot(detail_pcb, layer, path)

    x0, y0, _, _ = bounds
    positions = {footprint.ref: footprint.xy for footprint in board.footprints}
    for ref, y in detail_rows:
        cx, cy = positions[ref]
        text(svg, 80, y, f"{ref} aperture detail · 7 × 6 mm", font_weight="bold")
        viewbox = f"{cx-x0-3.5:g} {cy-y0-3:g} 7 6"
        for layer, x, _, colour in detail_columns:
            plot_panel(svg, detail_plots[layer], x, y+2, 28, 24, viewbox, colour)
    for _, x, heading, colour in detail_columns:
        text(svg, x, 72, heading, colour=colour)
    save(svg, out / "mask-and-paste.svg")


def board_bounds(edges):
    points = [point for edge in edges for point in edge]
    xs, ys = zip(*points)
    return min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys)


def usb_review(out, board, bounds, fab):
    pair = re.compile(r"USB_D[PM](?:_ESD|_CONN)?$")
    def is_usb(net):
        return bool(pair.fullmatch(net))
    segments = [s for s in children(board.tree, "segment")
                if is_usb(values(s, "net", [""])[0])]
    vias = [v for v in children(board.tree, "via")
            if is_usb(values(v, "net", [""])[0])]
    arcs = [a for a in children(board.tree, "arc")
            if is_usb(values(a, "net", [""])[0])]
    require(not arcs, "USB review expects straight trace segments")
    require(segments, "USB review found no differential pair")
    require(all(values(s, "layer")[0] in COPPER_COLOURS for s in segments),
            "USB review encountered an unknown copper layer")
    pads = [(f.ref, p) for f in board.footprints for p in f.pads if is_usb(p.net)]
    usb_refs = {ref for ref, _ in pads}
    anchors = [(*f.xy, f.ref) for f in board.footprints if f.ref in usb_refs]
    coords = ([values(s, k) for s in segments for k in ("start","end")]
              + [p.xy for _, p in pads] + [values(v, "at") for v in vias]
              + [(x, y) for x, y, _ in anchors])
    xs, ys = zip(*coords)
    left, top = min(xs)-1.6, min(ys)-1.6
    width, height = max(xs)-left+1.6, max(ys)-top+1.6
    pw = 68
    ph = pw * height / width
    svg = sheet("USB differential pair", "Top view · L1 red · L4 teal",
                pw+8, ph+17.5)
    panel = draw(svg, "svg", x=4, y=13.5, width=pw, height=ph,
                 viewBox=f"{left} {top} {width} {height}")
    x0, y0, _, _ = bounds
    backdrop = draw(panel, "g", transform=f"translate({x0} {y0})", opacity=".22")
    append_artwork(backdrop, ET.parse(fab).getroot())
    trace_boxes = []
    for node in segments:
        x1,y1 = values(node,"start")
        x2,y2 = values(node,"end")
        layer, = values(node,"layer")
        line = draw(panel, "line", x1=x1, y1=y1, x2=x2, y2=y2,
                    stroke=COPPER_COLOURS[layer], stroke_width=values(node,"width")[0],
                    stroke_linecap="round")
        net, = values(node, "net")
        draw(line, "title").text = f"{net} · {layer}"
        trace_boxes.extend((net, box) for box in artwork_boxes((line,)))
    for node in vias:
        x,y = values(node,"at")
        draw(panel, "circle", cx=x, cy=y, r=values(node,"size")[0]/2,
             fill=PAPER, stroke=TEXT, stroke_width=.08)
    contacts = list(artwork_boxes(panel.findall(SVG+"circle")))
    pin_nets = {}
    for ref, pad in pads:
        x, y = pad.xy
        w, h = pad.size
        layer = "F.Cu" if pad.on_layer("F.Cu") else "B.Cu"
        require(pad.shape in {"rect", "roundrect", "circle", "oval"},
                f"USB review cannot plot {ref}.{pad.number} pad shape {pad.shape}")
        node = draw(panel, "rect", x=x-w/2, y=y-h/2, width=w, height=h,
                    rx=pad.radius, fill=COPPER_COLOURS[layer],
                    transform=f"rotate({-pad.angle:g} {x} {y})")
        draw(node, "title").text = f"{ref}.{pad.number} · {pad.net}"
        corners = [rotate(u, v, pad.angle) for u in (-w/2, w/2) for v in (-h/2, h/2)]
        xs, ys = zip(*corners)
        contacts.append((x+min(xs)-.09, y+min(ys)-.09, x+max(xs)+.09, y+max(ys)+.09))
        if ref == "J2" and pad.number in {"B6", "B7"}:
            # Label the outer contacts of the four-pin row.
            pin_y = y + (min(ys) if pad.number == "B6" else max(ys))
            label = "D+" if pad.net.startswith("USB_DP") else "D−"
            anchors.append((x, pin_y, label))
            pin_nets[label] = pad.net
    fabrication_boxes = [(a+x0, b+y0, c+x0, d+y0)
                         for a, b, c, d in artwork_boxes(backdrop)]
    leader_regions = {
        label: (*contacts, *(box for net, box in trace_boxes if net != pin_nets.get(label)))
        for _, _, label in anchors
    }
    place_labels(panel, anchors, (left, top, width, height),
                 size=.44, clearance=.12, spacing=.08,
                 artwork=(*fabrication_boxes, *contacts, *(box for _, box in trace_boxes)),
                 leader_obstacles=leader_regions)
    save(svg, out/"usb-routing.svg")


def probe_map(out, csv_path, bounds, fab, board):
    x0,y0,w,h = bounds
    with csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    svg = sheet("Probe locations", "Board sides as viewed from above and below",
                2*w+16,h+48)
    mounting_holes = list(mounting_pads(board))
    for side, x in (("Top",4),("Bottom",w+12)):
        text(svg,x,15,side,font_weight="bold")
        draw(svg,"rect",x=x,y=17,width=w,height=h,fill="#eef2f6",
             stroke="#64748b",stroke_width=.12)
        panel = draw(svg,"svg",x=x,y=17,width=w,height=h,viewBox=f"0 0 {w} {h}")
        outlines = []
        if side == "Top":
            group = draw(panel,"g",opacity=.18)
            append_artwork(group, ET.parse(fab).getroot())
            outlines.extend(artwork_boxes(group))
        for pad in mounting_holes:
            px, py = pad.xy
            cx = px-x0 if side == "Top" else w-(px-x0)
            draw(panel, "circle", cx=cx, cy=py-y0, r=min(pad.drill)/2,
                 fill=PAPER, stroke="#94a3b8", stroke_width=.13)
        entries = [row for row in rows if row["Side"] == side]
        anchors = []
        for i,row in enumerate(entries):
            px = float(row["CAD_X_mm"])-x0
            py = float(row["CAD_Y_down_mm"])-y0
            if side == "Bottom":
                px = w-px
            anchors.append((px, py, row["Reference"]))
            text(svg,x+(i//7)*33,h+21+(i%7)*3,
                 f"{row['Reference']}  {row['Net']}",size=1.45)
        outlines.extend(artwork_boxes(panel))
        place_labels(panel, anchors, (0, 0, w, h), size=.98, clearance=.36,
                     spacing=.12, artwork=outlines)
        for px, py, _ in anchors:
            draw(panel,"circle",cx=px,cy=py,r=.32,fill="#a23443",
                 stroke="#fff",stroke_width=.1)
    save(svg,out/"probe-map.svg")
