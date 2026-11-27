"""Refresh the PCB guide's illustrations and review assets after make build."""
import csv
import heapq
import json
import math
import re
import os
import subprocess
import tempfile
import shutil
import unicodedata
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

from build import digest, kicad_environment
from board_data import pad_center
from guide_ic import CARDS, TRANSISTOR_CARDS
from guide_zones import SCHEMATICS, ZONES
from inspection_views import SVG, board_bounds, board_edges, draw, save
from kicad_board import Board, children, loads, rotate, values


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
GUIDE = ROOT / "docs/pcb-guide"
ASSETS = GUIDE / "assets"
INK, SOFT, LINE = "#183c39", "#4b6666", "#cbd8d5"
PALETTE = ["#0b6782", "#ad531b", "#7244a2", "#326a37", "#973e68"]
FONT = "'PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif"
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',monospace"
# Offset crowded labels in drawing units. Zoom views stay centred on the footprints.
LABEL_OFFSETS = {"C7": (20, 0), "R3": (-20, 0), "R28": (-20, -8), "R11": (20, 0),
                 "C11": (-24, 0), "R13": (20, 5)}
XLINK = "{http://www.w3.org/1999/xlink}"
ET.register_namespace("", SVG[1:-1])
ET.register_namespace("xlink", XLINK[1:-1])


def label(parent, x, y, content, size=16, colour=INK, **attrs):
    draw(parent, "text", x=x, y=y, font_size=size, fill=colour, **attrs).text = content


def line(parent, x1, y1, x2, y2, colour, width=1):
    draw(parent, "line", x1=x1, y1=y1, x2=x2, y2=y2, stroke=colour, stroke_width=width)


def panel(parent, x, y, w, h, fill="white", stroke=LINE, radius=0):
    return draw(parent, "rect", x=x, y=y, width=w, height=h, fill=fill, stroke=stroke, rx=radius)


def use(parent, name, **attrs):
    node = draw(parent, "use", **attrs)
    node.set(XLINK + "href", "#" + name)
    return node


# These are functional symbols. The annotated paths below carry PCB pad numbers.
GLYPHS = {
    "rail": "M-18 0H-9m0 -5V5m5 -8V8m4 -5V3m0 -3H18",
    "jack": "M-17 -7H0V-11H10V11H0V7H-17ZM-10 0H5",
    "fuse": "M-18 0H-11M-11 -5H11V5H-11ZM-11 0H18",
    "switch": "M-18 3H-10m2 0 14 -10M9 3H18",
    "resistor": "M-18 0H-12M-12 -4.5H12V4.5H-12ZM12 0H18",
    "inductor": "M-18 3H-14q0 -12 7 0q0 -12 7 0q0 -12 7 0q0 -12 7 0H18",
    "coil": "M-18 3H-14q0 -12 7 0q0 -12 7 0q0 -12 7 0q0 -12 7 0H18M-13 -7H13",
    "ground": "M0 -10V1M-12 1H12M-8 5H8M-4 9H4",
    "diode": "M-18 0H-8M-8 -7L6 0L-8 7ZM6 -8V8M6 0H18",
    "clamp": "M-18 0H-7M-7 -7L6 0L-7 7ZM2 -10L6 -7V7L10 10M6 0H18",
    "led": "M-16 4H-8M-8 -2L3 4L-8 10ZM3 -3V10M3 4H16M2 -5l5 -5m-3 0h3v3m2 3 5 -5m-3 0h3v3",
    "chip": "M-11 -7H11V7H-11ZM-7 -10V-7M0 -10V-7M7 -10V-7M-7 7V10M0 7V10M7 7V10M-6 0H6",
    "pulse": "M-17 6H-10V-6H-2V6H6V-6H14V6H18",
    "io": "M-16 0H-9M-9 -6H6L12 0L6 6H-9ZM12 0H17",
    "bridge": "M-11 -10V10M11 -10V10M-11 0H11M-15 -6l8 -5M7 11l8 -5",
    "nand": "M-16 -5H-9m-7 10H-9M-9 -8H0a8 8 0 0 1 0 16H-9ZM11 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0M15 0H19",
    "buffer": "M-18 0H-9M-9 -9L10 0L-9 9ZM10 0H18",
    "load": "M-18 0H-10M-10 -6H10V6H-10ZM10 0H18",
}


