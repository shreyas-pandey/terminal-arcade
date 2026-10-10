"""A BIOS-style power-on screen that types itself out. Any key skips it."""

from engine.canvas import Canvas
from engine.loop import Scene, Transition

CHARS_PER_SECOND = 90
FINAL_PAUSE = 0.6


class BootScene(Scene):
    def __init__(self, ctx, launcher, games):
        self.ctx = ctx
        self.launcher = launcher
        self.t = 0.0
        cartridges = " ".join(g.title for g in games)
        # (text, role, pause after the line); {display} is filled in at render time.
        self.script = (
            ("TERMINAL ARCADE BIOS v1.0", "bright", 0.15),
            ("(C) 2026 SHREYAS PANDEY", "text", 0.3),
            ("", "text", 0.0),
            ("MEMORY TEST ........... 640K OK", "text", 0.35),
            ("VIDEO ................. {display}", "text", 0.1),
            ("SOUND ................. NOT FOUND", "text", 0.1),
            (f"CARTRIDGES ............ {cartridges}", "text", 0.4),
            ("", "text", 0.0),
            ("READY.", "bright", 0.0),
        )
        self.starts = []
        clock = 0.3
        for text, _, pause in self.script:
            self.starts.append(clock)
            clock += len(text) / CHARS_PER_SECOND + pause
        self.duration = clock + FINAL_PAUSE

    def handle(self, keys, now):
        if keys and self.next_scene is None:
            self._finish()

    def update(self, dt):
        self.t += dt
        if self.t >= self.duration and self.next_scene is None:
            self._finish()

    def _finish(self):
        self.next_scene = Transition(self, self.launcher)

    def render(self, theme):
        c = Canvas(60, 24)
        cursor = None
        for row, ((text, role, _), start) in enumerate(zip(self.script, self.starts)):
            if self.t < start:
                break
            text = text.replace("{display}", theme.name)
            shown = min(len(text), int((self.t - start) * CHARS_PER_SECOND))
            c.put(2, 1 + row, text[:shown], role)
            cursor = (2 + shown, 1 + row)
        if cursor and int(self.t * 3) % 2 == 0:
            c.put(*cursor, "_", "bright")
        return c.lines(theme)
