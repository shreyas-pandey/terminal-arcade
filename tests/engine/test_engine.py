import json
import tempfile
import unittest
from pathlib import Path

from engine.canvas import Canvas
from engine.loop import QUIT, Context, Scene, Transition, _crt_mask
from engine.saves import MAX_ENTRIES, Saves, insert_score, migrate_legacy
from engine.screen import compose, visible_len
from engine.text import big_width, draw_big
from engine.theme import CGA, PHOSPHOR, by_key, next_theme


class ThemeTests(unittest.TestCase):
    def test_phosphor_is_green_only(self):
        for role in ("text", "frame", "piece_T", "active_T", "enemy_boss", "star", "rainbow3"):
            self.assertRegex(PHOSPHOR.sgr(role), r"^\x1b\[0;(2;)?(32|92);40m$", role)

    def test_phosphor_highlights_what_you_control(self):
        self.assertIn("92", PHOSPHOR.sgr("active_T"))
        self.assertIn("92", PHOSPHOR.sgr("player"))
        self.assertNotIn("92", PHOSPHOR.sgr("piece_T"))

    def test_cga_colours_each_piece_differently(self):
        codes = {CGA.sgr(f"piece_{k}") for k in "IOTSZJL"}
        self.assertEqual(len(codes), 7)
        self.assertEqual(CGA.sgr("active_T"), CGA.sgr("piece_T"))

    def test_always_black_background(self):
        for theme in (PHOSPHOR, CGA):
            self.assertTrue(theme.sgr("anything").endswith(";40m"))

    def test_cycle_and_lookup(self):
        self.assertIs(next_theme(PHOSPHOR), CGA)
        self.assertIs(next_theme(CGA), PHOSPHOR)
        self.assertIs(by_key("cga"), CGA)
        self.assertIs(by_key("nonsense"), PHOSPHOR)


class CanvasTests(unittest.TestCase):
    def test_put_clips_and_lines_have_full_width(self):
        c = Canvas(5, 2)
        c.put(3, 0, "abcdef", "bright")
        c.put(0, 5, "ignored")
        lines = c.lines(PHOSPHOR)
        self.assertEqual([visible_len(line) for line in lines], [5, 5])
        self.assertIn("ab", lines[0])

    def test_sprite_spaces_are_transparent(self):
        c = Canvas(3, 1)
        c.put(0, 0, "xyz")
        c.sprite(0, 0, ["a c"])
        self.assertEqual("".join(c.chars[0]), "ayc")

    def test_big_text_width(self):
        c = Canvas(big_width("AB"), 5)
        draw_big(c, 0, 0, "AB")
        self.assertEqual("".join(c.chars[0]), "  []    [][]  ")


class ScreenTests(unittest.TestCase):
    def test_compose_fills_screen(self):
        lines = compose(["hi"], 10, 4, CGA)
        self.assertEqual(len(lines), 4)
        self.assertEqual([visible_len(line) for line in lines], [10, 10, 10, 9])


class SavesTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.saves = Saves(self.dir / "saves")

    def test_one_file_per_game(self):
        self.assertEqual(self.saves.add_score("snake", 50, length=9), 0)
        self.assertEqual(self.saves.add_score("snake", 30, length=7), 1)
        self.saves.add_score("tetris", 900, lines=3, level=0)
        self.assertEqual(sorted(p.name for p in (self.dir / "saves").iterdir()), ["snake.json", "tetris.json"])
        fresh = Saves(self.dir / "saves")
        self.assertEqual(fresh.best("snake"), 50)
        self.assertEqual(fresh.best("starfighter"), 0)

    def test_zero_scores_are_not_recorded(self):
        self.assertIsNone(self.saves.add_score("snake", 0))
        self.assertEqual(self.saves.scores("snake"), [])

    def test_corrupt_file_is_ignored(self):
        (self.dir / "saves").mkdir()
        (self.dir / "saves" / "snake.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(self.saves.scores("snake"), [])

    def test_settings(self):
        self.assertIsNone(self.saves.setting("display"))
        self.saves.set_setting("display", "cga")
        self.assertEqual(Saves(self.dir / "saves").setting("display"), "cga")

    def test_table_is_capped(self):
        entries = []
        for score in range(MAX_ENTRIES + 3):
            entries, _ = insert_score(entries, {"score": score})
        self.assertEqual(len(entries), MAX_ENTRIES)
        self.assertEqual(entries[0]["score"], MAX_ENTRIES + 2)

    def test_legacy_highscore_migrates(self):
        legacy = self.dir / "highscore.json"
        legacy.write_text(json.dumps([{"score": 1234}]), encoding="utf-8")
        migrate_legacy(self.saves, legacy, "tetris")
        self.assertFalse(legacy.exists())
        self.assertEqual(self.saves.best("tetris"), 1234)


class TransitionTests(unittest.TestCase):
    class Stub(Scene):
        def render(self, theme):
            return ["aaaa"] * 4

    def test_switches_to_new_scene(self):
        old, new = self.Stub(), self.Stub()
        transition = Transition(old, new)
        transition.update(0.3)
        self.assertIsNone(transition.next_scene)
        transition.update(0.3)
        self.assertIs(transition.next_scene, new)

    def test_power_off_quits(self):
        transition = Transition(self.Stub(), None)
        transition.update(1.0)
        self.assertIs(transition.next_scene, QUIT)

    def test_mask_keeps_centre_rows(self):
        self.assertEqual(_crt_mask(["a", "b", "c", "d"], 0.5), [" ", "b", "c", " "])

    def test_standalone_game_exits_to_quit(self):
        ctx = Context(None, None, PHOSPHOR)
        self.assertIs(ctx.exit_from(self.Stub()), QUIT)


if __name__ == "__main__":
    unittest.main()
