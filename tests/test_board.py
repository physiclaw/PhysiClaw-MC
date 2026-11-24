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

INTERLOCK_SIGNALS = (
    "ESP_EN", "RESET_SINK", "ACTUATOR_ARM", "ACT_OE_N",
    "DRV_DISABLE_CMD", "DRIVERS_DISABLE", "SOL_CMD", "SOL_SAFE", "SOL_ENABLE",
)

# Follow supply and winding currents through the load and its bypass network.
# Every other net routed on L4 takes L3 ground as its reference.
L4_POWER_AND_WINDING_NETS = {
    "GND", "V3V3", "VIN_FUSED", "VIN_RAW",
    "X_A1", "X_A2", "X_B1", "X_B2", "Y_A1", "Y_A2", "Y_B1", "Y_B2",
}


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


def copper_strip_samples(start, end, width):
    """Sample the centerline and both copper edges every 0.02 mm or less."""
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy)
    count = math.ceil(length / 0.02)
    half_width = width / 2
    for i in range(count):
        along = (i + 0.5) / count
        x, y = ax + along * dx, ay + along * dy
        for offset in (-half_width, 0, half_width):
            yield x - offset * dy / length, y + offset * dx / length


def track_samples(segment):
    return copper_strip_samples(values(segment, "start"), values(segment, "end"),
                                values(segment, "width")[0])


def samples_outside_antipads(tracks, antipads):
    for track in tracks:
        for point in track_samples(track):
            if all(math.dist(point, at) > radius for at, radius in antipads):
                yield point


