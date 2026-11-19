"""Geometry regressions for footprint placement and USB-C routing."""

import heapq
import json
import math
import unittest
from collections import defaultdict
from pathlib import Path

from tools.board_data import pad_center
from tools.kicad_board import Board, children, values


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

    def test_usb_c_contact_ties_are_short(self):
        usb = self.footprints["J2"]
        for net, first, second in (
            ("USB_DP_CONN", "A6", "B6"),
            ("USB_DM_CONN", "A7", "B7"),
        ):
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

    def test_usb_c_bottom_ties_have_a_local_ground_return(self):
        fills = ground_fills(self.board)
        for stitch in ((163.67, 62.24), (163.72, 63.92)):
            with self.subTest(stitch=stitch):
                self.assertIn(stitch, self.vias)
                via = self.vias[stitch]
                self.assertEqual(
                    [values(via, field) for field in ("net", "layers", "size", "drill")],
                    [["GND"], ["F.Cu", "B.Cu"], [0.6], [0.3]],
                )
                for layer in ("In1.Cu", "In2.Cu", "B.Cu"):
                    self.assertTrue(in_ground_fill(stitch, fills[layer]), layer)

        # Signal via drill radius plus hole-to-copper clearance and contour tolerance.
        antipad_radius = 0.1 + 0.25 + 0.01
        for net in ("USB_DP_CONN", "USB_DM_CONN"):
            signal_vias = [
                at for at, via in self.vias.items() if values(via, "net") == [net]
            ]
            self.assertEqual(len(signal_vias), 2)
            covered = False
            for segment in self.segments["B.Cu", net]:
                for point in track_samples(segment):
                    if all(math.dist(point, via) > antipad_radius for via in signal_vias):
                        self.assertTrue(in_ground_fill(point, fills["In2.Cu"]), (net, point))
                        covered = True
            self.assertTrue(covered, net)
