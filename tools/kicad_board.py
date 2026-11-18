"""Read manufacturing geometry and prepare review copies of a KiCad 10 PCB."""

import math
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from sexpdata import Symbol, dumps, loads


def children(node, name):
    key = Symbol(name)
    return [item for item in node if isinstance(item, list) and item and item[0] == key]


def values(node, name, default=None):
    matches = children(node, name)
    if matches:
        return matches[0][1:]
    if default is None:
        raise ValueError(f"Missing {name} in {node[0]}")
    return default


def rotate(x, y, degrees):
    """Rotate a local CAD vector counterclockwise in KiCad's Y-down frame."""
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return x * c + y * s, -x * s + y * c


@dataclass
class Pad:
    number: str
    kind: str
    shape: str
    xy: tuple[float, float]
    angle: float
    size: tuple[float, float]
    layers: list[str]
    drill: tuple[float, float]
    radius: float
    net: str

    def on_layer(self, name):
        return name in self.layers or "*." + name.split(".")[1] in self.layers


@dataclass
class Footprint:
    land: str
    fields: dict[str, str]
    attributes: set[str]
    layer: str
    xy: tuple[float, float]
    angle: float
    pads: list[Pad]

    @property
    def ref(self):
        return self.fields["Reference"]

    @classmethod
    def read(cls, node):
        x, y, *rotation = values(node, "at")
        angle = rotation[0] if rotation else 0
        pads = []
        for item in children(node, "pad"):
            u, v, *pad_angle = values(item, "at")
            dx, dy = rotate(u, v, angle)
            # KiCad stores local pad centres but board-space pad angles, in nm resolution.
            centre = (round(x + dx, 6), round(y + dy, 6))
            size = tuple(values(item, "size"))
            hole = values(item, "drill", [])
            if hole and hole[0] == Symbol("oval"):
                _, w, h = hole
            elif hole:
                (w,) = hole
                h = w
            else:
                w = h = 0
            shape = str(item[3])
            radius = min(size) * values(item, "roundrect_rratio", [0])[0]
            if shape in {"circle", "oval"}:
                radius = min(size) / 2
            pads.append(
                Pad(
                    item[1],
                    str(item[2]),
                    shape,
                    centre,
                    pad_angle[0] if pad_angle else 0,
                    size,
                    values(item, "layers"),
                    (w, h),
                    round(radius, 6),
                    values(item, "net", [""])[-1],
                )
            )
        return cls(
            node[1],
            {p[1]: p[2] for p in children(node, "property")},
            set(map(str, values(node, "attr", []))),
            values(node, "layer")[0],
            (float(x), float(y)),
            float(angle),
            pads,
        )


def write_pcb(path, items):
    # Keep each top-level element on a separate line for KiCad's file reader.
    with path.open("w", encoding="utf-8") as output:
        output.write("(kicad_pcb\n")
        for item in items:
            output.write(dumps(item) + "\n")
        output.write(")\n")


def hide_property(prop):
    if hide := children(prop, "hide"):
        hide[0][1:] = [Symbol("yes")]
    else:
        prop.append([Symbol("hide"), Symbol("yes")])


class Board:
    def __init__(self, path: Path):
        self.tree = loads(
            path.read_text(encoding="utf-8"), nil=None, true=None, false=None
        )
        if self.tree[0] != Symbol("kicad_pcb"):
            raise ValueError(f"Expected KiCad PCB in {path}")
        self.footprints = [Footprint.read(f) for f in children(self.tree, "footprint")]
        self.vias = [
            (*values(v, "at"), values(v, "drill")[0])
            for v in children(self.tree, "via")
        ]

    def write_assembly_view(self, path: Path, board_name: str, version: str):
        # Move labels in the drawing copy to clear switches, slots and polarity marks.
        label_offsets = {
            "J1": (5, -2.4),
            "J3": (-3.75, -1.8),
            "J4": (-3.75, -1.8),
            "SW1": (0, 0),
            "D4": (-4, 0),
            "D1": (0, -2.6),
            "D2": (0, -4),
        }
        drawing = deepcopy(self.tree)
        for node, footprint in zip(
            children(drawing, "footprint"), self.footprints, strict=True
        ):
            labels = [
                t
                for t in children(node, "fp_text")
                if t[2] == "${REFERENCE}" and values(t, "layer")[0] == "F.Fab"
            ]
            board_only = "board_only" in footprint.attributes
            if labels or board_only:
                reference = next(
                    p for p in children(node, "property") if p[1] == "Reference"
                )
                hide_property(reference)
            for label in labels:
                if board_only:
                    children(label, "layer")[0][1] = "Dwgs.User"
                elif footprint.ref in label_offsets:
                    dx, dy = rotate(*label_offsets[footprint.ref], -footprint.angle)
                    children(label, "at")[0][1:] = [round(dx, 6), round(dy, 6), 0]
        title_block = children(drawing, "title_block")[0]
        if values(title_block, "rev") != [version] or values(title_block, "title") != [
            board_name
        ]:
            raise ValueError("PCB title block disagrees with the board name or version")
        children(title_block, "title")[0][1] = f"{board_name} | Top assembly"
        write_pcb(path, drawing[1:])

    def write_routing_view(self, path: Path):
        # Omit board zones in this temporary copy to make individual traces visible.
        write_pcb(path, (item for item in self.tree[1:] if item[0] != Symbol("zone")))

    def write_zone_view(self, path: Path, layer: str, net: str):
        zone = Symbol("zone")
        write_pcb(path, (
            item for item in self.tree[1:]
            if item[0] != zone or (
                layer in values(item, "layers", values(item, "layer", []))
                and values(item, "net", []) == [net]
            )
        ))

    def write_outline_view(self, path: Path):
        items = self.tree[1:]
        for index, item in enumerate(items):
            if item[0] != Symbol("footprint"):
                continue
            footprint = deepcopy(item)
            for prop in children(footprint, "property"):
                if prop[1] in {"Reference", "Value"}:
                    hide_property(prop)
            for label in children(footprint, "fp_text"):
                footprint.remove(label)
            items[index] = footprint
        write_pcb(path, items)

    def write_aperture_view(self, path: Path, references):
        # Keep the requested footprints and the original board outline and setup.
        omitted = {
            Symbol(name) for name in ("footprint", "segment", "arc", "via", "zone", "group")
        }
        items = [item for item in self.tree[1:] if item[0] not in omitted]
        items.extend(
            node for node, footprint in zip(children(self.tree, "footprint"),
                                            self.footprints, strict=True)
            if footprint.ref in references
        )
        write_pcb(path, items)
