"""Scenes, CRT-style transitions and the fixed-timestep main loop."""

import time

from .canvas import Canvas
from .screen import Screen, compose, too_small, visible_len
from .theme import next_theme

FPS = 60
MIN_WIDTH = 60
MIN_HEIGHT = 24
QUIT = object()


class Context:
    """What every scene can reach: input state, saves, the display mode, home."""

    def __init__(self, is_down, saves, theme):
        self.is_down = is_down
        self.saves = saves
        self.theme = theme
        self.home = None  # the launcher, when running as an arcade

    def toggle_theme(self):
        self.theme = next_theme(self.theme)
        self.saves.set_setting("display", self.theme.key)

    def exit_from(self, scene):
        """Where a game goes when the player leaves it."""
        return Transition(scene, self.home) if self.home else QUIT


class Scene:
    next_scene = None  # set to a Scene (or QUIT) to switch at the end of the frame

    def enter(self):
        pass

    def handle(self, keys, now):
        pass

    def update(self, dt):
        pass

    def render(self, theme):
        return []


class Transition(Scene):
    """Old CRT power-off: the picture collapses to a line, then the next one opens up."""

    OUT, LINE, IN = 0.22, 0.12, 0.22

    def __init__(self, old, new):
        self.old = old
        self.new = new
        self.t = 0.0

    def update(self, dt):
        self.t += dt
        if self.new is None and self.t >= self.OUT + self.LINE:
            self.next_scene = QUIT
        elif self.t >= self.OUT + self.LINE + self.IN:
            self.next_scene = self.new

    def render(self, theme):
        if self.t < self.OUT:
            return _crt_mask(self.old.render(theme), 1 - self.t / self.OUT)
        if self.t < self.OUT + self.LINE or self.new is None:
            body = self.old.render(theme)
            width = max((visible_len(line) for line in body), default=0)
            shrink = max(0.0, 1 - (self.t - self.OUT) / self.LINE)
            canvas = Canvas(width, len(body))
            canvas.center(len(body) // 2, "-" * max(1, int(width * shrink)), "bright")
            return canvas.lines(theme)
        return _crt_mask(self.new.render(theme), (self.t - self.OUT - self.LINE) / self.IN)


def _crt_mask(body, fraction):
    """Keep only the rows within `fraction` of the vertical centre."""
    half = len(body) / 2
    return [
        line if abs(i + 0.5 - half) <= fraction * half else " " * visible_len(line)
        for i, line in enumerate(body)
    ]


def run(term, ctx, scene):
    screen = Screen(term.write)
    frame = 1.0 / FPS
    last = time.perf_counter()
    theme_key_down = False
    scene.enter()
    while True:
        start = time.perf_counter()
        dt = min(start - last, 0.1)
        last = start

        keys = term.read_keys()
        if "CTRL_C" in keys:
            return
        if ctx.is_down and theme_key_down and not ctx.is_down("m"):
            theme_key_down = False
        if "m" in keys:
            if not theme_key_down:
                ctx.toggle_theme()
            theme_key_down = ctx.is_down is not None
            keys = [k for k in keys if k != "m"]

        scene.handle(keys, start)
        scene.update(dt)
        if scene.next_scene is not None:
            nxt, scene.next_scene = scene.next_scene, None
            if nxt is QUIT:
                return
            scene = nxt
            scene.enter()

        width, height = term.size()
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            body = too_small(width, height, MIN_WIDTH, MIN_HEIGHT)
        else:
            body = scene.render(ctx.theme)
        screen.draw(compose(body, width, height, ctx.theme), (width, height))

        elapsed = time.perf_counter() - start
        if elapsed < frame:
            time.sleep(frame - elapsed)
