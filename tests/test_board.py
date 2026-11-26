"""Geometry regressions for footprint placement and USB-C routing."""

import heapq
import json
import math
import re
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


def shortest_45_length(start, end):
    """Shortest horizontal, vertical and 45-degree path between two points."""
    diagonal, major = sorted(abs(a - b) for a, b in zip(start, end))
    return major - diagonal + math.sqrt(2) * diagonal


def planar_trace_length(board, net, start, end, *, top_only=False, segments=None):
    """Return the shortest planar trace length in millimetres."""
    edges = defaultdict(list)

    def connect(a, b, length):
        edges[a].append((b, length))
        edges[b].append((a, length))

    if segments is None:
        segments = children(board.tree, "segment")
    for segment in segments:
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
            for layer in ("In1.Cu", "In2.Cu", bottom):
                connect((top, at), (layer, at), 0)

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

    def test_routed_copper_uses_45_degree_increments(self):
        self.assertFalse(children(self.board.tree, "arc"), "Found a curved copper track")
        for (layer, net), tracks in self.segments.items():
            directions = defaultdict(list)
            for track in tracks:
                start, end = (tuple(values(track, key)) for key in ("start", "end"))
                # Compare exact offsets at KiCad's native nanometre resolution.
                dx, dy = (round(b * 1_000_000) - round(a * 1_000_000) for a, b in zip(start, end))
                detail = (layer, net, start, end)
                self.assertNotEqual((dx, dy), (0, 0), detail)
                self.assertTrue(dx == 0 or dy == 0 or abs(dx) == abs(dy), detail)
                directions[start].append((dx, dy))
                directions[end].append((-dx, -dy))

            terminals = {p.xy for f in self.footprints.values() for p in f.pads
                         if p.net == net and p.on_layer(layer)}
            terminals.update(at for at, via in self.vias.items() if values(via, "net") == [net])
            for point, vectors in directions.items():
                if len(vectors) == 2 and point not in terminals:
                    (ax, ay), (bx, by) = vectors
                    # Outward vectors meet at 135 or 180 degrees at a free bend.
                    self.assertLess(ax * bx + ay * by, 0, (layer, net, point))

    def test_rotated_pin_one_and_slot_angle(self):
        usb = self.footprints["J2"]
        self.assertEqual(pad_center(usb, "B8"), (161.995, 64.75))
        shell = [pad for pad in usb.pads if pad.drill == (0.6, 1.7)]
        self.assertEqual(len(shell), 2)
        self.assertTrue(all(pad.angle % 180 == 90 for pad in shell))
        self.assertEqual(pad_center(self.footprints["U4"], "1"), (151.15, 60.97))

    def test_board_pads_are_horizontal_or_vertical(self):
        for footprint in self.board.footprints:
            for pad in footprint.pads:
                self.assertAlmostEqual(math.remainder(pad.angle, 90), 0, msg=(footprint.ref, pad.number))

    def test_fitted_chip_resistors_and_capacitors_are_at_least_0402(self):
        for part in self.board.footprints:
            if "smd" not in part.attributes or part.attributes & {"dnp", "board_only"}:
                continue
            if not re.fullmatch(r"[RC]\d+", part.ref):
                continue
            with self.subTest(ref=part.ref, footprint=part.land):
                # KiCad's metric suffix gives nominal body dimensions in tenths of a millimetre.
                size = re.search(r"_(\d{2})(\d{2})Metric(?:_|$)", part.land)
                self.assertIsNotNone(size, "Expected metric body dimensions for this chip footprint")
                width, length = sorted(map(int, size.groups()))
                self.assertGreaterEqual(width, 5)
                self.assertGreaterEqual(length, 10)

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

    def test_cp2102n_self_powered_circuit(self):
        def nets(ref):
            return {p.number: p.net for p in self.footprints[ref].pads if p.number}

        bridge = nets("U4")
        self.assertEqual(self.footprints["U4"].fields["MPN"], "CP2102N-A02-GQFN24R")
        for pin in ("5", "6", "7"):
            self.assertEqual(bridge[pin], "V3V3")
        for pin in ("2", "25"):
            self.assertEqual(bridge[pin], "GND")
        self.assertEqual((bridge["19"], bridge["20"], bridge["21"], bridge["23"]),
                         ("USB_RTS_N", "ESP_TX", "ESP_RX", "USB_DTR_N"))
        self.assertEqual(self.footprints["U3"].fields["MPN"], "TPD4E05U06DQAR")
        clamp = nets("U3")
        self.assertEqual({pin: net for pin, net in clamp.items()
                          if not net.startswith("unconnected-")}, {
            "1": bridge["4"], "2": bridge["3"], "3": "GND", "5": "USB_VBUS",
            "8": "GND", "9": bridge["3"], "10": bridge["4"],
        })
        self.assertEqual({pin for pin, net in clamp.items() if net.startswith("unconnected-")},
                         {"4", "6", "7"})
        self.assertEqual((bridge["3"], bridge["4"]), ("USB_DP_CONN", "USB_DM_CONN"))
        for ref, value, net1, net2 in (
            ("R29", "22.1k", "USB_VBUS", bridge["8"]),
            ("R30", "47.5k", bridge["8"], "GND"),
            ("R47", "1k", "V3V3", bridge["9"]),
        ):
            self.assertEqual(self.footprints[ref].fields["Value"], value)
            self.assertEqual(nets(ref), {"1": net1, "2": net2})
        for ref in ("C10", "C11", "C29", "C36", "C37", "C38"):
            self.assertEqual(nets(ref), {"1": "V3V3", "2": "GND"})
            expected = "100n / 16V" if ref in {"C10", "C11", "C29"} else "4.7u / 16V"
            self.assertEqual(self.footprints[ref].fields["Value"], expected)

    def test_usb_c_duplicate_contact_ties(self):
        connector = self.footprints["J2"]
        plus, minus = "USB_DP_CONN", "USB_DM_CONN"
        a6, b6, a7, b7 = (("F.Cu", pad_center(connector, pin)) for pin in ("A6", "B6", "A7", "B7"))
        pad = next(p for p in connector.pads if p.number == "A7")
        row_x, row_y = pad.xy

        self.assertFalse(self.through_via_positions(plus))
        self.assertFalse(self.segments["B.Cu", plus])
        right = [s for s in self.segments["F.Cu", plus]
                 if min(values(s, "start")[0], values(s, "end")[0]) >= row_x]
        length = planar_trace_length(self.board, plus, a6, b6, top_only=True, segments=right)
        self.assertLessEqual(length, 3.5)
        crossing, = [s for s in right if min(values(s, "start")[1], values(s, "end")[1]) <
                     row_y < max(values(s, "start")[1], values(s, "end")[1])]
        x, _ = values(crossing, "start")
        self.assertEqual(x, values(crossing, "end")[0])
        self.assertGreater(pad.edge_distance((x, row_y)), 0)
        self.assertEqual(values(crossing, "width"), [0.39])

        vias = self.through_via_positions(minus)
        self.assertEqual(len(vias), 2)
        for x, _ in vias:
            self.assertLess(x, row_x)
            self.assertGreater(pad.edge_distance((x, row_y)), 0)
        self.assertTrue(math.isinf(planar_trace_length(self.board, minus, a7, b7, top_only=True)))
        tie = planar_trace_length(self.board, minus, a7, b7)
        self.assertLessEqual(round(tie, 2), 4.15)
        upper, lower = sorted(vias, key=lambda xy: xy[1])
        bottom = self.segments["B.Cu", minus]
        self.assertEqual(len(bottom), 2)
        for segment in bottom:
            self.assertEqual(values(segment, "width"), [0.364])
        crossing_length = planar_trace_length(
            self.board, minus, ("B.Cu", upper), ("B.Cu", lower), segments=bottom,
        )
        self.assertAlmostEqual(crossing_length, shortest_45_length(upper, lower))
        self.assertLessEqual(crossing_length, 1.50)

        # A7 reaches its via by branching perpendicularly off the straight pair.
        tap = (upper[0], row_y)
        branch = planar_trace_length(self.board, minus, ("F.Cu", tap), ("F.Cu", upper), top_only=True)
        self.assertAlmostEqual(branch, row_y - upper[1])
        lead = planar_trace_length(self.board, minus, b7, ("F.Cu", lower), top_only=True)
        self.assertAlmostEqual(lead, shortest_45_length(b7[1], lower))

    def test_usb_cc_contacts_reach_their_pulldowns_with_at_most_one_exposed_bend(self):
        for net, contact, resistor in (("USB_CC1", "A5", "R12"), ("USB_CC2", "B5", "R13")):
            with self.subTest(net=net):
                pads = [next(p for p in self.footprints[ref].pads if p.number == number)
                        for ref, number in (("J2", contact), (resistor, "1"))]
                start, end = (("F.Cu", p.xy) for p in pads)
                self.assertFalse(self.through_via_positions(net))
                # A centring segment wholly inside an SMT land adds no exposed bend.
                exposed = [s for s in self.segments["F.Cu", net] if not any(
                    all(p.edge_distance(values(s, k)) <= 0 for k in ("start", "end")) for p in pads
                )]
                self.assertLessEqual(len(exposed), 2)
                length = planar_trace_length(self.board, net, start, end, top_only=True)
                self.assertLess(length, 3.5)
                self.assertAlmostEqual(length, shortest_45_length(start[1], end[1]))

    def test_both_usb_vbus_contacts_reach_the_esd_clamp_on_top(self):
        net = "USB_VBUS"
        self.assertFalse(self.through_via_positions(net))
        a9, a4 = (("F.Cu", pad_center(self.footprints["J2"], pin)) for pin in ("A9", "A4"))
        right = [s for s in self.segments["F.Cu", net]
                 if min(values(s, "start")[0], values(s, "end")[0]) >= a9[1][0]]
        self.assertLessEqual(len(right), 5)
        self.assertLess(planar_trace_length(self.board, net, a9, a4, top_only=True, segments=right), 7.8)
        clamp = ("F.Cu", pad_center(self.footprints["U3"], "5"))
        bypass = ("F.Cu", pad_center(self.footprints["C12"], "1"))
        self.assertLess(planar_trace_length(self.board, net, clamp, bypass, top_only=True), 1.5)
        for pin, limit in (("A4", 4.8), ("A9", 12.8)):
            start = ("F.Cu", pad_center(self.footprints["J2"], pin))
            with self.subTest(pin=pin):
                self.assertLess(planar_trace_length(
                    self.board, net, start, clamp, top_only=True,
                ), limit)

    def test_corexy_profile_matches_the_gantry_and_motor_connectors(self):
        config = (Path(__file__).resolve().parents[1] / "firmware/config.yaml").read_text()
        self.assertRegex(config, r"(?m)^kinematics:\n  CoreXY:\n    x_scaler: 1\.0$")
        for axis, travel, address, step, direction in (
            ("x", 110, 0, 25, 26),  # J3 X MOTOR, right motor B
            ("y", 200, 1, 21, 22),   # J4 Y MOTOR, left motor A
        ):
            with self.subTest(axis=axis):
                block = re.search(rf"^  {axis}:\n((?:    .*\n)+)", config, re.MULTILINE)
                self.assertIsNotNone(block)
                self.assertIn("    motor0:\n      tmc_2209:\n", block[1])
                settings = dict(
                    line.strip().split(": ", 1) for line in block[1].splitlines() if ": " in line
                )
                self.assertEqual(float(settings["steps_per_mm"]), 80)
                self.assertEqual(int(settings["microsteps"]), 16)
                self.assertEqual(float(settings["max_travel_mm"]), travel)
                self.assertEqual(int(settings["addr"]), address)
                self.assertEqual(settings["step_pin"], f"gpio.{step}")
                self.assertEqual(settings["direction_pin"].split(":")[0], f"gpio.{direction}")

    def test_motor_profile_matches_the_shunts_on_both_axes(self):
        config = (Path(__file__).resolve().parents[1] / "firmware/config.yaml").read_text()
        for axis, references in (("x", ("R17", "R18")), ("y", ("R19", "R20"))):
            with self.subTest(axis=axis):
                block = re.search(rf"^  {axis}:\n((?:    .*\n)+)", config, re.MULTILINE)
                self.assertIsNotNone(block)
                setting = re.search(r"^        r_sense_ohms: ([\d.]+)$", block[1], re.MULTILINE)
                self.assertIsNotNone(setting)
                run = re.search(r"^        run_amps: ([\d.]+)$", block[1], re.MULTILINE)
                self.assertIsNotNone(run)
                self.assertAlmostEqual(float(run[1]), 0.800)
                for ref in references:
                    resistance = float(self.footprints[ref].fields["Value"].split("R")[0])
                    self.assertEqual(resistance, float(setting[1]))

    def test_idle_startup_turns_outputs_off_before_releasing_interlock(self):
        config = (Path(__file__).resolve().parents[1] / "firmware/config.yaml").read_text()
        self.assertIn('  after_reset: "M5&$MD&M64 P0"', config.splitlines())
        self.assertIn("  digital0_pin: gpio.27", config.splitlines())
        self.assertIn("  shared_stepper_disable_pin: gpio.13:high", config.splitlines())

    def test_solenoid_pwm_matches_the_first_article_profile(self):
        config = (Path(__file__).resolve().parents[1] / "firmware/config.yaml").read_text()
        pwm = re.search(r"^PWM:\n((?:  .*\n)+)", config, re.MULTILINE)
        self.assertIsNotNone(pwm)
        settings = dict(line.strip().split(": ", 1) for line in pwm[1].splitlines())
        self.assertEqual(int(settings["pwm_hz"]), 1000)
        self.assertEqual(settings["output_pin"], "gpio.32")
        self.assertEqual(settings["speed_map"], "0=0% 1000=100%")

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
            self.assertEqual(values(layers[name], "epsilon_r"), [4.4])
        settings = self.project["net_settings"]
        usb = next(c for c in settings["classes"] if c["name"] == "USB data")
        width, gap = 0.28, 0.22
        self.assertEqual((usb["diff_pair_width"], usb["diff_pair_gap"]), (width, gap))
        self.assertEqual(usb["track_width"], width)
        plus, minus = "USB_DP_CONN", "USB_DM_CONN"
        for net in (plus, minus):
            self.assertIn("USB data", settings["netclass_assignments"][net])
        # Sample the coupled straight runs from the bridge fanout through U3 to J2.
        for x in (154.1, 154.72, 157.55, 158.36, 159.6, 160.4, 161.1):
            with self.subTest(x=x):
                pair = []
                for net, pin in ((plus, "A6"), (minus, "A7")):
                    _, lane_y = pad_center(self.footprints["J2"], pin)
                    hits = []
                    for track in self.segments["F.Cu", net]:
                        (ax, ay), (bx, by) = (values(track, end) for end in ("start", "end"))
                        if ay == by == lane_y and min(ax, bx) < x < max(ax, bx):
                            hits.append(track)
                    self.assertEqual(len(hits), 1, net)
                    self.assertEqual(values(hits[0], "width"), [width])
                    pair.append(hits[0])
                self.assertAlmostEqual(overlapping_track_pitch(*pair) - width, gap)

    def test_usb_main_pair_runs_on_top_over_l2_from_j2_through_u3_to_u4(self):
        width = next(c["diff_pair_width"] for c in self.project["net_settings"]["classes"]
                     if c["name"] == "USB data")
        for net, contact, entry, clamp, bridge in (
            ("USB_DP_CONN", "A6", "9", "2", "3"),
            ("USB_DM_CONN", "A7", "10", "1", "4"),
        ):
            with self.subTest(net=net):
                start, pass_pad, active, end = (
                    ("F.Cu", pad_center(self.footprints[ref], pin))
                    for ref, pin in (("J2", contact), ("U3", entry), ("U3", clamp), ("U4", bridge))
                )
                # The A7 via branches off the straight pair. Its L2 opening
                # can overlap the trace, but its drill must clear the full width.
                openings = []
                if contact == "A7":
                    at = min(self.through_via_positions(net), key=lambda p: math.dist(p, start[1]))
                    drill, = values(self.vias[at], "drill")
                    self.assertGreater(start[1][1] - at[1], (width + drill) / 2)
                    openings.append((at, via_plane_clearance_radius(self.vias[at], "In1.Cu") + 0.01))
                grounded = [s for s in self.segments["F.Cu", net] if all(
                    in_ground_fill(p, self.ground_fills["In1.Cu"])
                    for p in samples_outside_antipads([s], openings))]
                distance = 0
                nodes = [start, pass_pad, active, end]
                for a, b in zip(nodes, nodes[1:]):
                    tracks = [s for s in grounded if values(s, "width") == [width]] if a == start else grounded
                    length = planar_trace_length(self.board, net, a, b, top_only=True, segments=tracks)
                    if b != end:
                        self.assertAlmostEqual(length, shortest_45_length(a[1], b[1]))
                    else:
                        self.assertLess(length, 7.2)
                    distance += length
                self.assertAlmostEqual(distance, planar_trace_length(self.board, net, start, end))
                self.assertTrue(all(active[1][0] < pass_pad[1][0] < x and
                                    math.dist((x, y), start[1]) < 2.0
                                    for x, y in self.through_via_positions(net)))

    def test_usb_route_lengths_in_both_plug_orientations(self):
        lengths = defaultdict(list)
        general, = children(self.board.tree, "general")
        thickness, = values(general, "thickness")
        for net, a_pin, b_pin in USB_C_CONTACTS:
            bridge = next(p.xy for p in self.footprints["U4"].pads if p.net == net)
            for pin in (a_pin, b_pin):
                start = ("F.Cu", pad_center(self.footprints["J2"], pin))
                length = planar_trace_length(self.board, net, start, ("F.Cu", bridge))
                self.assertTrue(math.isfinite(length), (pin, net))
                top = planar_trace_length(self.board, net, start, ("F.Cu", bridge), top_only=True)
                self.assertEqual(math.isfinite(top), pin != "B7")
                if pin == "B7":
                    length += 2 * thickness
                lengths[pin[0]].append(length)
        for orientation, (plus, minus) in lengths.items():
            self.assertLessEqual(abs(plus - minus), 1.27, orientation)

    def test_usb_bridge_and_bypass_capacitors_have_local_ground_vias(self):
        ground = self.ground_fills["In1.Cu"]
        returns = [at for at in self.through_via_positions("GND") if in_ground_fill(at, ground)]
        for ref, limit in (("U4", 1.15), ("C10", 0.8), ("C11", 1.8), ("C29", 0.8), ("C12", 0.9)):
            start = ("F.Cu", pad_center(self.footprints[ref], "2"))
            with self.subTest(ref=ref):
                lengths = [planar_trace_length(self.board, "GND", start, ("F.Cu", at), top_only=True)
                           for at in returns if math.dist(start[1], at) < limit]
                self.assertLess(min(lengths, default=math.inf), limit)

    def test_usb_bridge_reset_branches(self):
        for net, bridge_pin, destinations in (
            ("USB_DTR_N", "23", (("R8", "2", 3.2), ("R5", "1", 6.5), ("Q4", "2", 4.5))),
            ("USB_RTS_N", "19", (("R7", "2", 9.0), ("R6", "1", 3.7), ("Q3", "2", 6.0))),
        ):
            start = ("F.Cu", pad_center(self.footprints["U4"], bridge_pin))
            self.assertFalse(self.through_via_positions(net), net)
            for ref, pin, limit in destinations:
                with self.subTest(net=net, ref=ref):
                    end = ("F.Cu", pad_center(self.footprints[ref], pin))
                    self.assertLess(planar_trace_length(self.board, net, start, end, top_only=True), limit)

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

    def test_motor_controls_turn_once_on_l4_and_step_continues_through_its_via(self):
        for net, x_direction in (("X_STEP", -1), ("X_DIR", -1), ("Y_STEP", 1), ("Y_DIR", 1)):
            with self.subTest(net=net):
                vias = self.through_via_positions(net)
                self.assertEqual(len(vias), 2)
                source, driver = sorted(vias, key=lambda at: at[1])
                tracks = self.segments["B.Cu", net]
                self.assertEqual(len(tracks), 2)
                ends = [{tuple(values(s, k)) for k in ("start", "end")} for s in tracks]
                corner, = ends[0] & ends[1]
                self.assertEqual(ends[0] ^ ends[1], vias)
                self.assertEqual(corner[0], source[0])
                self.assertGreater(corner[1], source[1])
                self.assertGreater(driver[1], corner[1])
                self.assertAlmostEqual(x_direction * (driver[0] - corner[0]), driver[1] - corner[1])
                if net.endswith("_STEP"):
                    resistor = "R31" if net == "X_STEP" else "R32"
                    pad = pad_center(self.footprints[resistor], "1")
                    length = planar_trace_length(
                        self.board, net, ("B.Cu", corner), ("F.Cu", pad),
                    )
                    self.assertAlmostEqual(length, math.dist(corner, pad))

    def test_status_lights_run_on_top_from_gpio_to_each_led_row(self):
        for net, pin, pull, series, led in (
            ("STATUS_IDLE", "30", "R26", "R24", "D7"),
            ("STATUS_ALARM", "31", "R27", "R25", "D8"),
        ):
            with self.subTest(net=net):
                self.assertFalse(self.through_via_positions(net))
                gpio, tap, end = (("F.Cu", pad_center(self.footprints[r], p))
                                  for r, p in (("U2", pin), (pull, "1"), (series, "1")))
                to_tap = planar_trace_length(self.board, net, gpio, tap, top_only=True)
                total = planar_trace_length(self.board, net, gpio, end, top_only=True)
                self.assertLess(total, 9.5)
                self.assertAlmostEqual(total, to_tap + math.dist(tap[1], end[1]))
                output = ("F.Cu", pad_center(self.footprints[series], "2"))
                anode = next(p for p in self.footprints[led].pads if p.number == "2")
                self.assertEqual(output[1][1], anode.xy[1])
                self.assertAlmostEqual(planar_trace_length(self.board, anode.net, output,
                                                          ("F.Cu", anode.xy), top_only=True),
                                       math.dist(output[1], anode.xy))

    def test_bridge_uart_uses_one_bottom_run_between_two_short_top_fanouts(self):
        for net, ref, pin, bridge_pin in (("ESP_TX", "R28", "2", "20"), ("ESP_RX", "U2", "34", "21")):
            with self.subTest(net=net):
                vias = self.through_via_positions(net)
                self.assertEqual(len(vias), 2)
                left, right = sorted(vias)
                source = ("F.Cu", pad_center(self.footprints[ref], pin))
                bridge = ("F.Cu", pad_center(self.footprints["U4"], bridge_pin))
                self.assertLess(planar_trace_length(self.board, net, source, ("F.Cu", left), top_only=True), 1.6)
                self.assertLess(planar_trace_length(self.board, net, ("F.Cu", right), bridge, top_only=True), 2)
                bottom = self.segments["B.Cu", net]
                self.assertEqual(len(bottom), 2)
                length = sum(math.dist(values(t, "start"), values(t, "end")) for t in bottom)
                dx, dy = sorted((abs(right[0] - left[0]), abs(right[1] - left[1])))
                self.assertAlmostEqual(length, dy + dx * (math.sqrt(2) - 1))
                self.assertAlmostEqual(planar_trace_length(self.board, net, ("B.Cu", left), ("B.Cu", right)), length)

    def test_solenoid_switch_polarity_and_default_off_paths(self):
        assignments = self.project["net_settings"]["netclass_assignments"]
        self.assertIn("Load2A", assignments.get("SOL_POS", []))
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
            "R23": {"1": "SOL_CMD", "2": "SOL_LED_A"},
            "D6": {"1": "GND", "2": "SOL_LED_A"},
            "R46": {"1": "SOL_POS", "2": "SOL_OUT_LED_A"},
            "D9": {"1": "GND", "2": "SOL_OUT_LED_A"},
        }
        for ref, pin_nets in expected.items():
            with self.subTest(ref=ref):
                actual = {pad.number: pad.net for pad in self.footprints[ref].pads if pad.number}
                self.assertEqual(actual, pin_nets)

    def test_solenoid_base_and_gate_traces_run_directly_on_top(self):
        for net, start_ref, start_pin, end_ref, end_pin in (
            ("SOL_ENABLE", "R21", "2", "R22", "1"),
            ("SOL_ENABLE", "R21", "2", "TP14", "1"),
            ("SOL_ENABLE", "TP14", "1", "Q7", "1"),
            ("SOL_ENABLE", "R21", "2", "Q7", "1"),
            ("SOL_GATE_SINK", "Q7", "3", "R45", "1"),
            ("SOL_GATE", "R45", "2", "Q6", "4"),
        ):
            with self.subTest(net=net, start=start_ref, end=end_ref):
                start = pad_center(self.footprints[start_ref], start_pin)
                end = pad_center(self.footprints[end_ref], end_pin)
                length = planar_trace_length(
                    self.board, net, ("F.Cu", start), ("F.Cu", end), top_only=True
                )
                self.assertAlmostEqual(length, math.dist(start, end))
                self.assertFalse(self.through_via_positions(net))

    def test_solenoid_indicator_routing_and_silkscreen(self):
        output, ground = (pad_center(self.footprints["J5"], pin) for pin in ("1", "2"))
        feed, series = (pad_center(self.footprints["R46"], pin) for pin in ("1", "2"))
        cathode, anode = (pad_center(self.footprints["D9"], pin) for pin in ("1", "2"))
        # A 45-degree exit clears J5 pin 2 before the vertical run into R46.
        bend = (feed[0], round(output[1] + feed[0] - output[0], 6))
        for net, start, end in (
            ("SOL_POS", output, bend), ("SOL_POS", bend, feed),
            ("SOL_OUT_LED_A", series, anode), ("GND", cathode, ground),
        ):
            with self.subTest(net=net, start=start, end=end):
                self.assertIn({start, end}, [
                    {tuple(values(s, "start")), tuple(values(s, "end"))}
                    for s in self.segments["F.Cu", net]
                ])
        self.assertEqual(series[1], anode[1])
        self.assertEqual(cathode[0], ground[0])
        legend, = (t for t in children(self.board.tree, "gr_text")
                   if t[1] == "SOL" and values(t, "layer") == ["F.SilkS"])
        x, y, _ = values(legend, "at")
        self.assertEqual(x, self.footprints["D9"].xy[0])
        self.assertLess(y, self.footprints["D9"].xy[1])

    def test_single_channel_buffers_share_enable_and_have_local_bypasses(self):
        for ref, command, output, bypass in (
            ("U9", "DRV_DISABLE_CMD", "DRIVERS_DISABLE", "C39"),
            ("U12", "SOL_CMD", "SOL_SAFE", "C31"),
        ):
            with self.subTest(ref=ref):
                chip = self.footprints[ref]
                self.assertEqual(chip.fields["MPN"], "SN74LVC1G125DBVR")
                self.assertEqual(chip.fields["LCSC"], "C23654")
                self.assertEqual({p.number: p.net for p in chip.pads},
                                 {"1": "ACT_OE_N", "2": command, "3": "GND",
                                  "4": output, "5": "V3V3"})
                cap = self.footprints[bypass]
                self.assertEqual(cap.fields["MPN"], "CL10B104KB8NNNC")
                self.assertEqual({p.number: p.net for p in cap.pads}, {"1": "V3V3", "2": "GND"})
                self.assertLess(planar_trace_length(
                    self.board, "V3V3", ("F.Cu", pad_center(chip, "5")),
                    ("F.Cu", pad_center(cap, "1")), top_only=True,
                ), 2.0)

    def test_u9_ground_trace_reaches_its_via(self):
        pad = pad_center(self.footprints["U9"], "3")
        via = min(self.through_via_positions("GND"), key=lambda at: math.dist(pad, at))
        self.assertTrue(in_ground_fill(via, self.ground_fills["In1.Cu"]))
        self.assertEqual(pad[1], via[1])
        self.assertAlmostEqual(
            planar_trace_length(self.board, "GND", ("F.Cu", pad), ("F.Cu", via), top_only=True),
            math.dist(pad, via),
        )

    def test_interlock_signals_stay_on_top(self):
        for net in INTERLOCK_SIGNALS:
            with self.subTest(net=net):
                layers = {layer for (layer, name), tracks in self.segments.items()
                          if name == net and tracks}
                self.assertEqual(layers, {"F.Cu"})
                self.assertFalse(self.through_via_positions(net))

    def test_buffer_command_routes_pass_through_their_bias_resistors(self):
        for net, gpio_pin, taps, buffer, limit in (
            ("DRV_DISABLE_CMD", "16", [("R37", "2")], "U9", 7.5),
            ("SOL_CMD", "8", [("R23", "1"), ("R38", "1")], "U12", 16.0),
        ):
            with self.subTest(net=net):
                pads = [("U2", gpio_pin), *taps, (buffer, "2")]
                points = [("F.Cu", pad_center(self.footprints[ref], pin)) for ref, pin in pads]
                length = planar_trace_length(self.board, net, points[0], points[-1], top_only=True)
                self.assertLess(length, limit)
                self.assertAlmostEqual(length, sum(
                    planar_trace_length(self.board, net, a, b, top_only=True)
                    for a, b in zip(points, points[1:])
                ))
                bias, input_pin = points[-2:]
                self.assertEqual(bias[1][0], input_pin[1][0])
                self.assertAlmostEqual(
                    planar_trace_length(self.board, net, bias, input_pin, top_only=True),
                    math.dist(bias[1], input_pin[1]),
                )

    def test_solenoid_buffer_aligns_with_r21_and_takes_enable_through_tp12(self):
        led_tap = pad_center(self.footprints["R23"], "1")
        pwm_input = pad_center(self.footprints["U12"], "2")
        self.assertEqual(led_tap[0], pwm_input[0])
        self.assertAlmostEqual(
            planar_trace_length(self.board, "SOL_CMD", ("F.Cu", led_tap), ("F.Cu", pwm_input), top_only=True),
            math.dist(led_tap, pwm_input),
        )
        source = pad_center(self.footprints["U12"], "4")
        load = pad_center(self.footprints["R21"], "1")
        self.assertEqual(source[1], load[1])
        self.assertLess(math.dist(source, load), 2.0)
        self.assertAlmostEqual(
            planar_trace_length(self.board, "SOL_SAFE", ("F.Cu", source), ("F.Cu", load), top_only=True),
            math.dist(source, load),
        )
        gate, probe, enable = (("F.Cu", pad_center(self.footprints[ref], pin))
                               for ref, pin in (("U10", "4"), ("TP12", "1"), ("U12", "1")))
        self.assertEqual(gate[1][1], enable[1][1])
        direct = math.dist(gate[1], enable[1])
        self.assertAlmostEqual(direct, sum(
            planar_trace_length(self.board, "ACT_OE_N", a, b, top_only=True)
            for a, b in ((gate, probe), (probe, enable))
        ))
        motor = ("F.Cu", pad_center(self.footprints["U9"], "1"))
        pullup = ("F.Cu", pad_center(self.footprints["R36"], "2"))
        self.assertAlmostEqual(
            planar_trace_length(self.board, "ACT_OE_N", gate, motor, top_only=True),
            sum(planar_trace_length(self.board, "ACT_OE_N", a, b, top_only=True)
                for a, b in ((gate, pullup), (pullup, motor))),
        )

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
        for name, points in (("J2 and U3", usb_contacts + [pad_center(self.footprints["U3"], "5")]),
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

    def test_cp2102n_bypass_routes_and_supply_feed(self):
        net = "V3V3"
        bridge = self.footprints["U4"]
        for pin, cap, limit in (("5", "C10", 3.6), ("6", "C11", 3.6),
                                ("7", "C29", 3.6), ("7", "C36", 6.0)):
            start = ("F.Cu", pad_center(bridge, pin))
            end = ("F.Cu", pad_center(self.footprints[cap], "1"))
            self.assertLess(planar_trace_length(self.board, net, start, end, top_only=True), limit, cap)
        supply = plane_fills(self.board, net)["In2.Cu"]
        feed = ("F.Cu", pad_center(bridge, "7"))
        # The feed passes the two 100 nF pads before turning toward the 4.7 µF bank.
        previous = feed
        for ref in ("C11", "C29"):
            pad = ("F.Cu", pad_center(self.footprints[ref], "1"))
            self.assertEqual(pad[1][1], previous[1][1], ref)
            self.assertAlmostEqual(
                planar_trace_length(self.board, net, previous, pad, top_only=True),
                pad[1][0] - previous[1][0], msg=ref,
            )
            previous = pad
        first_bulk = ("F.Cu", pad_center(self.footprints["C36"], "1"))
        self.assertAlmostEqual(planar_trace_length(self.board, net, previous, first_bulk, top_only=True),
                               shortest_45_length(previous[1], first_bulk[1]))
        for pin, rail_net in (("1", net), ("2", "GND")):
            pads = [("F.Cu", pad_center(self.footprints[ref], pin)) for ref in ("C36", "C37", "C38")]
            for first, second in zip(pads, pads[1:]):
                self.assertEqual(first[1][0], second[1][0])
                self.assertAlmostEqual(planar_trace_length(self.board, rail_net, first, second, top_only=True),
                                       math.dist(first[1], second[1]))
        self.assertTrue(any(
            in_ground_fill(at, supply) and
            planar_trace_length(self.board, net, feed, ("F.Cu", at), top_only=True) < 3.0
            for at in self.through_via_positions(net)
        ))

    def test_cp2102n_qfn24_matches_silabs_table_7_2(self):
        chip = self.footprints["U4"]
        footprint = next(n for n in children(self.board.tree, "footprint") if n[1] == chip.land)
        self.assertEqual(values(footprint, "solder_mask_margin"), [0.06])
        leads = [p for p in chip.pads if p.number and p.number != "25"]
        self.assertEqual(len(leads), 24)
        for pad in leads:
            self.assertEqual(sorted(pad.size), [0.30, 0.85])
            self.assertTrue(pad.on_layer("F.Paste"))
        center = next(p for p in chip.pads if p.number == "25")
        self.assertEqual(center.size, (2.55, 2.55))
        self.assertFalse(center.on_layer("F.Paste"))
        windows = [p for p in chip.pads if not p.number and p.on_layer("F.Paste")]
        self.assertEqual(len(windows), 4)
        self.assertEqual({p.size for p in windows}, {(0.9, 0.9)})
        self.assertEqual({tuple(round(a-b, 2) for a, b in zip(p.xy, center.xy)) for p in windows},
                         {(x, y) for x in (-0.6, 0.6) for y in (-0.6, 0.6)})

    def test_x_driver_takes_power_between_pin_and_bypass_capacitor(self):
        net = "V3V3"
        regions = plane_fills(self.board, net)["In2.Cu"]
        feeds = [at for at in self.through_via_positions(net) if in_ground_fill(at, regions)]
        start = ("F.Cu", pad_center(self.footprints["U5"], "15"))
        end = ("F.Cu", pad_center(self.footprints["C16"], "1"))
        direct = shortest_45_length(start[1], end[1])
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
                                "SOL_GATE", "SOL_GATE_SINK", "USB_CC1", "USB_CC2", "USB_VBUS", "USB_BRIDGE_RESET_N",
                                "USB_VBUS_SENSE", "X_SENSE_A", "X_SENSE_B",
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

    def test_l4_signals_and_motor_outputs_have_local_ground_returns(self):
        self.assertEqual(len(self.ground_fills["In1.Cu"]), 1)
        grounded = self.plated_ground_returns_to_l2()
        returns = [(region, [at for at in grounded if in_ground_fill(at, [region])])
                   for region in self.ground_fills["In2.Cu"]]

        def check_launch(at, launch):
            regions = [region for region, contacts in returns
                       if any(math.dist(at, contact) <= 2.0 for contact in contacts)]
            self.assertTrue(launch, "Missing bottom-layer launch samples")
            self.assertTrue(all(in_ground_fill(p, regions) for p in launch),
                            "Launch needs a plated L2 return in its L3 ground region")

        motor_pins = {pad.net: pad for ref in ("J3", "J4") for pad in self.footprints[ref].pads}
        for net in sorted(set(self.l4_ground_referenced_nets()) | motor_pins.keys()):
            tracks = self.segments["B.Cu", net]
            if not tracks:
                continue
            samples = [p for segment in tracks for p in track_samples(segment)]
            for at in self.through_via_positions(net):
                land_radius = values(self.vias[at], "size")[0] / 2
                if not any(math.dist(p, at) <= land_radius for p in samples):
                    continue
                with self.subTest(net=net, via=at):
                    radius = via_plane_clearance_radius(self.vias[at], "In2.Cu")
                    check_launch(at, [p for p in samples
                                      if radius + 0.06 <= math.dist(p, at) <= radius + 0.25])
            if net in motor_pins:
                pad = motor_pins[net]
                with self.subTest(net=net, connector_pin=pad.xy):
                    # The L3 ground pour clears the actual pad outline by 0.20 mm.
                    check_launch(pad.xy, [p for p in samples if 0.26 <= pad.edge_distance(p) <= 0.45])

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
        u3_ground = pad_center(self.footprints["U3"], "3")
        usb_region, = [region for region in fills["In2.Cu"] if in_ground_fill(u3_ground, [region])]
        nearest = set()
        for pin in ("3", "8"):
            start = ("F.Cu", pad_center(self.footprints["U3"], pin))
            vias = [via for via in self.through_via_positions("GND")
                    if math.dist(start[1], via) < 1.5]
            length, via = min((planar_trace_length(self.board, "GND", start, ("F.Cu", via),
                                                   top_only=True), via) for via in vias)
            self.assertLess(length, 1.1)
            self.assertTrue(in_ground_fill(via, fills["In1.Cu"]))
            nearest.add(via)
        self.assertEqual(len(nearest), 2)
        # Count connected stitching in each part of the socket breakout.
        local_stitches = [at for at in self.through_via_positions("GND")
                          if in_ground_fill(at, [usb_region]) and all(
                              in_ground_fill(at, fills[layer]) for layer in ("In1.Cu", "B.Cu"))]
        for west, east, north, south, minimum in (
            (155.5, 159.0, 61.0, 65.6, 5), (159.0, 161.0, 60.0, 64.0, 2),
            (163.0, 166.0, 61.0, 65.0, 3),
        ):
            count = sum(west < x < east and north < y < south for x, y in local_stitches)
            self.assertGreaterEqual(count, minimum)
        shell = [p for p in self.footprints["J2"].pads if p.number == "SH"]
        self.assertEqual(len(shell), 4)
        for pad in shell:
            self.assertEqual(pad.net, "GND")
            self.assertTrue(in_ground_fill(pad.xy, fills["In1.Cu"]))
        plated_returns = [at for at in self.through_via_positions("GND")
                          if in_ground_fill(at, [usb_region]) and in_ground_fill(at, fills["In1.Cu"])]
        for net, _, _ in USB_C_CONTACTS:
            vias = {at: v for at, v in self.vias.items() if values(v, "net") == [net]}
            for at in vias:
                self.assertGreaterEqual(sum(math.dist(at, stitch) < 1.0 for stitch in plated_returns), 2)
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
                self.assertEqual(bool(samples), signal == "F.Cu" or bool(vias), (signal, net))
                for point in samples:
                    self.assertTrue(in_ground_fill(point, fills[reference]), (net, point))