class Copper:
    """Find the actual outer-layer segments between two specified lands."""
    def __init__(self, board):
        self.origin = board_bounds(board_edges(board))[:2]
        self.parts = {f.ref: f for f in board.footprints}
        self.graphs = defaultdict(lambda: defaultdict(list))
        for item in children(board.tree, "segment"):
            layer, = values(item, "layer")
            if layer in ("F.Cu", "B.Cu"):
                self.connect(item, (layer, *values(item, "start")), (layer, *values(item, "end")))
        for item in children(board.tree, "via"):
            xy = values(item, "at")
            self.connect(item, ("F.Cu", *xy), ("B.Cu", *xy))

    def connect(self, item, a, b):
        graph = self.graphs[values(item, "net")[0]]
        graph[a].append(b)
        graph[b].append(a)

    def local(self, xy):
        return tuple(round(v - o, 6) for v, o in zip(xy, self.origin))

    def pad(self, spec):
        ref, pin = spec.split(".")
        return next(p for p in self.parts[ref].pads if p.number == pin)

    def path(self, spec):
        start, direction, end = spec.split()
        a, b = self.pad(start), self.pad(end)
        if not a.net or a.net != b.net:
            raise ValueError(f"Different nets in {spec}")
        graph = self.graphs[a.net]
        # Through-hole connectors may be reached on either outer layer.
        starts = {n for n in graph if a.on_layer(n[0]) and a.edge_distance(n[1:]) <= 1e-6}
        ends = {n for n in graph if b.on_layer(n[0]) and b.edge_distance(n[1:]) <= 1e-6}
        queue = [(math.dist(n[1:], a.xy), n) for n in starts]
        heapq.heapify(queue)
        prev = dict.fromkeys(starts)
        dist = {n: d for d, n in queue}
        while queue:
            d, node = heapq.heappop(queue)
            if node in ends:
                path = []
                while node is not None:
                    path.append((node[0], self.local(node[1:])))
                    node = prev[node]
                return a.net, direction == "<>", list(reversed(path))
            if d != dist[node]:
                continue
            for peer in graph[node]:
                new = d + math.dist(node[1:], peer[1:])
                if new < dist.get(peer, math.inf):
                    prev[peer], dist[peer] = node, new
                    heapq.heappush(queue, (new, peer))
        raise ValueError(f"No routed connection for {spec} on {a.net}")


def width_units(s):
    return sum(1 if unicodedata.east_asian_width(c) in "FW" else .59 for c in s)


def wrap(s, limit):
    rows, row = [], ""
    for token in re.findall(r"[A-Za-z0-9.%µΩ°/±−+–≥≤_-]+|.", s):
        if row and width_units(row + token) > limit and token not in "，。；、）：":
            rows.append(row.rstrip())
            row = ""
        row += token if row else token.lstrip()
    return [*rows, row]


def hit(rect, point):
    x, y, r, b = rect
    return x <= point[0] <= r and y <= point[1] <= b


def define_routing(svg, source):
    defs = draw(svg, "defs")
    copper = draw(defs, "g", id="routing")
    # Source masks and footprint outlines stay in their original KiCad coordinate space.
    for child in source:
        if child.tag == SVG + "defs":
            defs.extend(child)
        elif ((child.tag == SVG + "rect" and child.get("mask"))
              or (child.tag == SVG + "g" and child.get("opacity"))):
            copper.append(child)
    return defs


def define_artwork(svg, source):
    defs = define_routing(svg, source)
    for shape, d in GLYPHS.items():
        draw(defs, "path", id="glyph-" + shape, d=d, fill="none", stroke_width=1.8,
             stroke_linecap="round", stroke_linejoin="round")


def draw_flow(svg, flow, i, x, y, row_h):
    colour = PALETTE[i]
    w = 605
    panel(svg, x, y + 2, 22, 22, colour, colour, 5)
    label(svg, x + 11, y + 18, chr(65 + i), 14, "white", text_anchor="middle", font_weight=700)
    label(svg, x + 32, y + 19, flow.title, 19, font_weight=650)
    stages = re.split(r" ([→⇄]) ", flow.stages)
    nodes, arrows = stages[::2], stages[1::2]
    pitch = w / len(nodes)
    for n, node in enumerate(nodes):
        glyph, name = node.split(":", 1)
        cx, cy = x + (n + .5) * pitch, y + 47
        use(svg, "glyph-" + glyph, transform=f"translate({cx} {cy})", stroke=colour)
        label(svg, cx, cy + 25, name, 15, text_anchor="middle", font_weight=600)
        if n < len(arrows):
            x1, x2 = cx + 26, cx + pitch - 26
            line(svg, x1, cy, x2, cy, colour, 1.65)
            draw(svg, "path", d=f"M{x2-5} {cy-3.5}l5 3.5 -5 3.5", fill="none", stroke=colour, stroke_width=1.65)
            if arrows[n] == "⇄":
                draw(svg, "path", d=f"M{x1+5} {cy-3.5}l-5 3.5 5 3.5", fill="none", stroke=colour, stroke_width=1.65)
    for n, row in enumerate(wrap(flow.note, 41)):
        label(svg, x, y + 96 + 20*n, row, 14, SOFT)
    line(svg, x, y + row_h - 9, x+w, y + row_h - 9, LINE)


