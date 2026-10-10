"""Full-screen composition and diffed terminal output."""

import re

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(text):
    return len(_ANSI.sub("", text))


def compose(body, width, height, theme):
    """Centre body lines on a width x height screen, padding every row."""
    block_width = max((visible_len(line) for line in body), default=0)
    left = " " * max(0, (width - block_width) // 2)
    top = max(0, (height - len(body)) // 2)
    lines = []
    for row in range(height):
        index = row - top
        line = left + body[index] if 0 <= index < len(body) else ""
        target = width - 1 if row == height - 1 else width  # avoid scrolling
        line += theme.base + " " * max(0, target - visible_len(line))
        lines.append(theme.base + line)
    return lines


def too_small(width, height, min_width, min_height):
    return [
        line[:width]
        for line in ("TERMINAL TOO SMALL", f"need {min_width}x{min_height}", f"have {width}x{height}")
    ]


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
            parts.append("\x1b[0;40m\x1b[2J")
        for i, line in enumerate(lines):
            if i < len(self._prev) and self._prev[i] == line:
                continue
            parts.append(f"\x1b[{i + 1};1H{line}")
        self._prev = list(lines)
        if parts:
            self._write("".join(parts))
