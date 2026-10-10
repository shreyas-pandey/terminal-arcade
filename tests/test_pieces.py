import unittest

from src.pieces import I_KICKS, JLSTZ_KICKS, KINDS, SHAPES, kicks


class ShapeTests(unittest.TestCase):
    def test_every_state_has_four_cells(self):
        for kind in KINDS:
            for state in SHAPES[kind]:
                self.assertEqual(len(set(state)), 4, kind)

    def test_t_rotation_states(self):
        t = SHAPES["T"]
        self.assertEqual(set(t[0]), {(1, 0), (0, 1), (1, 1), (2, 1)})  # points up
        self.assertEqual(set(t[1]), {(1, 0), (1, 1), (1, 2), (2, 1)})  # points right
        self.assertEqual(set(t[2]), {(0, 1), (1, 1), (2, 1), (1, 2)})  # points down
        self.assertEqual(set(t[3]), {(1, 0), (0, 1), (1, 1), (1, 2)})  # points left

    def test_i_rotation_states(self):
        i = SHAPES["I"]
        self.assertEqual(set(i[0]), {(x, 1) for x in range(4)})
        self.assertEqual(set(i[1]), {(2, y) for y in range(4)})
        self.assertEqual(set(i[2]), {(x, 2) for x in range(4)})
        self.assertEqual(set(i[3]), {(1, y) for y in range(4)})

    def test_o_never_changes(self):
        self.assertEqual(len(set(SHAPES["O"])), 1)


class KickTests(unittest.TestCase):
    def test_first_test_is_no_offset(self):
        for table in (JLSTZ_KICKS, I_KICKS):
            for offsets in table.values():
                self.assertEqual(offsets[0], (0, 0))

    def test_reverse_rotation_negates_kicks(self):
        for table in (JLSTZ_KICKS, I_KICKS):
            for (a, b), offsets in table.items():
                self.assertEqual(offsets, tuple((-x, -y) for x, y in table[(b, a)]))

    def test_o_has_single_kick(self):
        self.assertEqual(kicks("O", 0, 1), ((0, 0),))

    def test_screen_space_y_is_flipped(self):
        # SRS 0->R second test for JLSTZ is (-1, +1) upwards, i.e. y - 1 on screen.
        self.assertEqual(JLSTZ_KICKS[(0, 1)][2], (-1, -1))


if __name__ == "__main__":
    unittest.main()
