"""Big block lettering and boxed overlays."""

FONT = {
    "A": (".X.", "X.X", "XXX", "X.X", "X.X"),
    "B": ("XX.", "X.X", "XX.", "X.X", "XX."),
    "C": (".XX", "X..", "X..", "X..", ".XX"),
    "D": ("XX.", "X.X", "X.X", "X.X", "XX."),
    "E": ("XXX", "X..", "XX.", "X..", "XXX"),
    "F": ("XXX", "X..", "XX.", "X..", "X.."),
    "G": (".XX", "X..", "X.X", "X.X", ".XX"),
    "H": ("X.X", "X.X", "XXX", "X.X", "X.X"),
    "I": ("XXX", ".X.", ".X.", ".X.", "XXX"),
    "J": ("..X", "..X", "..X", "X.X", ".X."),
    "K": ("X.X", "X.X", "XX.", "X.X", "X.X"),
    "L": ("X..", "X..", "X..", "X..", "XXX"),
    "M": ("X.X", "XXX", "XXX", "X.X", "X.X"),
    "N": ("XX.", "X.X", "X.X", "X.X", "X.X"),
    "O": (".X.", "X.X", "X.X", "X.X", ".X."),
    "P": ("XX.", "X.X", "XX.", "X..", "X.."),
    "Q": (".X.", "X.X", "X.X", "XX.", ".XX"),
    "R": ("XX.", "X.X", "XX.", "X.X", "X.X"),
    "S": (".XX", "X..", ".X.", "..X", "XX."),
    "T": ("XXX", ".X.", ".X.", ".X.", ".X."),
    "U": ("X.X", "X.X", "X.X", "X.X", "XXX"),
    "V": ("X.X", "X.X", "X.X", "X.X", ".X."),
    "W": ("X.X", "X.X", "XXX", "XXX", "X.X"),
    "X": ("X.X", "X.X", ".X.", "X.X", "X.X"),
    "Y": ("X.X", "X.X", ".X.", ".X.", ".X."),
    "Z": ("XXX", "..X", ".X.", "X..", "XXX"),
}
FONT_HEIGHT = 5


def big_width(word, pixel="[]", gap=2):
    return len(word) * 3 * len(pixel) + (len(word) - 1) * gap


def draw_big(canvas, x, y, word, role="title", pixel="[]", gap=2):
    """Draw a word in 3x5 block letters. `role` may be a function of letter index."""
    advance = 3 * len(pixel) + gap
    for i, letter in enumerate(word):
        glyph = FONT.get(letter.upper())
        if glyph is None:
            continue
        letter_role = role(i) if callable(role) else role
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "X":
                    canvas.put(x + i * advance + col * len(pixel), y + row, pixel, letter_role)


def draw_big_centered(canvas, y, word, role="title", pixel="[]", gap=2):
    draw_big(canvas, (canvas.width - big_width(word, pixel, gap)) // 2, y, word, role, pixel, gap)


def draw_box(canvas, x, y, width, lines, role="bright", frame_role="frame"):
    """A +---+ box with centred lines; it clears whatever is underneath."""
    inner = width - 2
    edge = "+" + "-" * inner + "+"
    canvas.put(x, y, edge, frame_role)
    for i, text in enumerate(lines):
        canvas.put(x, y + 1 + i, "|", frame_role)
        canvas.put(x + 1, y + 1 + i, text.center(inner), role)
        canvas.put(x + inner + 1, y + 1 + i, "|", frame_role)
    canvas.put(x, y + 1 + len(lines), edge, frame_role)
