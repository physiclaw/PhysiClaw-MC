"""Geometry regressions for footprint placement and USB-C routing."""

import heapq
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
        cls.footprints = {f.ref: f for f in cls.board.footprints}

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