def via_plane_clearance_radius(via, reference):
    hole_clearance = values(via, "drill")[0] / 2 + 0.30
    outer_lands_only = str(values(via, "start_end_only", ["no"])[0]) == "yes"
    if outer_lands_only and reference not in values(via, "zone_layer_connections", []):
        return hole_clearance
    return max(values(via, "size")[0] / 2 + 0.20, hole_clearance)


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

    def l4_ground_referenced_nets(self):
        return sorted(net for (layer, net), tracks in self.segments.items()
                      if layer == "B.Cu" and tracks and net not in L4_POWER_AND_WINDING_NETS)

    def test_rotated_pin_one_and_slot_angle(self):
        usb = self.footprints["J2"]
        self.assertEqual(pad_center(usb, "B8"), (161.995, 64.75))
        shell = [pad for pad in usb.pads if pad.drill == (0.6, 1.7)]
        self.assertEqual(len(shell), 2)
        self.assertTrue(all(pad.angle % 180 == 90 for pad in shell))
        self.assertEqual(pad_center(self.footprints["U4"], "1"), (146.755, 63.375))

    def test_duplicate_switch_pads(self):
        self.assertEqual(pad_center(self.footprints["SW1"], "1"), (106, 61.9))

    def test_rear_recovery_probes(self):
        io, ground = (self.footprints[ref].pads[0] for ref in ("TP1", "TP2"))
        self.assertAlmostEqual(math.dist(io.xy, ground.xy), 2.5)
        for probe, net, label in ((io, "BOOT_N", "IO0"), (ground, "GND", "GND")):
            self.assertEqual(probe.net, net)
            self.assertTrue(probe.on_layer("B.Cu"))
            self.assertFalse(probe.on_layer("F.Cu"))
            legends = [values(t, "at")[:2] for t in children(self.board.tree, "gr_text")
                       if t[1] == label and values(t, "layer") == ["B.SilkS"]]
            self.assertTrue(any(math.dist(probe.xy, pos) < 3 for pos in legends), label)
        # Probe the centre and perimeter of the exposed circular IO0 land.
        x, y = io.xy
        self.assertTrue(in_ground_fill(io.xy, self.ground_fills["In2.Cu"]))
        for degree in range(360):
            angle = math.radians(degree)
            edge = (x + io.size[0] * math.cos(angle) / 2, y + io.size[1] * math.sin(angle) / 2)
            self.assertTrue(in_ground_fill(edge, self.ground_fills["In2.Cu"]), edge)

    def test_input_fuse_has_direct_top_layer_power_paths(self):
        for net, start, end, limit in (
            ("VIN_RAW", ("J1", "1"), ("F1", "1"), 6.3),
            ("VIN_FUSED", ("F1", "2"), ("Q1", "5"), 2.8),
        ):
            with self.subTest(net=net):
                self.assertFalse(self.through_via_positions(net))
                self.assertLessEqual(planar_trace_length(
                    self.board, net,
                    ("F.Cu", pad_center(self.footprints[start[0]], start[1])),
                    ("F.Cu", pad_center(self.footprints[end[0]], end[1])),
                    top_only=True,
                ), limit)

    def test_reverse_polarity_gate_clamp_reaches_both_mosfet_pins_on_top(self):
        for net, diode_pin, mosfet_pin in (("V12", "1", "2"), ("REV_GATE", "2", "4")):
            with self.subTest(net=net):
                diode = ("F.Cu", pad_center(self.footprints["D1"], diode_pin))
                mosfet = ("F.Cu", pad_center(self.footprints["Q1"], mosfet_pin))
                self.assertLess(planar_trace_length(self.board, net, diode, mosfet, top_only=True), 3.0)

    def test_routed_vias_clear_smt_pads(self):
        # Same-net pad and via overlap can pass KiCad's copper clearance DRC.
        smt = [
            (footprint.ref, pad)
            for footprint in self.board.footprints
            for pad in footprint.pads
            if pad.kind == "smd" and (pad.on_layer("F.Cu") or pad.on_layer("B.Cu"))
        ]
        # Measure from the copper edge. U1's larger mask opening is checked separately.
        for at, via in self.vias.items():
            drill, = values(via, "drill")
            distance, ref, number = min(
                (pad.edge_distance(at), ref, pad.number) for ref, pad in smt
            )
            gap = distance - drill / 2
            size, = values(via, "size")
            self.assertGreater(distance - size / 2, 1e-6,
                               f"Via land at {at} touches SMT pad {ref}.{number}")
            minimum = 0.20 if values(via, "net")[0] in {"USB_DP_CONN", "USB_DM_CONN"} else 0.125
            self.assertGreaterEqual(gap + 1e-6, minimum,
                                    f"Via drill at {at} too close to SMT pad {ref}.{number}")
            for pad in self.footprints["F1"].pads:
                self.assertGreaterEqual(pad.edge_distance(at) - drill / 2, 0.25,
                                        f"Via at {at} too close to F1.{pad.number}")

    def test_fill_layer_uses_the_drill_diameter_at_each_flash(self):
        # Synthetic locations exercise aperture selection for two drill diameters.
        holes = [("U1", "1", 115.0, -69.0, 0.32), ("U2", "2", 162.9, -63.25, 0.30)]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "sk.gbr"
            write_via_fill_layer(path, holes)
            records = path.read_text().splitlines()
        self.assertIn("%TF.FileFunction,Viafill*%", records)
        self.assertEqual(
            [r for r in records if r.startswith(("%ADD", "D", "X"))],
            ["%ADD10C,0.300*%", "%ADD11C,0.320*%", "D10*", "X162900000Y-63250000D03*",
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

    def test_usb_cc_contacts_reach_their_pulldowns_with_one_bend(self):
        for net, contact, resistor in (("USB_CC1", "A5", "R12"), ("USB_CC2", "B5", "R13")):
            with self.subTest(net=net):
                start = ("F.Cu", pad_center(self.footprints["J2"], contact))
                end = ("F.Cu", pad_center(self.footprints[resistor], "1"))
                self.assertFalse(self.through_via_positions(net))
                self.assertEqual(len(self.segments["F.Cu", net]), 2)
                self.assertLess(planar_trace_length(self.board, net, start, end, top_only=True), 3.5)

    def test_both_usb_vbus_contacts_reach_the_esd_clamp_on_top(self):
        net = "USB_VBUS"
        self.assertFalse(self.through_via_positions(net))
        clamp = ("F.Cu", pad_center(self.footprints["U3"], "5"))
        for pin in ("A4", "A9"):
            start = ("F.Cu", pad_center(self.footprints["J2"], pin))
            with self.subTest(pin=pin):
                self.assertLess(planar_trace_length(
                    self.board, net, start, clamp, top_only=True,
                ), 8.0)

    def test_x_driver_shunt_paths_match_at_each_track_width(self):
        paths = []
        for net, pin, resistor in (("X_SENSE_A", "23", "R17"), ("X_SENSE_B", "27", "R18")):
            by_width = defaultdict(float)
            for track in self.segments["F.Cu", net]:
                width, = values(track, "width")
                by_width[width] += math.dist(values(track, "start"), values(track, "end"))
            length = planar_trace_length(
                self.board, net, ("F.Cu", pad_center(self.footprints["U5"], pin)),
                ("F.Cu", pad_center(self.footprints[resistor], "1")), top_only=True,
            )
            self.assertAlmostEqual(length, sum(by_width.values()))
            paths.append(by_width)
        first, second = paths
        self.assertEqual(first.keys(), second.keys())
        for width in first:
            self.assertAlmostEqual(first[width], second[width], delta=0.01)

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

    def test_usb_bridge_reaches_reset_transistor_inputs_on_top(self):
        for net, bridge_pin, endpoints in (
            ("USB_DTR_N", "13", (("R5", "1", 10.0), ("Q4", "2", 13.5))),
            ("USB_RTS_N", "14", (("Q3", "2", 10.0), ("R6", "1", 8.0))),
        ):
            self.assertFalse(self.through_via_positions(net), net)
            start = ("F.Cu", pad_center(self.footprints["U4"], bridge_pin))
            for ref, pin, limit in endpoints:
                with self.subTest(net=net, ref=ref):
                    end = ("F.Cu", pad_center(self.footprints[ref], pin))
                    self.assertLess(planar_trace_length(
                        self.board, net, start, end, top_only=True,
                    ), limit)

    def test_step_pulldowns_lie_on_the_route_to_each_driver(self):
        for net, gpio, resistor, driver in (
            ("X_STEP", "10", "R31", "U5"), ("Y_STEP", "33", "R32", "U6"),
        ):
            with self.subTest(net=net):
                source = ("F.Cu", pad_center(self.footprints["U2"], gpio))
                junction = ("F.Cu", pad_center(self.footprints[resistor], "1"))
                end = ("F.Cu", pad_center(self.footprints[driver], "16"))
                direct = planar_trace_length(self.board, net, source, end)
                self.assertTrue(math.isfinite(direct))
                to_junction = planar_trace_length(self.board, net, source, junction)
                to_driver = planar_trace_length(self.board, net, junction, end, top_only=True)
                self.assertAlmostEqual(direct, to_junction + to_driver)

    def test_status_lights_use_one_direct_diagonal_each_on_the_bottom(self):
        for net in ("STATUS_IDLE", "STATUS_ALARM"):
            with self.subTest(net=net):
                vias = self.through_via_positions(net)
                self.assertEqual(len(vias), 2)
                a, b = sorted(vias)
                self.assertAlmostEqual(b[0] - a[0], a[1] - b[1])
                length = sum(math.dist(values(track, "start"), values(track, "end"))
                             for track in self.segments["B.Cu", net])
                self.assertAlmostEqual(length, math.dist(a, b))

    def test_solenoid_switch_polarity_and_default_off_paths(self):
        expected = {
            "Q6": {"1": "V12", "2": "V12", "3": "V12", "4": "SOL_GATE",
                   "5": "SOL_POS", "6": "SOL_POS", "7": "SOL_POS", "8": "SOL_POS"},
            "Q7": {"1": "SOL_ENABLE", "2": "GND", "3": "SOL_GATE_SINK"},
            "R21": {"1": "SOL_SAFE", "2": "SOL_ENABLE"},
            "R22": {"1": "SOL_ENABLE", "2": "GND"},
            "R33": {"1": "V12", "2": "SOL_GATE"},
            "R45": {"1": "SOL_GATE_SINK", "2": "SOL_GATE"},
            "D4": {"1": "SOL_POS", "2": "GND"},
            "J5": {"1": "SOL_POS", "2": "GND"},
        }
        for ref, pin_nets in expected.items():
            with self.subTest(ref=ref):
                actual = {pad.number: pad.net for pad in self.footprints[ref].pads if pad.number}
                self.assertEqual(actual, pin_nets)

    def test_interlock_signals_stay_on_top(self):
        for net in INTERLOCK_SIGNALS:
            with self.subTest(net=net):
                layers = {layer for (layer, name), tracks in self.segments.items()
                          if name == net and tracks}
                self.assertEqual(layers, {"F.Cu"})
                self.assertFalse(self.through_via_positions(net))

    def plated_ground_returns_to_l2(self):
        returns = self.through_via_positions("GND")
        returns.update(
            pad.xy for footprint in self.board.footprints for pad in footprint.pads
            if pad.net == "GND" and pad.kind == "thru_hole"
            and pad.on_layer("In1.Cu") and pad.on_layer("In2.Cu")
        )
        return {at for at in returns if in_ground_fill(at, self.ground_fills["In1.Cu"])}

    def test_each_l3_ground_region_has_two_plated_returns_to_l2(self):
        fills = self.ground_fills
        grounded = self.plated_ground_returns_to_l2()
        self.assertTrue(fills["In2.Cu"])
        for region in fills["In2.Cu"]:
            count = sum(in_ground_fill(at, [region]) for at in grounded)
            self.assertGreaterEqual(count, 2,
                                    f"L3 ground region near {region[0][1:]} needs two L2 returns")

    def test_l3_ground_regions_cover_their_local_devices(self):
        def thermal_holes(ref):
            holes = [p.xy for p in self.footprints[ref].pads
                     if p.kind == "thru_hole" and p.net == "GND"]
            self.assertTrue(holes, ref)
            return holes

        usb_contacts = [pad_center(self.footprints["J2"], pin)
                        for pin in ("A6", "A7", "B6", "B7")]
        regions = self.ground_fills["In2.Cu"]
        assigned = set()
        for name, points in (("J2 and U3", usb_contacts + [pad_center(self.footprints["U3"], "2")]),
                             ("U2 and U5", thermal_holes("U2") + thermal_holes("U5")),
                             ("U6", thermal_holes("U6"))):
            with self.subTest(region=name):
                matches = [i for i, region in enumerate(regions)
                           if all(in_ground_fill(at, [region]) for at in points)]
                self.assertEqual(len(matches), 1)
                self.assertNotIn(matches[0], assigned)
                assigned.add(matches[0])

    def test_l3_3v3_plane_connects_regulator_and_driver_feeds(self):
        regions = plane_fills(self.board, "V3V3")["In2.Cu"]
        self.assertEqual(len(regions), 1, "3.3 V must be continuous on L3")
        power_vias = self.through_via_positions("V3V3")
        output = pad_center(self.footprints["C5"], "1")
        nearby = [at for at in power_vias if math.dist(at, output) < 2]
        self.assertEqual(len(nearby), 2, "C5 needs two local 3.3 V plane feeds")
        for at in nearby:
            self.assertLess(planar_trace_length(self.board, "V3V3", ("F.Cu", output),
                                                ("F.Cu", at), top_only=True), 2)
        # The U6 feeds land beside C23 / VCC_IO and the MS2 address pin.
        for at in (*nearby, (151.725, 80.09), (153.3, 84.5)):
            with self.subTest(at=at):
                self.assertIn(at, power_vias)
                self.assertTrue(in_ground_fill(at, regions))

    def test_l3_3v3_feed_across_the_north_edge_keeps_its_width(self):
        supply = plane_fills(self.board, "V3V3")["In2.Cu"]
        # Probe the filled copper from the ESP32 across to the USB side.
        # Connectivity alone also accepts the former 0.49 mm neck.
        for start_x, end_x, width in ((125, 149, 3.3), (149, 162, 4.0)):
            rows = math.ceil(width / 0.25)
            for column in range(4 * (end_x - start_x) + 1):
                x = start_x + column / 4
                for row in range(rows + 1):
                    at = (x, 50.51 + width * row / rows)
                    self.assertTrue(in_ground_fill(at, supply), at)

    def test_buck_feedback_senses_c5_and_returns_at_u1_on_top(self):
        def pad(ref, pin):
            return ("F.Cu", pad_center(self.footprints[ref], pin))

        fb, = [p.net for p in self.footprints["U1"].pads if p.number == "4"]
        for net, start, end, max_length in (
            ("V3V3", pad("C5", "1"), pad("R43", "1"), 12),
            (fb, pad("U1", "4"), pad("R43", "2"), 6),
            (fb, pad("U1", "4"), pad("C35", "2"), 8),
            (fb, pad("U1", "4"), pad("R44", "1"), 3),
            ("GND", pad("R44", "2"), pad("U1", "1"), 8),
        ):
            with self.subTest(net=net, start=start, end=end):
                length = planar_trace_length(self.board, net, start, end, top_only=True)
                self.assertLess(length, max_length)
        self.assertTrue(self.segments["F.Cu", fb])
        self.assertFalse(self.through_via_positions(fb))
        self.assertFalse(in_ground_fill(pad("R44", "2")[1], self.ground_fills["F.Cu"]))
        for track in self.segments["F.Cu", fb]:
            for point in track_samples(track):
                self.assertTrue(in_ground_fill(point, self.ground_fills["In1.Cu"]), point)

    def test_buck_ddc_lands_keep_mask_clear_of_via_drills(self):
        regulator = self.footprints["U1"]
        footprint = next(n for n in children(self.board.tree, "footprint")
                         if n[1] == regulator.land)
        margin, = values(footprint, "solder_mask_margin")
        self.assertAlmostEqual(margin, 0.05)
        self.assertEqual(len(regulator.pads), 6)
        for pad in regulator.pads:
            self.assertEqual(pad.size, (1.1, 0.6))
            for at, via in self.vias.items():
                drill, = values(via, "drill")
                self.assertGreaterEqual(pad.edge_distance(at) - margin - drill / 2, 0.125)

    def test_usb_bridge_and_x_driver_take_power_between_pin_and_bypass_capacitor(self):
        net = "V3V3"
        regions = plane_fills(self.board, net)["In2.Cu"]
        feeds = [at for at in self.through_via_positions(net) if in_ground_fill(at, regions)]
        for chip, pin, cap in (("U4", "4", "C11"), ("U5", "15", "C16")):
            with self.subTest(chip=chip, pin=pin, capacitor=cap):
                start = ("F.Cu", pad_center(self.footprints[chip], pin))
                end = ("F.Cu", pad_center(self.footprints[cap], "1"))
                # A shortest 45-degree route covers the smaller offset diagonally.
                diagonal, major = sorted(abs(a - b) for a, b in zip(start[1], end[1]))
                direct = major - diagonal + math.sqrt(2) * diagonal
                self.assertAlmostEqual(planar_trace_length(self.board, net, start, end, top_only=True), direct)
                via_paths = []
                for at in feeds:
                    if math.dist(start[1], at) < direct:
                        via = ("F.Cu", at)
                        to_via = planar_trace_length(self.board, net, start, via, top_only=True)
                        to_cap = planar_trace_length(self.board, net, via, end, top_only=True)
                        via_paths.append(to_via + to_cap)
                self.assertAlmostEqual(min(via_paths, default=math.inf), direct)

    def test_motor_uart_crossing_continues_straight_into_the_x_driver(self):
        vias = sorted(self.through_via_positions("TMC_BUS"))
        self.assertEqual(len(vias), 2)
        pin = pad_center(self.footprints["U5"], "14")
        for at in vias:
            self.assertAlmostEqual(at[1], pin[1])
        length = planar_trace_length(self.board, "TMC_BUS", ("B.Cu", vias[1]), ("F.Cu", pin))
        self.assertAlmostEqual(length, math.dist(vias[1], pin))

    def test_power_led_has_a_direct_feed_from_the_3v3_plane(self):
        # Keep LED current on its own plane feed, away from the buck pickup.
        regions = plane_fills(self.board, "V3V3")["In2.Cu"]
        led_feed = ("F.Cu", pad_center(self.footprints["R2"], "1"))
        self.assertTrue(any(
            in_ground_fill(at, regions) and math.isfinite(planar_trace_length(
                self.board, "V3V3", led_feed, ("F.Cu", at), top_only=True,
            ))
            for at in self.through_via_positions("V3V3")
        ))

    def test_12v_feed_vias_share_the_input_bulk_capacitor_plane(self):
        bulk = pad_center(self.footprints["C1"], "1")
        regions = plane_fills(self.board, "V12")["In2.Cu"]
        self.assertEqual(len(regions), 1, "12 V must be continuous on L3")
        supply = [region for region in regions if in_ground_fill(bulk, [region])]
        self.assertEqual(len(supply), 1, "C1.1 must land on the L3 12 V plane")
        for at in self.through_via_positions("V12"):
            self.assertTrue(in_ground_fill(at, supply), f"Isolated L3 12 V feed at {at}")

    def test_control_tracks_keep_adjacent_ground(self):
        for layer, reference, nets in (
            ("F.Cu", "In1.Cu", ("X_STEP", "X_DIR", "Y_STEP", "Y_DIR", "TMC_BUS",
                                "ESP_RX", "ESP_TX", "TMC_RX", "TMC_TX", "BOOT_N", "BOOT_BASE", "USB_DTR_N", "USB_RTS_N",
                                "SOL_GATE", "SOL_GATE_SINK", "USB_CC1", "USB_CC2", "USB_VBUS", "USB_OE_N",
                                "USB_DETECT_BASE", "X_SENSE_A", "X_SENSE_B",
                                "STATUS_IDLE", "STATUS_ALARM",
                                *INTERLOCK_SIGNALS)),
            ("B.Cu", "In2.Cu", self.l4_ground_referenced_nets()),
        ):
            for net in nets:
                # The ground zone clears the via land by 0.20 mm or the drill
                # by 0.30 mm. Allow 0.04 mm for rounding at the fill boundary.
                antipads = [
                    (at, via_plane_clearance_radius(v, reference) + 0.04)
                    for at, v in self.vias.items() if values(v, "net") == [net]
                ]
                tracks = self.segments[layer, net]
                for point in samples_outside_antipads(tracks, antipads):
                    self.assertTrue(in_ground_fill(point, self.ground_fills[reference]),
                                    (layer, net, point))

    def test_l4_signal_transitions_have_local_ground_returns(self):
        self.assertEqual(len(self.ground_fills["In1.Cu"]), 1)
        grounded = self.plated_ground_returns_to_l2()
        for net in self.l4_ground_referenced_nets():
            tracks = self.segments["B.Cu", net]
            samples = [p for segment in tracks for p in track_samples(segment)]
            for at in self.through_via_positions(net):
                land_radius = values(self.vias[at], "size")[0] / 2
                if not any(math.dist(p, at) <= land_radius for p in samples):
                    continue
                with self.subTest(net=net, via=at):
                    nearby = [p for p in grounded if math.dist(p, at) <= 2.0]
                    regions = [r for r in self.ground_fills["In2.Cu"]
                               if any(in_ground_fill(p, [r]) for p in nearby)]
                    # Probe the outgoing copper just beyond the via clearance.
                    radius = via_plane_clearance_radius(self.vias[at], "In2.Cu")
                    launch = [p for p in samples
                              if radius + 0.06 <= math.dist(p, at) <= radius + 0.25]
                    self.assertTrue(launch, "Missing bottom-layer launch samples")
                    self.assertTrue(all(in_ground_fill(p, regions) for p in launch),
                                    "Launch needs a plated L2 return in its L3 ground region")

    def test_motor_outputs_keep_adjacent_ground_to_connectors(self):
        for connector in ("J3", "J4"):
            for pad in self.footprints[connector].pads:
                with self.subTest(connector=connector, pin=pad.number, net=pad.net):
                    vias = self.through_via_positions(pad.net)
                    self.assertEqual(bool(vias), pad.net != "X_B2")
                    for layer, reference in (("F.Cu", "In1.Cu"), ("B.Cu", "In2.Cu")):
                        tracks = self.segments[layer, pad.net]
                        self.assertEqual(bool(tracks), layer == "F.Cu" or pad.net != "X_B2")
                        antipads = [(at, via_plane_clearance_radius(self.vias[at], reference) + 0.04)
                                    for at in vias]
                        for point in samples_outside_antipads(tracks, antipads):
                            # The reference plane clears the plated connector land by 0.20 mm.
                            if pad.edge_distance(point) > 0.20 + 0.04:
                                self.assertTrue(in_ground_fill(point, self.ground_fills[reference]),
                                                (pad.net, reference, point))

    def test_input_tvs_has_two_local_returns_to_input_ground(self):
        bulk = pad_center(self.footprints["C1"], "2")
        jack = pad_center(self.footprints["J1"], "2")
        anode = pad_center(self.footprints["D2"], "2")
        input_ground, = [r for r in self.ground_fills["In1.Cu"]
                         if in_ground_fill(bulk, [r]) and in_ground_fill(jack, [r])]
        returns = [at for at in self.through_via_positions("GND")
                   if math.dist(at, anode) <= 2.5 and in_ground_fill(at, [input_ground])]
        top = self.ground_fills["F.Cu"]
        direct = [
            at for at in returns
            if all(in_ground_fill(p, top) for p in copper_strip_samples(anode, at, 0.8))
        ]
        self.assertGreaterEqual(len(direct), 2, "D2 needs two short, wide returns to L2")

    def test_usb_c_breakout_vias_and_ground_returns(self):
        fills = self.ground_fills
        u3_ground = pad_center(self.footprints["U3"], "2")
        usb_region, = [region for region in fills["In2.Cu"] if in_ground_fill(u3_ground, [region])]
        for stitch in ((157.50, 59.56), (160.25, 61.88), (163.68, 62.22), (165.04, 62.12),
                       (165.04, 63.93), (158.77, 63.60)):
            with self.subTest(stitch=stitch):
                via = self.vias[stitch]
                self.assertEqual(values(via, "net"), ["GND"])
                self.assertEqual(values(via, "layers"), ["F.Cu", "B.Cu"])
                self.assertTrue(in_ground_fill(stitch, [usb_region]))
                for layer in ("In1.Cu", "B.Cu"):
                    self.assertTrue(in_ground_fill(stitch, fills[layer]), layer)

        for net, j2_pin, _ in USB_C_CONTACTS:
            vias = {at: v for at, v in self.vias.items() if values(v, "net") == [net]}
            self.assertEqual(len(vias), 2)
            u3_pin = "1" if net == "USB_DP_CONN" else "3"
            for ref, pin in (("J2", j2_pin), ("U3", u3_pin)):
                pad = pad_center(self.footprints[ref], pin)
                self.assertEqual(sum(math.dist(at, pad) <= 1.25 for at in vias), 1)
            for via in vias.values():
                tenting, = children(via, "tenting")
                for side in ("front", "back"):
                    self.assertEqual(str(values(tenting, side)[0]), "yes")
                for treatment in ("filling", "capping"):
                    self.assertEqual(str(values(via, treatment)[0]), "no")
                self.assertEqual(values(via, "size"), [0.60])
                self.assertEqual(values(via, "drill"), [0.30])
                self.assertEqual(values(via, "layers"), ["F.Cu", "B.Cu"])
            # Start/end-only lands leave the drill plus 0.30 mm clearance on
            # each inner plane. Allow 0.01 mm for KiCad's polygon approximation.
            antipad_radius = 0.30 / 2 + 0.30 + 0.01
            antipads = [(at, antipad_radius) for at in vias]
            for signal, reference in (("F.Cu", "In1.Cu"), ("B.Cu", "In2.Cu")):
                samples = list(samples_outside_antipads(self.segments[signal, net], antipads))
                self.assertTrue(samples, (signal, net))
                for point in samples:
                    self.assertTrue(in_ground_fill(point, fills[reference]), (net, point))
