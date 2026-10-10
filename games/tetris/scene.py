"""Tetris scene: title, playing, paused and game-over screens."""

from engine.canvas import Canvas
from engine.controls import Controls
from engine.loop import Scene
from engine.text import draw_big_centered, draw_box

from .board import HEIGHT, HIDDEN, VISIBLE_HEIGHT, WIDTH
from .game import LINE_CLEAR_TIME, Game
from .pieces import SHAPES

KEY = "tetris"
MAX_START_LEVEL = 9
FLASH_PERIOD = 0.05
INNER = WIDTH * 2  # visible characters inside the walls
PANEL_X = INNER + 8

KEYMAP = {
    "LEFT": "left", "a": "left",
    "RIGHT": "right", "d": "right",
    "DOWN": "soft_drop", "s": "soft_drop",
    "SPACE": "hard_drop", "w": "hard_drop",
    "UP": "rotate_cw", "x": "rotate_cw",
    "z": "rotate_ccw",
    "c": "hold",
    "p": "pause", "ESC": "pause",
}

CONTROLS = (
    "LEFT RIGHT / A D   move",
    "DOWN / S           soft drop",
    "SPACE / W          hard drop",
    "UP / X             rotate right",
    "Z                  rotate left",
    "C                  hold",
    "P / ESC            pause",
)


class TetrisScene(Scene):
    def __init__(self, ctx):
        self.ctx = ctx
        self.controls = Controls(KEYMAP, ctx.is_down, repeat=("left", "right"), held=("soft_drop",))
        self.state = "title"
        self.start_level = 0
        self.game = None
        self.new_high = False

    def enter(self):
        self.controls.reset()

    @property
    def best(self):
        return self.ctx.saves.best(KEY)

    # --- input --------------------------------------------------------

    def handle(self, keys, now):
        getattr(self, f"_on_{self.state}")(keys, now)

    def _on_title(self, keys, now):
        for key in keys:
            if key in ("LEFT", "a"):
                self.start_level = max(0, self.start_level - 1)
            elif key in ("RIGHT", "d"):
                self.start_level = min(MAX_START_LEVEL, self.start_level + 1)
            elif key.isdigit():
                self.start_level = int(key)
            elif key == "ENTER":
                self._start()
                return
            elif key in ("q", "ESC"):
                self.next_scene = self.ctx.exit_from(self)
                return

    def _on_playing(self, keys, now):
        game = self.game
        if game.paused and "q" in keys:
            self._record()
            self.next_scene = self.ctx.exit_from(self)
            return
        for action in self.controls.update(keys, now):
            if action == "pause":
                game.paused = not game.paused
            elif game.paused:
                continue
            elif action == "left":
                game.move(-1)
            elif action == "right":
                game.move(1)
            elif action == "rotate_cw":
                game.rotate(1)
            elif action == "rotate_ccw":
                game.rotate(-1)
            elif action == "hard_drop":
                game.hard_drop()
            elif action == "hold":
                game.hold()
            elif action == "soft_drop":  # only without key-held detection
                game.soft_drop_step()
        game.soft_drop = self.controls.held("soft_drop")

    def _on_over(self, keys, now):
        if "ENTER" in keys:
            self._start()
        elif "q" in keys or "ESC" in keys:
            self.next_scene = self.ctx.exit_from(self)

    def _start(self):
        self.game = Game(self.start_level)
        self.controls.reset()
        self.new_high = False
        self.state = "playing"

    def _record(self):
        game = self.game
        rank = self.ctx.saves.add_score(KEY, game.score, lines=game.lines, level=game.level)
        self.new_high = rank == 0

    # --- time ---------------------------------------------------------

    def update(self, dt):
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
        c = Canvas(46, 19)
        draw_big_centered(c, 0, "TETRIS", role=lambda i: f"logo{i}")
        c.center(6, f"START LEVEL  < {self.start_level} >", "select")
        c.center(8, f"HIGH SCORE  {self.best:07d}")
        for i, line in enumerate(CONTROLS):
            c.put(8, 10 + i, line, "dim")
        c.center(18, "ENTER start   LEFT/RIGHT level   ESC back")
        return c

    def _playfield(self):
        game = self.game
        c = Canvas(PANEL_X + 10, VISIBLE_HEIGHT + 2)
        for row in range(VISIBLE_HEIGHT):
            c.put(0, row, "<!", "frame")
            c.put(INNER + 2, row, "!>", "frame")
        c.put(0, VISIBLE_HEIGHT, "<!" + "=" * INNER + "!>", "frame")
        c.put(2, VISIBLE_HEIGHT + 1, "\\/" * WIDTH, "frame")

        if game.paused:
            draw_box(c, 2, 7, INNER, ["PAUSED", "", "P  resume", "Q  quit"])
        else:
            self._draw_board(c, game)
            if self.state == "over":
                draw_box(c, 2, 5, INNER, [
                    "GAME OVER", "",
                    f"SCORE {game.score:07d}",
                    "NEW HIGH SCORE!" if self.new_high else "",
                    "",
                    "ENTER  play again",
                    "Q  quit",
                ])
        self._draw_panel(c, game)
        return c

    @staticmethod
    def _draw_board(c, game):
        active = set(game.piece.cells()) if game.piece else set()
        active_role = f"active_{game.piece.kind}" if game.piece else ""
        flash_on = int((LINE_CLEAR_TIME - game.clear_timer) / FLASH_PERIOD) % 2 == 1
        for y in range(HIDDEN, HEIGHT):
            row = y - HIDDEN
            if y in game.clearing_rows:
                c.put(2, row, ("[]" if flash_on else "  ") * WIDTH, "bright")
                continue
            for x in range(WIDTH):
                value = game.board.grid[y][x]
                if (x, y) in active:
                    c.put(2 + 2 * x, row, "[]", active_role)
                elif value:
                    c.put(2 + 2 * x, row, "[]", f"piece_{value}" if isinstance(value, str) else "piece")
                else:
                    c.put(2 + 2 * x, row, " .", "dim")

    def _draw_panel(self, c, game):
        x = PANEL_X
        queue = list(game.queue)
        c.put(x, 0, "SCORE")
        c.put(x, 1, f"{game.score:07d}", "bright")
        c.put(x, 3, "HI SCORE")
        c.put(x, 4, f"{max(self.best, game.score):07d}", "bright")
        c.put(x, 6, f"LEVEL {game.level:02d}")
        c.put(x, 7, f"LINES {game.lines:03d}")
        c.put(x, 9, "NEXT")
        for i, kind in enumerate(queue[:3]):
            _draw_preview(c, x, 10 + 3 * i, kind)
        c.put(x, 19, "HOLD")
        _draw_preview(c, x, 20, game.hold_kind)


def _draw_preview(c, x, y, kind):
    if kind is None:
        return
    cells = SHAPES[kind][0]
    top = min(cy for _, cy in cells)
    for cx, cy in cells:
        c.put(x + 2 * cx, y + cy - top, "[]", f"piece_{kind}")
