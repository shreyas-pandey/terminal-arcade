"""Frame building (pure: state -> list of lines) and diffed screen output."""

import re

from .board import HEIGHT, HIDDEN, VISIBLE_HEIGHT, WIDTH
from .game import LINE_CLEAR_TIME
from .pieces import SHAPES

GREEN = "\x1b[0;32;40m"
BRIGHT = "\x1b[92m"
NORMAL = "\x1b[32m"
BLOCK = "[]"
EMPTY = " ."

MIN_WIDTH = 48
MIN_HEIGHT = 24
INNER = WIDTH * 2  # visible characters inside the walls
FLASH_PERIOD = 0.05

_ANSI = re.compile(r"\x1b\[[0-9;]*m")

_FONT = {
    "T": ("XXX", ".X.", ".X.", ".X.", ".X."),
    "E": ("XXX", "X..", "XX.", "X..", "XXX"),
    "R": ("XX.", "X.X", "XX.", "X.X", "X.X"),
    "I": ("XXX", ".X.", ".X.", ".X.", "XXX"),
    "S": (".XX", "X..", ".X.", "..X", "XX."),
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


def visible_len(text):
    return len(_ANSI.sub("", text))


# --- frame builders -------------------------------------------------------


def build_frame(app, width, height):
    if width < MIN_WIDTH or height < MIN_HEIGHT:
        body = [
            "TERMINAL TOO SMALL",
            f"need {MIN_WIDTH}x{MIN_HEIGHT}",
            f"have {width}x{height}",
        ]
        body = [line[:width] for line in body]
    elif app.state == "title":
        body = _title(app)
    else:
        body = _playfield(app)
    return _compose(body, width, height)


def _compose(body, width, height):
    block_width = max((visible_len(line) for line in body), default=0)
    left = " " * max(0, (width - block_width) // 2)
    top = max(0, (height - len(body)) // 2)
    lines = []
    for row in range(height):
        index = row - top
        line = left + body[index] if 0 <= index < len(body) else ""
        target = width - 1 if row == height - 1 else width  # avoid scrolling
        line += " " * max(0, target - visible_len(line))
        lines.append(GREEN + line)
    return lines


def _title(app):
    logo = []
    for row in range(5):
        logo.append("  ".join(
            "".join(BLOCK if c == "X" else "  " for c in _FONT[letter][row])
            for letter in "TETRIS"
        ))
    width = max(len(line) for line in logo)
    controls_width = max(len(line) for line in CONTROLS)
    pad = " " * ((width - controls_width) // 2)
    return [
        *logo,
        "",
        f"START LEVEL  < {app.start_level} >".center(width),
        "",
        f"HIGH SCORE  {app.best:07d}".center(width),
        "",
        *(pad + line for line in CONTROLS),
        "",
        "ENTER start   LEFT/RIGHT level   Q quit".center(width),
    ]


def _playfield(app):
    game = app.game
    if game.paused:
        rows = [" " * INNER] * VISIBLE_HEIGHT
        rows = _overlay(rows, ["PAUSED", "", "P  resume", "Q  quit"])
    else:
        rows = _board_rows(game)
        if app.state == "over":
            rows = _overlay(rows, [
                "GAME OVER",
                "",
                f"SCORE {game.score:07d}",
                "NEW HIGH SCORE!" if app.new_high else "",
                "",
                "ENTER  play again",
                "Q  quit",
            ])
    left = ["<!" + row + "!>" for row in rows]
    left.append("<!" + "=" * INNER + "!>")
    left.append("  " + "\\/" * WIDTH + "  ")
    return [l + "    " + p for l, p in zip(left, _panel(app))]


def _board_rows(game):
    active = set(game.piece.cells()) if game.piece else set()
    flash_on = int((LINE_CLEAR_TIME - game.clear_timer) / FLASH_PERIOD) % 2 == 1
    rows = []
    for y in range(HIDDEN, HEIGHT):
        if y in game.clearing_rows:
            rows.append((BLOCK if flash_on else "  ") * WIDTH)
            continue
        parts = []
        for x in range(WIDTH):
            if (x, y) in active:
                parts.append(BRIGHT + BLOCK + NORMAL)
            elif game.board.grid[y][x]:
                parts.append(BLOCK)
            else:
                parts.append(EMPTY)
        rows.append("".join(parts))
    return rows


def _overlay(rows, text):
    inner = INNER - 2
    box = ["+" + "-" * inner + "+"]
    box += ["|" + line.center(inner) + "|" for line in text]
    box += ["+" + "-" * inner + "+"]
    start = (len(rows) - len(box)) // 2
    rows = list(rows)
    rows[start:start + len(box)] = box
    return rows


def _preview(kind):
    if kind is None:
        return ["", ""]
    cells = SHAPES[kind][0]
    top = min(y for _, y in cells)
    return [
        "".join(BLOCK if (x, y) in cells else "  " for x in range(4)).rstrip()
        for y in (top, top + 1)
    ]


def _panel(app):
    game = app.game
    queue = list(game.queue)
    hi = max(app.best, game.score)
    return [
        "SCORE", f"{game.score:07d}",
        "",
        "HI SCORE", f"{hi:07d}",
        "",
        f"LEVEL {game.level:02d}",
        f"LINES {game.lines:03d}",
        "",
        "NEXT",
        *_preview(queue[0]),
        "",
        *_preview(queue[1]),
        "",
        *_preview(queue[2]),
        "",
        "HOLD",
        *_preview(game.hold_kind),
    ]


# --- output -----------------------------------------------------------------


class Screen:
    """Writes only the lines that changed since the previous frame."""

    def __init__(self, write):
        self._write = write
        self._prev = []
        self._size = None

    def draw(self, lines, size):
        parts = []
        if size != self._size:
            self._size = size
            self._prev = []
            parts.append(GREEN + "\x1b[2J")
        for i, line in enumerate(lines):
            if i < len(self._prev) and self._prev[i] == line:
                continue
            parts.append(f"\x1b[{i + 1};1H{line}")
        self._prev = list(lines)
        if parts:
            self._write("".join(parts))
