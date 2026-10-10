"""Game rules: spawning, movement, gravity, lock delay, hold, scoring.

Pure logic with no I/O. Time only enters through `update(dt)`.
"""

import random
from collections import deque
from dataclasses import dataclass

from .board import HIDDEN, Board
from .pieces import KINDS, SHAPES, SPAWN_X, kicks

NEXT_COUNT = 3
LOCK_DELAY = 0.5
LOCK_RESET_LIMIT = 15
SOFT_DROP_FACTOR = 20
LINE_CLEAR_TIME = 0.2
LINES_PER_LEVEL = 10
MAX_GRAVITY_LEVEL = 15
LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}


def gravity_interval(level):
    """Seconds per row: guideline formula (0.8 - (L-1)*0.007)^(L-1), L = level + 1."""
    n = min(level, MAX_GRAVITY_LEVEL)
    return (0.8 - n * 0.007) ** n


@dataclass
class Piece:
    kind: str
    rot: int = 0
    x: int = 0
    y: int = 0

    def cells(self, dx=0, dy=0, rot=None):
        state = self.rot if rot is None else rot
        return [(self.x + dx + cx, self.y + dy + cy) for cx, cy in SHAPES[self.kind][state]]


class Game:
    def __init__(self, start_level=0, rng=None):
        self.rng = rng or random.Random()
        self.board = Board()
        self.start_level = start_level
        self.level = start_level
        self.score = 0
        self.lines = 0
        self.hold_kind = None
        self.hold_used = False
        self.soft_drop = False
        self.paused = False
        self.over = False
        self.clearing_rows = []
        self.clear_timer = 0.0
        self.piece = None
        self._bag = []
        self.queue = deque(self._draw() for _ in range(NEXT_COUNT))
        self._spawn(self._next_from_queue())

    # --- piece supply -------------------------------------------------

    def _draw(self):
        if not self._bag:
            self._bag = list(KINDS)
            self.rng.shuffle(self._bag)
        return self._bag.pop()

    def _next_from_queue(self):
        kind = self.queue.popleft()
        self.queue.append(self._draw())
        return kind

    def _spawn(self, kind):
        piece = Piece(kind, 0, SPAWN_X[kind], 0)
        if not self.board.fits(piece.cells()):
            self.piece = None
            self.over = True  # block out
            return
        if self.board.fits(piece.cells(dy=1)):
            piece.y += 1
        self.piece = piece
        self._gravity_acc = 0.0
        self._lock_timer = None
        self._lock_resets = 0
        self._lowest_y = piece.y

    # --- player actions -----------------------------------------------

    def _active(self):
        return self.piece is not None and not self.over and not self.paused

    def _fits(self, dx=0, dy=0, rot=None):
        return self.board.fits(self.piece.cells(dx, dy, rot))

    def move(self, dx):
        if not self._active() or not self._fits(dx=dx):
            return False
        self.piece.x += dx
        self._on_moved()
        return True

    def rotate(self, direction):
        """Rotate clockwise (+1) or counter-clockwise (-1) using SRS kicks."""
        if not self._active():
            return False
        target = (self.piece.rot + direction) % 4
        for dx, dy in kicks(self.piece.kind, self.piece.rot, target):
            if self._fits(dx, dy, target):
                self.piece.x += dx
                self.piece.y += dy
                self.piece.rot = target
                self._on_moved()
                return True
        return False

    def soft_drop_step(self):
        """Drop one row immediately (used when key-held state is unavailable)."""
        if not self._active() or not self._fits(dy=1):
            return False
        self.piece.y += 1
        self.score += 1
        self._on_fell()
        return True

    def hard_drop(self):
        if not self._active():
            return
        distance = 0
        while self._fits(dy=1):
            self.piece.y += 1
            distance += 1
        self.score += 2 * distance
        self._lock()

    def hold(self):
        if not self._active() or self.hold_used:
            return False
        current = self.piece.kind
        if self.hold_kind is None:
            self.hold_kind = current
            self._spawn(self._next_from_queue())
        else:
            self.hold_kind, swapped = current, self.hold_kind
            self._spawn(swapped)
        self.hold_used = True
        return True

    def _on_moved(self):
        if self.piece.y > self._lowest_y:
            self._lowest_y = self.piece.y
            self._lock_resets = 0
        if self._lock_timer is not None:
            self._lock_resets += 1
            self._lock_timer = 0.0

    def _on_fell(self):
        self._lock_timer = None
        if self.piece.y > self._lowest_y:
            self._lowest_y = self.piece.y
            self._lock_resets = 0

    # --- time ---------------------------------------------------------

    def update(self, dt):
        if self.over or self.paused:
            return
        if self.clearing_rows:
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                self.board.clear_rows(self.clearing_rows)
                self.clearing_rows = []
                self._spawn(self._next_from_queue())
            return
        if self.piece is None:
            return

        interval = gravity_interval(self.level)
        if self.soft_drop:
            interval /= SOFT_DROP_FACTOR
        self._gravity_acc += dt
        while self._gravity_acc >= interval:
            self._gravity_acc -= interval
            if not self._fits(dy=1):
                self._gravity_acc = 0.0
                break
            self.piece.y += 1
            if self.soft_drop:
                self.score += 1
            self._on_fell()

        if self._fits(dy=1):
            self._lock_timer = None
            return
        self._lock_timer = (self._lock_timer or 0.0) + dt
        if self._lock_timer >= LOCK_DELAY or self._lock_resets >= LOCK_RESET_LIMIT:
            self._lock()

    def _lock(self):
        cells = self.piece.cells()
        self.board.place(cells)
        self.piece = None
        self.hold_used = False
        if all(y < HIDDEN for _, y in cells):
            self.over = True  # lock out
            return
        rows = self.board.full_rows()
        if not rows:
            self._spawn(self._next_from_queue())
            return
        self.score += LINE_SCORES[len(rows)] * (self.level + 1)
        self.lines += len(rows)
        self.level = max(self.start_level, self.lines // LINES_PER_LEVEL)
        self.clearing_rows = rows
        self.clear_timer = LINE_CLEAR_TIME
