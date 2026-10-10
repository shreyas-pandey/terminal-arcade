"""Tetromino shapes, SRS rotation states and wall-kick tables.

Coordinates are (x, y) with y growing downwards (screen space). Rotation
states are numbered 0 (spawn), 1 (R, clockwise), 2 (180) and 3 (L).
"""

KINDS = ("I", "O", "T", "S", "Z", "J", "L")

# Spawn-state cells inside an n x n bounding box.
_SPAWN_SHAPES = {
    "I": (4, ((0, 1), (1, 1), (2, 1), (3, 1))),
    "O": (2, ((0, 0), (1, 0), (0, 1), (1, 1))),
    "T": (3, ((1, 0), (0, 1), (1, 1), (2, 1))),
    "S": (3, ((1, 0), (2, 0), (0, 1), (1, 1))),
    "Z": (3, ((0, 0), (1, 0), (1, 1), (2, 1))),
    "J": (3, ((0, 0), (0, 1), (1, 1), (2, 1))),
    "L": (3, ((2, 0), (0, 1), (1, 1), (2, 1))),
}

# Column of the bounding box's left edge at spawn (pieces centred, rounded left).
SPAWN_X = {kind: 3 for kind in KINDS}
SPAWN_X["O"] = 4


def _rotate_cw(cells, n):
    return tuple(sorted((n - 1 - y, x) for x, y in cells))


def _build_shapes():
    shapes = {}
    for kind, (n, cells) in _SPAWN_SHAPES.items():
        states = [tuple(sorted(cells))]
        for _ in range(3):
            states.append(_rotate_cw(states[-1], n))
        shapes[kind] = tuple(states)
    return shapes


SHAPES = _build_shapes()

# SRS kick offsets as published (y grows upwards), keyed by (from, to).
_JLSTZ_KICKS = {
    (0, 1): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (1, 0): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    (1, 2): ((0, 0), (1, 0), (1, -1), (0, 2), (1, 2)),
    (2, 1): ((0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)),
    (2, 3): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
    (3, 2): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (3, 0): ((0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)),
    (0, 3): ((0, 0), (1, 0), (1, 1), (0, -2), (1, -2)),
}

_I_KICKS = {
    (0, 1): ((0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)),
    (1, 0): ((0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)),
    (1, 2): ((0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)),
    (2, 1): ((0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)),
    (2, 3): ((0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)),
    (3, 2): ((0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)),
    (3, 0): ((0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)),
    (0, 3): ((0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)),
}


def _to_screen(table):
    return {key: tuple((x, -y) for x, y in offsets) for key, offsets in table.items()}


JLSTZ_KICKS = _to_screen(_JLSTZ_KICKS)
I_KICKS = _to_screen(_I_KICKS)


def kicks(kind, from_rot, to_rot):
    """Offsets (dx, dy) to try, in order, when rotating between two states."""
    if kind == "O":
        return ((0, 0),)
    table = I_KICKS if kind == "I" else JLSTZ_KICKS
    return table[(from_rot, to_rot)]
