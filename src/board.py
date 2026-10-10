"""The playfield grid: collision, locking and line clearing."""

WIDTH = 10
VISIBLE_HEIGHT = 20
HIDDEN = 2  # rows above the visible field used for spawning
HEIGHT = VISIBLE_HEIGHT + HIDDEN


class Board:
    def __init__(self):
        self.grid = [[False] * WIDTH for _ in range(HEIGHT)]

    def is_free(self, x, y):
        return 0 <= x < WIDTH and 0 <= y < HEIGHT and not self.grid[y][x]

    def fits(self, cells):
        return all(self.is_free(x, y) for x, y in cells)

    def place(self, cells):
        for x, y in cells:
            self.grid[y][x] = True

    def full_rows(self):
        return [y for y, row in enumerate(self.grid) if all(row)]

    def clear_rows(self, rows):
        rows = set(rows)
        kept = [row for y, row in enumerate(self.grid) if y not in rows]
        self.grid = [[False] * WIDTH for _ in rows] + kept