def arrow(svg, x, y, angle, colour):
    g = draw(svg, "g", transform=f"translate({x:.2f} {y:.2f}) rotate({angle:.2f})")
    draw(g, "path", d="M-4 -4L1.5 0L-4 4", fill="none", stroke="white", stroke_width=4.4)
    draw(g, "path", d="M-4 -4L1.5 0L-4 4", fill="none", stroke=colour, stroke_width=2.4)


def trace(svg, route, project, bounds, colour):
    net, both, points = route
    g = draw(svg, "g", data_net=net)
    segments = []
    for (la, a), (lb, b) in zip(points, points[1:]):
        if la != lb:
            continue
        p, q = project(a), project(b)
        line(g, *p, *q, "white", 6.2)
        segments.append((la, p, q))
    for layer, p, q in segments:
        seg = draw(g, "line", x1=p[0], y1=p[1], x2=q[0], y2=q[1],
                   stroke=colour, stroke_width=3.8, stroke_linecap="round")
        if layer == "B.Cu":
            seg.set("stroke-dasharray", "5 3")
    # Show direction on the longest visible portion, including cropped off-sheet nets.
    # Liang–Barsky clipping keeps the arrow inside the inset even when both ends lie outside.
    visible = []
    for _, p, q in segments:
        dx, dy = q[0]-p[0], q[1]-p[1]
        lo, hi = 0., 1.
        for value, delta, minimum, maximum in zip(p, (dx, dy), bounds[:2], bounds[2:]):
            if delta:
                a, b = sorted(((minimum-value)/delta, (maximum-value)/delta))
                lo, hi = max(lo, a), min(hi, b)
            elif not minimum <= value <= maximum:
                hi = -1.
        if hi > lo:
            visible.append(((hi-lo)*math.hypot(dx,dy), p, dx, dy, lo, hi))
    if visible:
        length, p, dx, dy, lo, hi = max(visible)
        angle = math.degrees(math.atan2(dy, dx))
        for fraction, rotation in ((.29, 180), (.71, 0)) if both else ((.52, 0),):
            t = lo + (hi-lo)*fraction
            if length >= (12 if both else 5):
                arrow(g, p[0]+dx*t, p[1]+dy*t, angle+rotation, colour)


