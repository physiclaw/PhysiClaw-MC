"""Geometry regressions for footprint placement and USB-C routing."""

import heapq
import json
import math
import unittest
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.board_data import pad_center, write_via_fill_layer
from tools.kicad_board import Board, children, values


USB_C_CONTACTS = (
    ("USB_DP_CONN", "A6", "B6"),
    ("USB_DM_CONN", "A7", "B7"),
)


def planar_trace_length(board, net, start, end, *, top_only=False):
    """Return the shortest planar trace length in millimetres."""
    edges = defaultdict(list)

    def connect(a, b, length):
        edges[a].append((b, length))
        edges[b].append((a, length))

    for segment in children(board.tree, "segment"):
        if values(segment, "net") != [net]:
            continue
        layer, = values(segment, "layer")
        if top_only and layer != "F.Cu":
            continue
        a = tuple(values(segment, "start"))
        b = tuple(values(segment, "end"))
        connect((layer, a), (layer, b), math.dist(a, b))

    if not top_only:
        # The planar length excludes via barrels.
        for via in children(board.tree, "via"):
            if values(via, "net") != [net]:
                continue
            at = tuple(values(via, "at"))
            top, bottom = values(via, "layers")
            connect((top, at), (bottom, at), 0)

    pending = [(0, start)]
    visited = set()
    while pending:
        distance, node = heapq.heappop(pending)
        if node == end:
            return distance
        if node in visited:
            continue
        visited.add(node)
        for neighbour, length in edges[node]:
            if neighbour not in visited:
                heapq.heappush(pending, (distance + length, neighbour))
    return math.inf


def overlapping_track_pitch(first, second):
    """Measure the center-to-center spacing where two parallel tracks overlap."""
    ax, ay = values(first, "start")
    bx, by = values(first, "end")
    cx, cy = values(second, "start")
    dx, dy = values(second, "end")
    length = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / length, (by - ay) / length
    if abs(ux * (dy - cy) - uy * (dx - cx)) > 1e-5:
        return math.inf
    start, end = sorted(((cx - ax) * ux + (cy - ay) * uy,
                         (dx - ax) * ux + (dy - ay) * uy))
    if min(length, end) <= max(0, start):
        return math.inf
    return abs(ux * (cy - ay) - uy * (cx - ax))


def plane_fills(board, net):
    fills = defaultdict(list)
    for zone in children(board.tree, "zone"):
        if values(zone, "net", []) == [net]:
            for polygon in children(zone, "filled_polygon"):
                layer, = values(polygon, "layer")
                fills[layer].append(values(polygon, "pts"))
    return fills


def in_ground_fill(point, polygons):
    x, y = point
    for polygon in polygons:
        inside = False
        _, ax, ay = polygon[-1]
        for _, bx, by in polygon:
            if (ay > y) != (by > y) and x < ax + (bx - ax) * (y - ay) / (by - ay):
                inside = not inside
            ax, ay = bx, by
        if inside:
            return True
    return False


def track_samples(segment):
    """Sample the centerline and both copper edges every 0.02 mm or less."""
    ax, ay = values(segment, "start")
    bx, by = values(segment, "end")
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    count = math.ceil(length / 0.02)
    half_width = values(segment, "width")[0] / 2
    for i in range(count):
        along = (i + 0.5) / count
        x, y = ax + along * dx, ay + along * dy
        for offset in (-half_width, 0, half_width):
            yield x - offset * dy / length, y + offset * dx / length


def samples_outside_antipads(tracks, antipads):
    for track in tracks:
        for point in track_samples(track):
            if all(math.dist(point, at) > radius for at, radius in antipads):
                yield point


class PlacementGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pcb = (
            Path(__file__).resolve().parents[1]
            / "pcb"
            / "kicad"
            / "PCW-MC-01.kicad_pcb"
        )
        cls.board = Board(pcb)
        cls.project = json.loads(
            pcb.with_suffix(".kicad_pro").read_text(encoding="utf-8")
        )
        cls.footprints = {f.ref: f for f in cls.board.footprints}
        cls.vias = {
            tuple(values(v, "at")): v for v in children(cls.board.tree, "via")
        }
        cls.capped_positions = {(x, y) for x, y, _, _ in cls.board.capped_vias}
        cls.ground_fills = plane_fills(cls.board, "GND")
        cls.segments = defaultdict(list)
        for segment in children(cls.board.tree, "segment"):
            layer, = values(segment, "layer")
            net, = values(segment, "net")
            cls.segments[layer, net].append(segment)

    def through_via_positions(self, net):
        return {
            at for at, via in self.vias.items()
            if values(via, "net") == [net] and values(via, "layers") == ["F.Cu", "B.Cu"]
        }

    def test_rotated_pin_one_and_slot_angle(self):
        usb = self.footprints["J2"]
        self.assertEqual(pad_center(usb, "B8"), (161.995, 64.75))
        shell = [pad for pad in usb.pads if pad.drill == (0.6, 1.7)]
        self.assertEqual(len(shell), 2)
        self.assertTrue(all(pad.angle % 180 == 90 for pad in shell))
        self.assertEqual(pad_center(self.footprints["U4"], "1"), (146.755, 63.375))

    def test_duplicate_switch_pads_and_rear_probe(self):
        self.assertEqual(pad_center(self.footprints["SW1"], "1"), (106, 61.9))
        probe = self.footprints["TP2"].pads[0]
        self.assertTrue(probe.on_layer("B.Cu"))
        self.assertFalse(probe.on_layer("F.Cu"))

    def test_routed_vias_clear_smt_pads(self):
        # Same-net pad and via overlap can pass KiCad's copper clearance DRC.
        smt = [
            (footprint.ref, pad)
            for footprint in self.board.footprints
            for pad in footprint.pads
            if pad.kind == "smd" and (pad.on_layer("F.Cu") or pad.on_layer("B.Cu"))
        ]
        # Mask is 1:1 on the signal and passive lands in this clearance check.
        for at, via in self.vias.items():
            drill, = values(via, "drill")
            distance, ref, number = min(
                (pad.edge_distance(at), ref, pad.number) for ref, pad in smt
            )
            gap = distance - drill / 2
            size, = values(via, "size")
            self.assertGreater(distance - size / 2, 1e-6,
                               f"Via land at {at} touches SMT pad {ref}.{number}")
            minimum = 0.20 if at in self.capped_positions else 0.125
            self.assertGreaterEqual(gap + 1e-6, minimum,
                                    f"Via drill at {at} too close to SMT pad {ref}.{number}")
            for pad in self.footprints["F1"].pads:
                self.assertGreaterEqual(pad.edge_distance(at) - drill / 2, 0.25,
                                        f"Via at {at} too close to F1.{pad.number}")

    def test_fill_layer_uses_the_drill_diameter_at_each_flash(self):
        holes = [("U8", "9", 115.0, -69.0, 0.30), ("J2", "A6", 162.9, -63.25, 0.20)]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sk.gbr"
            write_via_fill_layer(path, holes)
            records = path.read_text().splitlines()
        self.assertIn("%TF.FileFunction,Viafill*%", records)
        self.assertEqual(
            [r for r in records if r.startswith(("%ADD", "D", "X"))],
            ["%ADD10C,0.200*%", "%ADD11C,0.300*%", "D10*", "X162900000Y-63250000D03*",
             "D11*", "X115000000Y-69000000D03*"],
        )

    def test_usb_unused_port_terminations(self):
        for pin, ref in (("1", "R41"), ("2", "R42")):
            with self.subTest(pin=pin, ref=ref):
                resistor = self.footprints[ref]
                pads = {p.number: p for p in resistor.pads}
                self.assertEqual(resistor.fields["Value"], "49.9")
                self.assertEqual(pads["2"].net, "GND")
                net = pads["1"].net
                self.assertEqual(
                    {(f.ref, p.number) for f in self.board.footprints
                     for p in f.pads if p.net == net},
                    {("U7", pin), (ref, "1")},
                )
                start = ("F.Cu", pad_center(self.footprints["U7"], pin))
                end = ("F.Cu", pads["1"].xy)
                self.assertTrue(math.isfinite(
                    planar_trace_length(self.board, net, start, end, top_only=True)
                ))

    def test_usb_c_contact_ties_are_short(self):
        usb = self.footprints["J2"]
        for net, first, second in USB_C_CONTACTS:
            with self.subTest(net=net):
                start = ("F.Cu", pad_center(usb, first))
                end = ("F.Cu", pad_center(usb, second))
                self.assertLessEqual(planar_trace_length(self.board, net, start, end, top_only=True), 3.5)

    def test_usb_dimensions_match_the_7628_design(self):
        setup, = children(self.board.tree, "setup")
        stackup, = children(setup, "stackup")
        layers = {layer[1]: layer for layer in children(stackup, "layer")}
        expected = {
            "F.Cu": 0.035,
            "In1.Cu": 0.0152,
            "In2.Cu": 0.0152,
            "B.Cu": 0.035,
            "dielectric 1": 0.2104,
            "dielectric 2": 1.065,
            "dielectric 3": 0.2104,
        }
        self.assertEqual(
            {name: values(layers[name], "thickness")[0] for name in expected}, expected
        )
        for name in ("dielectric 1", "dielectric 3"):
            self.assertEqual(values(layers[name], "material"), ["FR4 (7628)"])
        settings = self.project["net_settings"]
        usb = next(c for c in settings["classes"] if c["name"] == "USB data")
        width, gap = 0.28, 0.18
        self.assertEqual((usb["diff_pair_width"], usb["diff_pair_gap"]), (width, gap))
        self.assertEqual(usb["track_width"], width)
        for suffix in ("", "_ESD", "_CONN"):
            plus, minus = f"USB_DP{suffix}", f"USB_DM{suffix}"
            with self.subTest(pair=(plus, minus)):
                for net in (plus, minus):
                    self.assertIn("USB data", settings["netclass_assignments"][net])
                layer = "B.Cu" if suffix == "_CONN" else "F.Cu"
                p_tracks, m_tracks = (
                    [s for s in self.segments[layer, net] if values(s, "width") == [width]]
                    for net in (plus, minus)
                )
                self.assertTrue(any(
                    math.isclose(overlapping_track_pitch(p, m), width + gap, abs_tol=1e-5)
                    for p in p_tracks
                    for m in m_tracks
                ))

    def test_u7_dm_fanout_width(self):
        endpoints = {(156.165, 67.6), (155.875, 67.6)}
        widths = [
            values(track, "width")[0]
            for track in self.segments["F.Cu", "USB_DM_ESD"]
            if {tuple(values(track, key)) for key in ("start", "end")} == endpoints
        ]
        self.assertEqual(widths, [0.26])

    def test_usb_route_lengths_in_both_plug_orientations(self):
        lengths = defaultdict(list)
        for net, a_pin, b_pin in USB_C_CONTACTS:
            # The ESD device and switch divide the path from J2 to U4 into three nets.
            lane = net.removesuffix("_CONN")
            tail = 0
            for name, first, last in ((lane + "_ESD", "U3", "U7"), (lane, "U7", "U4")):
                start, end = (
                    next(pad.xy for pad in self.footprints[ref].pads if pad.net == name)
                    for ref in (first, last)
                )
                tail += planar_trace_length(
                    self.board, name, ("F.Cu", start), ("F.Cu", end), top_only=True
                )
            esd = next(p.xy for p in self.footprints["U3"].pads if p.net == net)
            for pin in (a_pin, b_pin):
                contact = pad_center(self.footprints["J2"], pin)
                total = tail + planar_trace_length(
                    self.board, net, ("F.Cu", contact), ("F.Cu", esd)
                )
                self.assertTrue(math.isfinite(total), (pin, net))
                lengths[pin[0]].append(total)
        for orientation, (plus, minus) in lengths.items():
            self.assertLessEqual(abs(plus - minus), 2.0, orientation)

    def test_usb_controlled_traces_keep_l2_ground(self):
        ground = self.ground_fills["In1.Cu"]
        for (layer, net), tracks in self.segments.items():
            if layer != "F.Cu" or not net.startswith(("USB_DP", "USB_DM")):
                continue
            for track in tracks:
                if values(track, "width") != [0.28]:
                    continue
                for point in track_samples(track):
                    self.assertTrue(in_ground_fill(point, ground), (net, point))

    def test_each_l3_ground_region_has_two_plated_returns_to_l2(self):
        fills = self.ground_fills
        returns = self.through_via_positions("GND")
        returns.update(
            pad.xy for footprint in self.board.footprints for pad in footprint.pads
            if pad.net == "GND" and pad.kind == "thru_hole"
            and pad.on_layer("In1.Cu") and pad.on_layer("In2.Cu")
        )
        grounded = [at for at in returns if in_ground_fill(at, fills["In1.Cu"])]
        self.assertTrue(fills["In2.Cu"])
        for region in fills["In2.Cu"]:
            count = sum(in_ground_fill(at, [region]) for at in grounded)
            self.assertGreaterEqual(count, 2,
                                    f"L3 ground region near {region[0][1:]} needs two L2 returns")

    def test_each_l3_3v3_region_has_two_plated_connections(self):
        regions = plane_fills(self.board, "V3V3")["In2.Cu"]
        self.assertTrue(regions)
        power_vias = self.through_via_positions("V3V3")
        for region in regions:
            count = sum(in_ground_fill(at, [region]) for at in power_vias)
            self.assertGreaterEqual(count, 2,
                                    f"L3 3.3 V region near {region[0][1:]} needs two power vias")

    def test_bottom_control_tracks_keep_l3_ground(self):
        ground = self.ground_fills["In2.Cu"]
        for net in ("SOL_CMD", "ACTUATOR_ARM", "ESP_EN", "DRIVERS_DISABLE",
                    "TMC_BUS", "X_STEP", "X_DIR", "Y_DIR", "USB_VBUS"):
            antipads = [
                # The ground zone clears the via land by 0.20 mm or the drill
                # by 0.25 mm. Allow 0.04 mm for rounding at the fill boundary.
                (at, max(values(v, "size")[0] / 2 + 0.20,
                         values(v, "drill")[0] / 2 + 0.25) + 0.04)
                for at, v in self.vias.items() if values(v, "net") == [net]
            ]
            for point in samples_outside_antipads(self.segments["B.Cu", net], antipads):
                self.assertTrue(in_ground_fill(point, ground), (net, point))

    def test_usb_c_breakout_vias_and_ground_returns(self):
        fills = self.ground_fills
        for stitch in ((160.25, 61.88), (163.68, 62.22), (165.04, 62.12),
                       (165.04, 63.93), (158.77, 63.60)):
            with self.subTest(stitch=stitch):
                via = self.vias[stitch]
                self.assertEqual(values(via, "net"), ["GND"])
                self.assertEqual(values(via, "layers"), ["F.Cu", "B.Cu"])
                for layer in ("In1.Cu", "In2.Cu", "B.Cu"):
                    self.assertTrue(in_ground_fill(stitch, fills[layer]), layer)

        for net, _, _ in USB_C_CONTACTS:
            vias = {at: v for at, v in self.vias.items() if values(v, "net") == [net]}
            self.assertEqual(len(vias), 2)
            self.assertTrue(vias.keys() <= self.capped_positions)
            for via in vias.values():
                self.assertEqual(values(via, "size"), [0.60])
                self.assertEqual(values(via, "drill"), [0.30])
                self.assertEqual(values(via, "layers"), ["F.Cu", "B.Cu"])
            # Start/end-only lands leave the drill plus 0.25 mm clearance on
            # each inner plane. Allow 0.01 mm for KiCad's polygon approximation.
            antipad_radius = 0.30 / 2 + 0.25 + 0.01
            antipads = [(at, antipad_radius) for at in vias]
            for signal, reference in (("F.Cu", "In1.Cu"), ("B.Cu", "In2.Cu")):
                samples = list(samples_outside_antipads(self.segments[signal, net], antipads))
                self.assertTrue(samples, (signal, net))
                for point in samples:
                    self.assertTrue(in_ground_fill(point, fills[reference]), (net, point))
