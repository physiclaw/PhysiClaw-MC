"""Geometry regressions for footprint placement and USB-C routing."""

import heapq
import json
import math
import unittest
from collections import defaultdict
from pathlib import Path

from tools.board_data import pad_center
from tools.kicad_board import Board, children, rotate, values


USB_C_CONTACTS = (
    ("USB_DP_CONN", "A6", "B6"),
    ("USB_DM_CONN", "A7", "B7"),
)


def distance_to_pad(point, pad):
    """Return the signed distance to a rotated SMT copper pad."""
    x, y = rotate(point[0] - pad.xy[0], point[1] - pad.xy[1], -pad.angle)
    width, height = pad.size
    radius = pad.radius
    dx, dy = abs(x) - width / 2 + radius, abs(y) - height / 2 + radius
    return math.hypot(max(dx, 0), max(dy, 0)) + min(max(dx, dy), 0) - radius


def planar_trace_length(board, net, start, end):
    """Return the shortest planar trace length in millimetres."""
    edges = defaultdict(list)

    def connect(a, b, length):
        edges[a].append((b, length))
        edges[b].append((a, length))

    for segment in children(board.tree, "segment"):
        if values(segment, "net") != [net]:
            continue
        a = tuple(values(segment, "start"))
        b = tuple(values(segment, "end"))
        layer = values(segment, "layer")[0]
        connect((layer, a), (layer, b), math.dist(a, b))

    for via in children(board.tree, "via"):
        if values(via, "net") != [net]:
            continue
        at = tuple(values(via, "at"))
        top, bottom = values(via, "layers")
        # This check measures planar trace length and excludes via barrels.
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


def ground_fills(board):
    fills = defaultdict(list)
    for zone in children(board.tree, "zone"):
        if values(zone, "net", []) == ["GND"]:
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
        cls.segments = defaultdict(list)
        for segment in children(cls.board.tree, "segment"):
            layer, = values(segment, "layer")
            net, = values(segment, "net")
            cls.segments[layer, net].append(segment)

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

    def test_routed_via_drills_clear_smt_pads(self):
        # Same-net pad and via overlap can pass KiCad's copper clearance DRC.
        smt = [
            (footprint.ref, pad)
            for footprint in self.board.footprints
            for pad in footprint.pads
            if pad.kind == "smd" and (pad.on_layer("F.Cu") or pad.on_layer("B.Cu"))
        ]
        for at, via in self.vias.items():
            drill, = values(via, "drill")
            distance, ref, number = min(
                (distance_to_pad(at, pad), ref, pad.number) for ref, pad in smt
            )
            self.assertGreater(distance - drill / 2, 0,
                               f"Via at {at} touches SMT pad {ref}.{number}")

    def test_usb_c_contact_ties_are_short(self):
        usb = self.footprints["J2"]
        for net, first, second in USB_C_CONTACTS:
            with self.subTest(net=net):
                start = ("F.Cu", pad_center(usb, first))
                end = ("F.Cu", pad_center(usb, second))
                self.assertLessEqual(planar_trace_length(self.board, net, start, end), 3.5)

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
                p_tracks, m_tracks = (
                    [s for s in self.segments["F.Cu", net] if values(s, "width") == [width]]
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

    def test_usb_c_horizontal_escapes_and_mirrored_45_degree_ties(self):
        usb = self.footprints["J2"]
        columns = []
        for net, *pins in USB_C_CONTACTS:
            via_x = []
            for pin in pins:
                pad_x, pad_y = pad_center(usb, pin)
                at, = [
                    point for point, via in self.vias.items()
                    if values(via, "net") == [net] and point[1] == pad_y
                ]
                self.assertGreater(at[0], pad_x)
                endpoints = {(pad_x, pad_y), at}
                self.assertTrue(any(
                    {tuple(values(t, "start")), tuple(values(t, "end"))} == endpoints
                    for t in self.segments["F.Cu", net]
                ), pin)
                via_x.append(at[0])
            self.assertEqual(via_x[0], via_x[1], net)
            columns.append(via_x[0])

        plus_x, minus_x = columns
        self.assertGreater(minus_x, plus_x)
        x_sum = plus_x + minus_x
        y_offset = pad_center(usb, "A7")[1] - pad_center(usb, "B6")[1]
        plus_tracks, minus_tracks = (
            self.segments["B.Cu", net] for net, _, _ in USB_C_CONTACTS
        )
        mirrored = set()
        for track in plus_tracks:
            self.assertEqual(values(track, "width"), [0.20])
            ax, ay = values(track, "start")
            bx, by = values(track, "end")
            dx, dy = abs(ax - bx), abs(ay - by)
            self.assertTrue(dx == 0 or dy == 0 or math.isclose(dx, dy, abs_tol=1e-6))
            mirrored.add(frozenset(
                (round(x_sum - x, 6), round(y + y_offset, 6))
                for x, y in ((ax, ay), (bx, by))
            ))
        actual = set()
        for track in minus_tracks:
            self.assertEqual(values(track, "width"), [0.20])
            actual.add(frozenset(tuple(values(track, key)) for key in ("start", "end")))
        self.assertEqual(mirrored, actual)

    def test_usb_controlled_traces_keep_l2_ground(self):
        ground = ground_fills(self.board)["In1.Cu"]
        for (layer, net), tracks in self.segments.items():
            if layer != "F.Cu" or not net.startswith(("USB_DP", "USB_DM")):
                continue
            for track in tracks:
                if values(track, "width") != [0.28]:
                    continue
                for point in track_samples(track):
                    self.assertTrue(in_ground_fill(point, ground), (net, point))

    def test_usb_c_bottom_ties_have_a_local_ground_return(self):
        fills = ground_fills(self.board)
        for stitch in ((160.25, 61.88), (165.04, 62.12), (165.04, 63.93)):
            with self.subTest(stitch=stitch):
                self.assertIn(stitch, self.vias)
                via = self.vias[stitch]
                self.assertEqual(
                    [values(via, field) for field in ("net", "layers", "size", "drill")],
                    [["GND"], ["F.Cu", "B.Cu"], [0.6], [0.3]],
                )
                for layer in ("In1.Cu", "In2.Cu", "B.Cu"):
                    self.assertTrue(in_ground_fill(stitch, fills[layer]), layer)

        # Either contact tie can cross the clearance around a signal via.
        # Use the greater of L3 zone-to-copper and hole-to-copper clearances.
        diameter, drill = 0.40, 0.30
        antipad_radius = max(diameter / 2 + 0.20, drill / 2 + 0.25) + 0.01
        signal_positions = []
        for net, _, _ in USB_C_CONTACTS:
            vias = {at: via for at, via in self.vias.items() if values(via, "net") == [net]}
            self.assertEqual(len(vias), 2)
            for via in vias.values():
                self.assertEqual(values(via, "size"), [diameter])
                self.assertEqual(values(via, "drill"), [drill])
            signal_positions.extend(vias)

        for net, _, _ in USB_C_CONTACTS:
            covered = False
            for segment in self.segments["B.Cu", net]:
                for point in track_samples(segment):
                    if all(math.dist(point, at) > antipad_radius for at in signal_positions):
                        self.assertTrue(in_ground_fill(point, fills["In2.Cu"]), (net, point))
                        covered = True
            self.assertTrue(covered, net)
