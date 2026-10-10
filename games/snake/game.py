"""Snake rules. Pure logic with no I/O; time enters through `update(dt)`."""

import random
from collections import deque

WIDTH = 20
HEIGHT = 18
START_LENGTH = 4
START_INTERVAL = 0.16  # seconds per step
MIN_INTERVAL = 0.06
SPEEDUP = 0.004  # per food eaten
FOOD_SCORE = 10
MAX_QUEUED_TURNS = 2

DIRECTIONS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class SnakeGame:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        y = HEIGHT // 2
        head_x = WIDTH // 2
        self.body = deque((head_x - i, y) for i in range(START_LENGTH))  # head first
        self.direction = DIRECTIONS["right"]
        self.turns = deque()
        self.score = 0
        self.eaten = 0
        self.paused = False
        self.over = False
        self.won = False
        self._timer = 0.0
        self.food = None
        self._place_food()

    @property
    def head(self):
        return self.body[0]

    @property
    def interval(self):
        return max(MIN_INTERVAL, START_INTERVAL - SPEEDUP * self.eaten)

    @property
    def speed(self):
        """1 at the start, rising as the snake speeds up."""
        return 1 + round((START_INTERVAL - self.interval) / SPEEDUP / 5)

    def turn(self, name):
        """Queue a turn; reversals and repeats are ignored."""
        new = DIRECTIONS[name]
        last = self.turns[-1] if self.turns else self.direction
        if new == last or new == (-last[0], -last[1]) or len(self.turns) >= MAX_QUEUED_TURNS:
            return False
        self.turns.append(new)
        return True

    def update(self, dt):
        if self.over or self.paused:
            return
        self._timer += dt
        while self._timer >= self.interval and not self.over:
            self._timer -= self.interval
            self.step()

    def step(self):
        if self.turns:
            self.direction = self.turns.popleft()
        x, y = self.head
        head = (x + self.direction[0], y + self.direction[1])
        eating = head == self.food
        body = set(self.body)
        if not eating:
            body.discard(self.body[-1])  # the tail moves out of the way
        if not (0 <= head[0] < WIDTH and 0 <= head[1] < HEIGHT) or head in body:
            self.over = True
            return
        self.body.appendleft(head)
        if eating:
            self.eaten += 1
            self.score += FOOD_SCORE
            self._place_food()
        else:
            self.body.pop()

    def _place_food(self):
        occupied = set(self.body)
        free = [(x, y) for y in range(HEIGHT) for x in range(WIDTH) if (x, y) not in occupied]
        if not free:
            self.food = None
            self.over = self.won = True
            return
        self.food = self.rng.choice(free)
