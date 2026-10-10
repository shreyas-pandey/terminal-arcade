import unittest

from src.input import Controls


class FakeKeyboard:
    def __init__(self):
        self.down = set()

    def is_down(self, key):
        return key in self.down


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.kb = FakeKeyboard()
        self.controls = Controls(self.kb.is_down, das=0.17, arr=0.05)

    def test_das_then_arr(self):
        self.kb.down.add("LEFT")
        self.assertEqual(self.controls.update(["LEFT"], 0.0), ["left"])
        self.assertEqual(self.controls.update(["LEFT"], 0.10), [])  # OS repeat ignored
        self.assertEqual(self.controls.update([], 0.17), ["left"])
        self.assertEqual(self.controls.update([], 0.23), ["left"])
        self.kb.down.clear()
        self.assertEqual(self.controls.update([], 0.40), [])

    def test_rotate_does_not_auto_repeat(self):
        self.kb.down.add("UP")
        self.assertEqual(self.controls.update(["UP"], 0.0), ["rotate_cw"])
        self.assertEqual(self.controls.update(["UP", "UP"], 0.5), [])
        self.kb.down.clear()
        self.controls.update([], 0.6)
        self.kb.down.add("UP")
        self.assertEqual(self.controls.update(["UP"], 0.7), ["rotate_cw"])

    def test_soft_drop_held(self):
        self.kb.down.add("DOWN")
        self.controls.update(["DOWN"], 0.0)
        self.assertTrue(self.controls.soft_drop)
        self.kb.down.clear()
        self.controls.update([], 0.1)
        self.assertFalse(self.controls.soft_drop)

    def test_without_key_state_every_event_is_an_action(self):
        controls = Controls(None)
        self.assertEqual(controls.update(["LEFT", "LEFT", "DOWN"], 0.0),
                         ["left", "left", "soft_step"])


if __name__ == "__main__":
    unittest.main()