def layouts(count, x, h):
    """Allocate source crops within one of the two aligned panels."""
    y, w, gap = 175, 628, 8
    if count == 1:
        return [(x, y, w, h)]
    half = (h-gap)/2
    if count == 2:
        return [(x, y, w, h-121), (x, y+h-113, w, 113)]
    if count == 3:
        return [(x, y, 369, h), (x+377, y, 251, half), (x+377, y+half+gap, 251, half)]
    return [(x+i%2*318, y+i//2*(half+gap), 310, half) for i in range(4)]


def focus_view(svg, name, centre, width, bounds):
    x, y, w, h = bounds
    width = min(width, w, h * 1.56)
    height = width / 1.56
    left = min(max(x, centre[0]-width/2), x+w-width)
    top = min(max(y, centre[1]-height/2), y+h-height)
    draw(svg, "view", id=name, viewBox=f"{left:.3f} {top:.3f} {width:.3f} {height:.3f}")


def schematic_sources():
    project = ROOT / "pcb/kicad"
    pages = {}
    cli = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
    if not cli:
        cli = next((p for p in (Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
                    Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "KiCad/10.0/bin/kicad-cli.exe")
                    if p.is_file()), "kicad-cli")
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run([cli, "sch", "export", "svg", "--exclude-drawing-sheet", "--no-background-color",
                        "-o", folder, project/"PCW-MC-01.kicad_sch"],
                       check=True, stdout=subprocess.DEVNULL,
                       env=kicad_environment(shutil.which(str(cli)) or cli, Path(folder)))
        plots = [ET.parse(path).getroot() for path in Path(folder).glob("*.svg")]
        for path in sorted((project / "schematics").glob("*.kicad_sch")):
            page = int(path.name[:2])+1
            symbols = {}
            for node in children(loads(path.read_text(encoding="utf-8")), "symbol"):
                ref = next(p[2] for p in children(node, "property") if p[1] == "Reference")
                if not ref.startswith("#"):
                    symbols[ref] = values(node, "at")[:2]
            plot, = [p for p in plots if symbols.keys() <= {t.text for t in p.iter(SVG+"text")}]
            art = ET.Element(SVG+"g", {"id": f"sheet-{page}", "font-family": "sans-serif"})
            for group in plot.findall(SVG+"g"):
                # KiCad supplies a searchable text layer over stroked glyphs. Use its
                # own glyph widths and anchors with native text for legibility at zoom.
                for parent in group.iter():
                    for child in list(parent):
                        if child.get("class") == "stroked-text":
                            parent.remove(child)
                        elif child.tag == SVG+"text":
                            colour = re.search(r"(?:^|;)\s*stroke:(#[0-9a-fA-F]+)", parent.get("style", ""))
                            child.set("fill", colour[1] if colour else INK)
                            child.set("opacity", "1")
                art.append(group)
            ref_labels = {ref: min(((float(t.get("x")), float(t.get("y")))
                               for t in art.iter(SVG+"text") if t.text == ref),
                              key=lambda xy: math.dist(xy, centre)) for ref, centre in symbols.items()}
            pages[page] = (art, symbols, ref_labels)
    return pages


def draw_schematic(svg, crops, pages, parts, h):
    defs = svg.find(SVG+"defs")
    for page in sorted({p for p, _, _ in crops}):
        defs.append(pages[page][0])
    seen = set()
    for (page, crop, caption), box in zip(crops, layouts(len(crops), 690, h), strict=True):
        x, y, w, height = box
        l, t, r, b = crop
        panel(svg, x, y, w, height, "white", LINE, 8)
        label(svg, x+12, y+23, f"{caption}  ·  原理图第 {page} 页", 15, SOFT)
        ix, iy, iw, ih = x+9, y+29, w-18, height-35
        scale = min(iw/(r-l), ih/(b-t))
        ox, oy = ix+(iw-(r-l)*scale)/2, iy+(ih-(b-t)*scale)/2
        viewport = draw(svg, "svg", x=ox, y=oy, width=(r-l)*scale, height=(b-t)*scale,
                        viewBox=f"{l} {t} {r-l} {b-t}", overflow="hidden")
        use(viewport, f"sheet-{page}")
        for part in parts:
            ref = part["ref"]
            pt = pages[page][1].get(ref)
            if pt and hit(crop, pt):
                if part["page"] != page:
                    raise ValueError(f"{ref}: guide links to page {part['page']}, symbol is on page {page}")
                seen.add(ref)
                # On large ICs the plotted reference can sit well above the body.
                # Include the symbol, reference and nearby wiring in the same zoom.
                rx, ry = pages[page][2][ref]
                dy = abs(ry-pt[1])
                left, right = min(pt[0]-8, rx-6), max(pt[0]+8, rx+7)
                top = min(pt[1]-6, ry-5)
                bottom = max(pt[1]+6, ry+6, pt[1]+.72*dy)
                centre = ox+((left+right)/2-l)*scale, oy+((top+bottom)/2-t)*scale
                span = max(44, right-left+4, (bottom-top+3)*1.56)
                focus_view(svg, "sch-"+ref, centre, span*scale,
                           (ox, oy, (r-l)*scale, (b-t)*scale))
    if seen != {p["ref"] for p in parts}:
        raise ValueError(f"Missing schematic symbol in {crops}: {seen}")


def draw_inset(svg, index, box, crop, caption, refs, coords, flows):
    x, y, w, h = box
    left, top, right, bottom = crop
    panel(svg, x, y, w, h, "#f5f8f7", LINE, 8)
    label(svg, x+14, y+24, caption, 15, SOFT, font_weight=600)
    vx, vy, vw, vh = x+12, y+38, w-24, h-54
    scale = min(vw/(right-left), vh/(bottom-top))
    cw, ch = (right-left)*scale, (bottom-top)*scale
    ox, oy = vx+(vw-cw)/2, vy+(vh-ch)/2
    def project(point):
        return (ox+(point[0]-left)*scale, oy+(point[1]-top)*scale)
    layer = draw(svg, "svg", x=ox, y=oy, width=cw, height=ch,
                 viewBox=f"{left} {top} {right-left} {bottom-top}", overflow="hidden")
    use(layer, "routing", opacity=".63")
    defs = draw(svg, "defs")
    clip = draw(defs, "clipPath", id=f"crop-{index}")
    panel(clip, ox, oy, cw, ch, "white", "none")
    tracks = draw(svg, "g", clip_path=f"url(#crop-{index})")
    for i, routes in enumerate(flows):
        for route in routes:
            trace(tracks, route, project, (ox+4, oy+4, ox+cw-4, oy+ch-4), PALETTE[i])

    for ref in refs:
        px, py = project(coords[ref])
        focus_view(svg, "pcb-"+ref, (px, py), min(260, 16*scale), (x, y, w, h))
        dx, dy = LABEL_OFFSETS.get(ref, (0, 0))
        if dx or dy:
            line(svg, px, py, px+dx, py+dy, SOFT, 1.2)
            draw(svg, "circle", cx=px, cy=py, r=2, fill=SOFT)
        group = draw(svg, "g", data_ref=ref, data_board_xy="%g %g" % coords[ref],
                     transform=f"translate({px+dx:.3f} {py+dy:.3f})")
        label(group, 0, 0, ref, 15, "#10302f", text_anchor="middle", dy=".35em",
              font_family=MONO, font_weight=700, stroke="white", stroke_width=3.5,
              paint_order="stroke fill", stroke_linejoin="round")


def spec_table(svg, parts, y):
    label(svg, 38, y, "元件规格", 24, font_weight=700)
    label(svg, 151, y-1, f"{len(parts)} 个装配位号", 15, SOFT)
    xs = (50, 155, 480, 687)
    panel(svg, 38, y+14, 1280, 31, "#e5eeea", "none")
    for x, s in zip(xs, ("位号", "制造商型号 / MPN", "封装", "本板参数与器件额定值")):
        label(svg, x, y+35, s, 14, SOFT, font_weight=650)
    yy = y + 45
    for i, p in enumerate(parts):
        lines = wrap(p["spec"], 40)
        height = 30 + (len(lines)-1)*20
        panel(svg, 38, yy, 1280, height, "white" if i%2 else "#f5f8f6", "none")
        label(svg, xs[0], yy+20, p["ref"], 16, font_weight=700, font_family=MONO)
        label(svg, xs[1], yy+20, p["mpn"], 15, font_family=MONO)
        label(svg, xs[2], yy+20, p["pkg"], 15)
        for n, row in enumerate(lines):
            label(svg, xs[3], yy+20+n*20, row, 15)
        yy += height
    return yy


def body_center(footprint):
    # These through-hole libraries place the origin at pin 1. Use the centre of
    # the F.Fab body, transformed with the footprint's current board rotation.
    offsets = {"C1": (1.75, 0), "C15": (1.75, 0), "C22": (1.75, 0),
               "J1": (0, 6.85), "J3": (3.75, .525), "J4": (3.75, .525), "J5": (2.5, 0)}
    dx, dy = rotate(*offsets.get(footprint.ref, (0, 0)), footprint.angle)
    return footprint.xy[0]+dx, footprint.xy[1]+dy


def illustration(zone, number, parts, copper, source, pages):
    coords = {p["ref"]: copper.local(body_center(copper.parts[p["ref"]])) for p in parts}
    svg = ET.Element(SVG+"svg", {"version":"1.1", "font-family":FONT, "lang":"zh-CN",
                                 "role":"img", "aria-labelledby":"title summary"})
    draw(svg, "title", id="title").text = zone.name + " · 双层走线与工作原理"
    draw(svg, "desc", id="summary").text = zone.summary
    define_artwork(svg, source)
    background = panel(svg, 0, 0, 1360, 1, "#fcfdfb", "none")
    panel(svg, 0, 0, 1360, 108, "#173d39", "none")
    label(svg, 37, 29, f"PCW-MC-01   /   功能分区 {number:02d} · 09", 15, "#c2dbd6", font_weight=600)
    label(svg, 35, 79, zone.name, 40, "white", font_weight=700)
    label(svg, 36, 137, zone.summary, 19)
    # Show the position of each crop in the same orientation as the detailed view.
    mx, my, factor = 1210, 13, 1.55
    label(svg, mx-16, 60, "整板定位", 14, "#c2dbd6", text_anchor="end")
    panel(svg, mx, my, 70*factor, 50*factor, "#35554f", "#94ada7", 3)
    for _, (l,t,r,b) in zone.crops:
        panel(svg, mx+l*factor, my+t*factor, (r-l)*factor, (b-t)*factor, "#b7dabd", "#e2f3cd", 1)
    h = 446
    label(svg, 38, 164, "双层走线局部放大", 16, SOFT, font_weight=650)
    label(svg, 690, 164, "KiCad 电路原理图", 16, SOFT, font_weight=650)
    routes = [[copper.path(r) for r in f.routes] for f in zone.flows]
    seen = []
    for i, ((caption, crop), box) in enumerate(zip(zone.crops, layouts(len(zone.crops), 38, h), strict=True)):
        refs = [ref for ref, xy in coords.items() if hit(crop, xy)]
        seen.extend(refs)
        draw_inset(svg, i, box, crop, caption, refs, coords, routes)
    if sorted(seen) != sorted(coords):
        raise ValueError(f"{zone.id} crop coverage differs: {seen} vs {list(coords)}")
    draw_schematic(svg, SCHEMATICS[zone.id], pages, parts, h)
    y = 175+h+24
    for x, colour, name in ((40, "#a23443", "L1 顶层"), (152, "#1b6b61", "L4 底层")):
        line(svg, x, y-5, x+22, y-5, colour, 4)
        label(svg, x+29, y, name, 14, SOFT)
    label(svg, 275, y, "箭头与下方同色通路对应，虚线段在 L4。内层电源与地平面省略。", 14, SOFT)
    label(svg, 38, y+50, "工作原理与流向", 24, font_weight=700)
    y += 67
    for first in range(0, len(zone.flows), 2):
        pair = zone.flows[first:first+2]
        height = 108+20*max(len(wrap(f.note, 41)) for f in pair)
        for n, flow in enumerate(pair):
            draw_flow(svg, flow, first+n, 38+n*652, y, height)
        y += height
    bottom = spec_table(svg, parts, y+30)
    label(svg, 39, bottom+27, "PhysiClaw  /  PCW-MC-01 v1.0", 14, SOFT)
    label(svg, 1316, bottom+27, "底图  top-bottom-routing.svg    ·    元件面俯视", 14, SOFT, text_anchor="end")
    svg.set("viewBox", f"0 0 1360 {bottom+44}")
    draw(svg, "view", id="board", viewBox=f"38 175 628 {h}")
    draw(svg, "view", id="schematic", viewBox=f"690 175 628 {h}")
    background.set("height", str(bottom+44))
    return svg


def ic_routing(svg, copper, footprint, rows):
    """Crop the original plot in board coordinates and mark real, rotated pad centres."""
    points = [copper.local(pad_center(footprint, str(n))) for n in range(1, len(rows)+1)]
    cx, cy = copper.local(footprint.xy)
    x, y, w, h = 36, 177, 549, 310
    # Keep some surrounding routing, while reserving at least a pin pitch per label.
    extent_x, extent_y = (max(abs(p[i]-c) for p in points) for i, c in enumerate((cx, cy)))
    scale = min(w / (2*extent_x + 2.6), h / (2*extent_y + max(1.35, extent_y*.38)))
    left, top = cx-w/(2*scale), cy-h/(2*scale)
    panel(svg, x, y, w, h, "#f8fafc")
    inset = draw(svg, "svg", x=x, y=y, width=w, height=h, overflow="hidden",
                 viewBox=f"{left} {top} {w/scale} {h/scale}")
    use(inset, "routing")
    nearest = min(math.dist(a, b) for i, a in enumerate(points) for b in points[i+1:])
    radius = min(13, nearest*scale*.465)
    # On fine-pitch packages, name the motion and serial paths beside the pads.
    # Other names remain in the numbered key so adjacent text never hides a land.
    named_pins = {"U2": (8, 10, 11, 12, 27, 28, 33, 34, 35, 36),
                  "U4": (3, 4, 8, 19, 20, 21, 23),
                  "U5": (2, 14, 16, 19, 21, 23, 24, 26), "U6": (2, 14, 16, 19, 21, 23, 24, 26)}
    for n, ((bx, by), (name, kind, net, _)) in enumerate(zip(points, rows, strict=True), 1):
        px, py = x+(bx-left)*scale, y+(by-top)*scale
        marker = draw(svg, "g", data_pad=n)
        draw(marker, "title").text = f"{n} · {name} · {kind} · {net}"
        draw(marker, "circle", cx=px, cy=py, r=radius, fill="#ffcd78" if n == 1 else "#16352e",
             stroke="white", stroke_width=1)
        label(marker, px, py+radius*.4, str(n), radius*1.17, "#192d26" if n == 1 else "white",
              font_family=MONO, font_weight=700, text_anchor="middle")
        if len(rows) <= 10 or n in named_pins.get(footprint.ref, ()):
            # Print names outside the package, leaving copper between pads visible.
            horizontal = footprint.ref in {"U3", "Q6"} or (len(rows) > 10 and math.isclose(abs(bx-cx), extent_x))
            if horizontal:
                side = -1 if px < x+w/2 else 1
                tx, ty = px+side*(radius+13), py+5
                anchor = "end" if side < 0 else "start"
            else:
                tx, ty = px, py+(-radius-9 if py < y+h/2 else radius+19)
                anchor = "middle"
            caption = net if footprint.ref == "U2" else name
            label(marker, tx, ty, caption, 14, INK, text_anchor=anchor, font_family=MONO,
                  font_weight=700, paint_order="stroke", stroke="white", stroke_width=4,
                  stroke_linejoin="round")
    for lx, colour, name in ((38, "#a23443", "L1 顶层"), (150, "#1b6b61", "L4 底层")):
        line(svg, lx, 511, lx+23, 511, colour, 4)
        label(svg, lx+31, 516, name, 14, SOFT)
    label(svg, 260, 516, "橙色为 1 脚 · 省略覆铜与内层", 14, SOFT)
    # A same-orientation board overview connects the close-up to the physical board.
    mx, my, factor = 1044, 20, 1.72
    panel(svg, mx, my, 70*factor, 50*factor, "#f4f7f2", "none", 3)
    overview = draw(svg, "svg", x=mx, y=my, width=70*factor, height=50*factor, viewBox="0 0 70 50")
    use(overview, "routing")
    draw(overview, "circle", cx=cx, cy=cy, r=3.0, fill="#ffcd78", stroke="#19352c", stroke_width=1)


def ic_pin_table(svg, rows, *, transistor=False):
    dense = len(rows) > 10
    y = 606
    label(svg, 36, 566, "逐脚对照", 25, font_weight=700)
    legend = "电流方向按板上的开关电路标注" if transistor else "输入、输出均以本颗器件为参照   ·   — 表示焊盘悬空"
    label(svg, 1164, 565, legend, 15, SOFT, text_anchor="end")
    count = (len(rows)+1)//2 if dense else len(rows)
    width, step = (551, 54) if dense else (1128, 40)
    for col in range(2 if dense else 1):
        x = 36 + col*577
        panel(svg, x, y-23, width, 31, "#e5eee8", "none")
        for offset, heading in ((10, "脚号"), (58, "引脚" if transistor else "芯片引脚"), (224, "方向 / 类型")):
            label(svg, x+offset, y-2, heading, 13, SOFT, font_weight=650)
        net_x = width-10 if dense else 375
        anchor = "end" if dense else "start"
        label(svg, x+net_x, y-2, "PCB 网络", 13, SOFT, font_weight=650, text_anchor=anchor)
        if not dense:
            label(svg, x+567, y-2, "在本板上的连接与作用", 13, SOFT, font_weight=650)
        for i, (name, kind, net, note) in enumerate(rows[col*count:(col+1)*count]):
            n = col*count+i+1
            baseline = y+31+i*step
            group = draw(svg, "g", data_pin=n, data_net=net)
            label(group, x+10, baseline, f"{n:02d}", 16, "#935412" if n == 1 else INK,
                  font_family=MONO, font_weight=700)
            label(group, x+58, baseline, name, 15, font_family=MONO, font_weight=700)
            label(group, x+224, baseline, kind, 15, "#23614b")
            label(group, x+net_x, baseline, net, 14, SOFT, font_family=MONO, text_anchor=anchor)
            label(group, x+(58 if dense else 567), baseline+(20 if dense else 0), note, 15)
            line(group, x, y+8+(i+1)*step, x+width, y+8+(i+1)*step, LINE)
    return y+8+count*step


def ic_illustration(part, card, copper, source):
    ref = part["ref"]
    footprint = copper.parts[ref]
    rows = [tuple(raw.split("|")) for raw in card.pins.strip().splitlines()]
    pins = {(int(p.number), "—" if p.net.startswith("unconnected-") or not p.net else p.net)
            for p in footprint.pads if p.number and p.on_layer("F.Cu")}
    expected = {(n, net) for n, (_, _, net, _) in enumerate(rows, 1)}
    if pins != expected:
        raise ValueError(f"{ref}: pin notes and copper disagree: {pins ^ expected}")
    svg = ET.Element(SVG+"svg", {"font-family": FONT, "lang": "zh-CN", "role": "img",
                                 "aria-labelledby": "title summary"})
    draw(svg, "title", id="title").text = f"{ref} · {part['mpn']} · {card.title}"
    draw(svg, "desc", id="summary").text = card.path + "。元件面俯视，数字与下方引脚表对应。"
    define_routing(svg, source)
    background = panel(svg, 0, 0, 1200, 1, "#fcfdf9", "none")
    panel(svg, 0, 0, 1200, 126, "#173b32", "none")
    label(svg, 36, 31, "PhysiClaw    /    PCW-MC-01   v1.0", 15, "#cbdfd2", font_weight=600)
    label(svg, 34, 86, ref, 48, "#ffcd78", font_family=MONO, font_weight=700)
    label(svg, 148, 82, card.title, 36, "#ffffff", font_weight=700)
    label(svg, 150, 109, part["mpn"], 17, "#d3e3d9", font_family=MONO)
    label(svg, 1028, 68, "板上位置", 14, "#d3e3d9", text_anchor="end")
    label(svg, 36, 161, "焊盘与走线", 21, font_weight=700)
    label(svg, 585, 161, "元件面俯视", 14, SOFT, text_anchor="end")
    ic_routing(svg, copper, footprint, rows)
    x = 618
    label(svg, x, 161, "电路怎样工作", 21, font_weight=700)
    panel(svg, x, 177, 546, 39, "#e5eee8", "none", 4)
    label(svg, x+12, 203, card.path, 18, font_weight=650)
    for i, (title, body) in enumerate(card.lessons):
        y = 249+i*91
        label(svg, x, y, title, 18, "#226348", font_weight=700)
        for j, row in enumerate(wrap(body, 30)):
            label(svg, x, y+26+j*23, row, 17)
    end = ic_pin_table(svg, rows, transistor=ref in TRANSISTOR_CARDS)
    label(svg, 36, end+36, f"PCW-MC-01 v1.0   /   KiCad 原理图第 {part['page']} 页   /   top-bottom-routing.svg", 14, SOFT)
    link = draw(svg, "a", target="_blank")
    link.set(XLINK+"href", part["datasheet"])
    label(link, 1164, end+36, f"{part['mpn']}  ·  原厂数据手册 ↗", 14, "#226348", text_anchor="end")
    height = end+55
    svg.set("viewBox", f"0 0 1200 {height}")
    svg.set("width", "1200")
    svg.set("height", str(height))
    background.set("height", str(height))
    return svg


def main():
    pcb = ROOT / "pcb/kicad/PCW-MC-01.kicad_pcb"
    base = BUILD / "view/top-bottom-routing.svg"
    review_assets = ("view/top-bottom-routing.svg", "view/usb-routing.svg", "view/component-reference.svg",
                     "view/probe-map.svg", "view/L3-power.svg", "view/3d-top.png", "schematic.pdf")
    manifest = json.loads((BUILD / "manifest.json").read_text())
    inputs = [(ROOT / name, sha) for name, sha in manifest["source_sha256"].items()
              if name.startswith("pcb/kicad/")]
    inputs.extend((BUILD / name, manifest["review_sha256"][name])
                  for name in (*review_assets, "assembly/assembly.csv"))
    for path, expected in inputs:
        if digest(path) != expected:
            raise ValueError(f"{path.name} differs from the build manifest. Run make build first.")
    copper = Copper(Board(pcb))
    raw = (GUIDE / "parts.js").read_text().split("const parts = ", 1)[1]
    parts = json.loads(raw.strip().removesuffix(";"))
    with (BUILD / "assembly/assembly.csv").open() as f:
        bom = {row["Reference"]: row for row in csv.DictReader(f)}
    if len(parts) != len(bom) or {p["ref"]: (p["mpn"], p["code"], p["process"]) for p in parts} != {
        ref: (row["MPN"], row["LCSC"], row["Process"]) for ref, row in bom.items()
    }:
        raise ValueError("Guide parts differ from the fitted assembly BOM")
    for part in parts:
        footprint = copper.parts[part["ref"]]
        pins = {(pad.number, pad.net) for pad in footprint.pads
                if pad.number and pad.net and not pad.net.startswith("unconnected-")}
        if set(map(tuple, part["pins"])) != pins or tuple(part["xy"]) != copper.local(footprint.xy):
            raise ValueError(f"{footprint.ref}: guide pin map or footprint position differs from the PCB")
    if {p["zone"] for p in parts} != {z.id for z in ZONES}:
        raise ValueError("Guide parts and illustration zones differ")
    pages = schematic_sources()
    source = ET.parse(base).getroot()
    by_ref = {p["ref"]: p for p in parts}
    if {ref for ref in by_ref if ref.startswith("U")} != CARDS.keys():
        raise ValueError("IC illustrations do not cover the fitted ICs")
    for directory, cards in (("ic", CARDS), ("transistors", TRANSISTOR_CARDS)):
        pin_folder = ASSETS / directory
        pin_folder.mkdir(exist_ok=True)
        for ref, card in cards.items():
            save(ic_illustration(by_ref[ref], card, copper, source), pin_folder / f"{ref}.svg")
    folder = ASSETS / "zones"
    folder.mkdir(exist_ok=True)
    atlas = {}
    for n, zone in enumerate(ZONES, 1):
        fitted = [p for p in parts if p["zone"] == zone.id]
        svg = illustration(zone, n, fitted, copper, source, pages)
        save(svg, folder / f"{zone.id}.svg")
        anchors = {}
        for tag in svg.findall("./"+SVG+"g[@data-ref]"):
            x, y = map(float, tag.get("transform").split(")")[0][10:].split())
            anchors[tag.get("data-ref")] = [round((x-38)/628*100, 3), round((y-175)/446*100, 3)]
        atlas[zone.id] = {"anchors": anchors, "flows": [
            [flow.title, re.sub(r"[a-z]+:", "", flow.stages), flow.note] for flow in zone.flows]}
    (GUIDE / "routing.js").write_text("// Generated by tools/guide_illustrations.py\nconst routing = "
                                     + json.dumps(atlas, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    for name in review_assets:
        shutil.copyfile(BUILD / name, ASSETS / Path(name).name)


if __name__ == "__main__":
    main()
