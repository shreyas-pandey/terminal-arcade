"""Snake scene: title, playing, paused and game-over screens."""

from engine.canvas import Canvas
from engine.controls import Controls
from engine.loop import Scene
from engine.text import draw_big_centered, draw_box

from .game import HEIGHT, WIDTH, SnakeGame

KEY = "snake"
INNER = WIDTH * 2
PANEL_X = INNER + 6

KEYMAP = {
    "UP": "up", "w": "up",
    "DOWN": "down", "s": "down",
    "LEFT": "left", "a": "left",
    "RIGHT": "right", "d": "right",
    "p": "pause", "ESC": "pause",
}

CONTROLS = (
    "ARROWS / W A S D   steer",
    "P / ESC            pause",
)


class SnakeScene(Scene):
    def __init__(self, ctx):
        self.ctx = ctx
        self.controls = Controls(KEYMAP, ctx.is_down)
        self.state = "title"
        self.game = None
        self.new_high = False
        self.clock = 0.0

    def enter(self):
        self.controls.reset()

    @property
    def best(self):
        return self.ctx.saves.best(KEY)

    def handle(self, keys, now):
        if self.state == "title" or self.state == "over":
            if "ENTER" in keys:
                self._start()
            elif "q" in keys or "ESC" in keys:
                self.next_scene = self.ctx.exit_from(self)
            return
        game = self.game
        if game.paused and "q" in keys:
            self._record()
            self.next_scene = self.ctx.exit_from(self)
            return
        for action in self.controls.update(keys, now):
            if action == "pause":
                game.paused = not game.paused
            elif not game.paused:
                game.turn(action)

    def _start(self):
        self.game = SnakeGame()
        self.controls.reset()
        self.new_high = False
        self.state = "playing"

    def _record(self):
        game = self.game
        rank = self.ctx.saves.add_score(KEY, game.score, length=len(game.body))
        self.new_high = rank == 0

    def update(self, dt):
        self.clock += dt
        if self.state == "playing":
            self.game.update(dt)
            if self.game.over:
                self._record()
                self.state = "over"

    # --- drawing ------------------------------------------------------

    def render(self, theme):
        canvas = self._title() if self.state == "title" else self._playfield()
        return canvas.lines(theme)

    def _title(self):
        c = Canvas(46, 16)
        draw_big_centered(c, 0, "SNAKE", role=lambda i: f"logo{i}")
        # A little snake chasing its food across the title.
        x = int(self.clock * 10) % 60 - 14
        c.put(x, 7, "[][][][]", "snake_body")
        c.put(x + 8, 7, "()", "snake_head")
        c.put(x + 14, 7, "<>", "food")
        c.center(9, f"HIGH SCORE  {self.best:07d}")
        for i, line in enumerate(CONTROLS):
            c.put(10, 11 + i, line, "dim")
        c.center(15, "ENTER start   ESC back")
        return c

    def _playfield(self):
        game = self.game
        c = Canvas(PANEL_X + 10, HEIGHT + 2)
        edge = "+" + "-" * INNER + "+"
        c.put(0, 0, edge, "frame")
        c.put(0, HEIGHT + 1, edge, "frame")
        for y in range(HEIGHT):
            c.put(0, y + 1, "|", "frame")
            c.put(INNER + 1, y + 1, "|", "frame")
            c.put(1, y + 1, " ." * WIDTH, "dim")

        if game.paused:
            for y in range(HEIGHT):
                c.put(1, y + 1, " " * INNER)
            draw_box(c, 10, 6, 22, ["PAUSED", "", "P  resume", "Q  quit"])
        else:
            if game.food and int(self.clock * 4) % 4:
                c.put(1 + 2 * game.food[0], 1 + game.food[1], "<>", "food")
            for i, (x, y) in enumerate(game.body):
                if i == 0:
                    c.put(1 + 2 * x, 1 + y, "()", "snake_head")
                else:
                    c.put(1 + 2 * x, 1 + y, "[]", "snake_body")
            if self.state == "over":
                draw_box(c, 9, 5, 24, [
                    "YOU WIN!" if game.won else "GAME OVER", "",
                    f"SCORE {game.score:07d}",
                    "NEW HIGH SCORE!" if self.new_high else "",
                    "",
                    "ENTER  play again",
                    "Q  quit",
                ])

        x = PANEL_X
        c.put(x, 1, "SCORE")
        c.put(x, 2, f"{game.score:07d}", "bright")
        c.put(x, 4, "HI SCORE")
        c.put(x, 5, f"{max(self.best, game.score):07d}", "bright")
        c.put(x, 7, f"LENGTH {len(game.body):03d}")
        c.put(x, 8, f"SPEED  {game.speed:02d}")
        return c
