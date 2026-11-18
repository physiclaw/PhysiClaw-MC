"""Geometry regressions that would place polarized parts on the wrong pads."""

import unittest
from pathlib import Path

from tools.board_data import pad_center
from tools.kicad_board import Board


class PlacementGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pcb = (
            Path(__file__).resolve().parents[1]
            / "pcb"
            / "kicad"
            / "PCW-MC-01.kicad_pcb"
        )
        cls.footprints = {f.ref: f for f in Board(pcb).footprints}

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
