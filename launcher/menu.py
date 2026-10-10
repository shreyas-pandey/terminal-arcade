"""The arcade front screen: marquee lights, logo, game select, display mode."""

from engine.canvas import Canvas
from engine.loop import Scene, Transition
from engine.text import big_width, draw_big

WIDTH = 60
HEIGHT = 24
TICKER_WIDTH = 52

# Sprites from each cartridge marching across the screen: (offset, text, role).
PARADE = (
    (0, "[][][][]", "snake_body"), (8, "()", "snake_head"), (13, "<>", "food"),
    (20, "[][][]", "piece_T"),
    (30, "{o}", "enemy_grunt"), (35, "<V>", "enemy_wing"), (41, "/=O=\\", "enemy_boss"),
    (52, "|", "bullet"), (55, "<[#]>", "player"),
)
PARADE_LENGTH = 60


def _marquee_path():
    path = [(x, 0) for x in range(0, WIDTH, 2)]
    path += [(WIDTH - 1, y) for y in range(1, HEIGHT - 1)]
    path += [(x, HEIGHT - 1) for x in range(WIDTH - 2, -1, -2)]
    path += [(0, y) for y in range(HEIGHT - 2, 0, -1)]
    return path


MARQUEE = _marquee_path()


class Launcher(Scene):
    def __init__(self, ctx, games):
        self.ctx = ctx
        self.games = games
        self.selected = 0
        self.t = 0.0

    def handle(self, keys, now):
        for key in keys:
            if key in ("UP", "w"):
                self.selected = (self.selected - 1) % len(self.games)
            elif key in ("DOWN", "s"):
                self.selected = (self.selected + 1) % len(self.games)
            elif key.isdigit() and 1 <= int(key) <= len(self.games):
                self.selected = int(key) - 1
                self._launch()
                return
            elif key in ("ENTER", "SPACE"):
                self._launch()
                return
            elif key in ("q", "ESC"):
                self.next_scene = Transition(self, None)  # power off, then quit
                return

    def _launch(self):
        game = self.games[self.selected]
        self.next_scene = Transition(self, game.create(self.ctx))

    def update(self, dt):
        self.t += dt

    def render(self, theme):
        c = Canvas(WIDTH, HEIGHT)
        t = self.t

        phase = int(t * 12)
        for i, (x, y) in enumerate(MARQUEE):
            lit = (i - phase) % 4 == 0
            c.put(x, y, "*" if lit else "o", "bulb_on" if lit else "bulb_off")

        c.center(2, "T   E   R   M   I   N   A   L", "bright")
        shift = int(t * 5)
        draw_big(c, (WIDTH - big_width("ARCADE")) // 2, 4, "ARCADE",
                 role=lambda i: f"rainbow{(i - shift) % 6}")

        start = int(t * 10) % (PARADE_LENGTH + WIDTH) - PARADE_LENGTH
        for offset, text, role in PARADE:
            x = start + offset
            if 1 < x and x + len(text) < WIDTH - 2:
                c.put(x, 10, text, role)

        c.center(12, "=====  SELECT GAME  =====", "text")
        blink = int(t * 3) % 2 == 0
        for i, game in enumerate(self.games):
            entry = f"{i + 1}. {game.title:<12} {'.' * 6} {self.ctx.saves.best(game.key):07d}"
            if i == self.selected:
                marker_l, marker_r = (">>", "<<") if blink else ("  ", "  ")
                c.center(14 + i, f"{marker_l} {entry} {marker_r}", "select")
            else:
                c.center(14 + i, f"   {entry}   ", "text")
        c.center(18, self.games[self.selected].blurb, "dim")

        c.center(19, f"DISPLAY  < {theme.name} >   press M to switch", "text")
        c.center(20, theme.blurb, "dim")
        if (t % 1.0) < 0.65:
            c.center(21, "PRESS ENTER TO PLAY", "bright")

        ticker = self._ticker_text()
        offset = int(t * 8) % len(ticker)
        c.put((WIDTH - TICKER_WIDTH) // 2, 22, (ticker * 2)[offset:offset + TICKER_WIDTH], "dim")
        return c.lines(theme)

    def _ticker_text(self):
        scores = "   ".join(f"{g.title} {self.ctx.saves.best(g.key):07d}" for g in self.games)
        return (f"***  HIGH SCORES   {scores}   ***   UP/DOWN SELECT   ENTER PLAY   "
                f"M DISPLAY MODE   Q QUIT   ***   INSERT COIN   ")
