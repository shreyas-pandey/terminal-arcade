import unittest

from engine.controls import Controls
from games.tetris.scene import KEYMAP as TETRIS_KEYMAP


class FakeKeyboard:
    def __init__(self):
        self.down = set()

    def is_down(self, key):
        return key in self.down


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.kb = FakeKeyboard()
        self.controls = Controls(TETRIS_KEYMAP, self.kb.is_down, repeat=("left", "right"),
                                 held=("soft_drop",), das=0.17, arr=0.05)

    def test_das_then_arr(self):
        self.kb.down.add("LEFT")
        self.assertEqual(self.controls.update(["LEFT"], 0.0), ["left"])
        self.assertEqual(self.controls.update(["LEFT"], 0.10), [])  # OS repeat ignored
        self.assertEqual(self.controls.update([], 0.17), ["left"])
        self.assertEqual(self.controls.update([], 0.23), ["left"])
        self.kb.down.clear()
        self.assertEqual(self.controls.update([], 0.40), [])

    def test_opposite_direction_cancels_repeat(self):
        self.kb.down.update({"LEFT", "RIGHT"})
        self.controls.update(["LEFT"], 0.0)
        self.assertEqual(self.controls.update(["RIGHT"], 0.05), ["right"])
        self.assertEqual(self.controls.update([], 0.30), ["right", "right"])

    def test_one_shot_does_not_auto_repeat(self):
        self.kb.down.add("UP")
        self.assertEqual(self.controls.update(["UP"], 0.0), ["rotate_cw"])
        self.assertEqual(self.controls.update(["UP", "UP"], 0.5), [])
        self.kb.down.clear()
        self.controls.update([], 0.6)
        self.kb.down.add("UP")
        self.assertEqual(self.controls.update(["UP"], 0.7), ["rotate_cw"])

    def test_held_action(self):
        self.kb.down.add("DOWN")
        self.assertEqual(self.controls.update(["DOWN"], 0.0), [])
        self.assertTrue(self.controls.held("soft_drop"))
        self.kb.down.clear()
        self.controls.update([], 0.1)
        self.assertFalse(self.controls.held("soft_drop"))

    def test_without_key_state_every_event_is_an_action(self):
        controls = Controls(TETRIS_KEYMAP, None, repeat=("left", "right"), held=("soft_drop",))
        self.assertEqual(controls.update(["LEFT", "LEFT", "DOWN", "q"], 0.0),
                         ["left", "left", "soft_drop"])


if __name__ == "__main__":
    unittest.main()
