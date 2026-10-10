"""Starfighter rules: a Galaxian-style shooter.

Pure logic with no I/O; time enters through `update(dt)`. The field is
measured in characters: x across (0..WIDTH-1), y down (0..HEIGHT-1).
"""

import math
import random
from dataclasses import dataclass

WIDTH = 40
HEIGHT = 20

PLAYER_SPRITE = (" /^\\ ", "<[#]>")
PLAYER_WIDTH = 5
PLAYER_TOP = HEIGHT - 6  # highest row the ship may climb to
PLAYER_BOTTOM = HEIGHT - 2
START_LIVES = 3
FIRE_COOLDOWN = 0.16
MAX_PLAYER_BULLETS = 3
BULLET_SPEED = 32.0
ENEMY_BULLET_SPEED = 13.0
VERTICAL_COOLDOWN = 0.07
RESPAWN_DELAY = 1.5
INVULNERABLE_TIME = 2.0
WAVE_BANNER_TIME = 1.6
INTERMISSION_TIME = 1.5

SWAY = 3.0
DIVE_SPEED = 9.0
RETURN_SPEED = 10.0
EXPLOSION_FRAME = 0.08

# kind -> (animation frames, points); divers score double.
ENEMY_TYPES = {
    "boss": (("/=O=\\", "\\=O=/"), 50),
    "wing": (("<V>", ">V<"), 20),
    "grunt": (("{o}", "}o{"), 10),
}
# Formation rows from the top: (kind, count, spacing).
FORMATION = (("boss", 4, 8), ("wing", 6, 5), ("wing", 6, 5), ("grunt", 8, 4), ("grunt", 8, 4))
FORMATION_TOP = 1

SMALL_BOOM = ("\\*/", "-*-", " . ")
BIG_BOOM = ("\\\\|//", "-=*=-", "//|\\\\", " . . ")


def _clamp(value, low, high):
    return max(low, min(high, value))


@dataclass
class Enemy:
    kind: str
    home_x: float
    home_y: float
    x: float
    y: float
    state: str = "formation"  # formation | dive | return
    t: float = 0.0
    shot_at: float = 0.0
    shot: bool = False

    @property
    def width(self):
        return len(ENEMY_TYPES[self.kind][0][0])

    @property
    def points(self):
        return ENEMY_TYPES[self.kind][1] * (2 if self.state == "dive" else 1)

    def cells(self):
        ex, ey = round(self.x), round(self.y)
        return {(ex + i, ey) for i in range(self.width)}


@dataclass
class Explosion:
    x: int
    y: int
    frames: tuple
    t: float = 0.0

    @property
    def frame(self):
        return int(self.t / EXPLOSION_FRAME)

    @property
    def done(self):
        return self.frame >= len(self.frames)


class StarfighterGame:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.score = 0
        self.lives = START_LIVES
        self.wave = 0
        self.paused = False
        self.over = False
        self.time = 0.0

        self.player_x = (WIDTH - PLAYER_WIDTH) // 2
        self.player_y = PLAYER_BOTTOM
        self.alive = True
        self.respawn_timer = 0.0
        self.invulnerable = 0.0
        self.firing = False
        self._fire_cooldown = 0.0
        self._last_vertical = -1.0

        self.bullets = []  # [x, y]
        self.enemy_bullets = []
        self.enemies = []
        self.explosions = []
        self.stars = [
            [self.rng.uniform(0, WIDTH), self.rng.uniform(0, HEIGHT), self.rng.choice((2.0, 3.5, 6.0))]
            for _ in range(28)
        ]
        self.banner = 0.0
        self.intermission = None
        self._next_wave()

    # --- waves --------------------------------------------------------

    def _next_wave(self):
        self.wave += 1
        self.enemies = []
        for row, (kind, count, spacing) in enumerate(FORMATION):
            width = len(ENEMY_TYPES[kind][0][0])
            x0 = (WIDTH - ((count - 1) * spacing + width)) / 2
            for i in range(count):
                hx, hy = x0 + i * spacing, FORMATION_TOP + row
                self.enemies.append(Enemy(kind, hx, hy, hx, hy))
        self.banner = WAVE_BANNER_TIME
        self._dive_timer = 2.5
        self._fire_timer = 1.5

    @property
    def sway(self):
        return SWAY * math.sin(self.time * 0.8)

    # --- player -------------------------------------------------------

    def _can_act(self):
        return self.alive and not self.over and not self.paused

    def player_cells(self):
        return {
            (self.player_x + dx, self.player_y + dy)
            for dy, row in enumerate(PLAYER_SPRITE)
            for dx, ch in enumerate(row)
            if ch != " "
        }

    def move(self, dx):
        if self._can_act():
            self.player_x = _clamp(self.player_x + dx, 0, WIDTH - PLAYER_WIDTH)

    def move_vertical(self, dy):
        if self._can_act() and self.time - self._last_vertical >= VERTICAL_COOLDOWN:
            self.player_y = _clamp(self.player_y + dy, PLAYER_TOP, PLAYER_BOTTOM)
            self._last_vertical = self.time

    def fire(self):
        if not self._can_act() or self._fire_cooldown > 0 or len(self.bullets) >= MAX_PLAYER_BULLETS:
            return False
        self.bullets.append([self.player_x + PLAYER_WIDTH // 2, self.player_y - 1.0])
        self._fire_cooldown = FIRE_COOLDOWN
        return True

    # --- time ---------------------------------------------------------

    def update(self, dt):
        if self.over or self.paused:
            return
        self.time += dt
        self._fire_cooldown = max(0.0, self._fire_cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.banner = max(0.0, self.banner - dt)

        for star in self.stars:
            star[1] += star[2] * dt
            if star[1] >= HEIGHT:
                star[0], star[1] = self.rng.uniform(0, WIDTH), star[1] - HEIGHT

        if self.firing:
            self.fire()
        self._update_bullets(dt)
        self._update_enemies(dt)
        self._update_enemy_bullets(dt)
        self._collide_divers()

        for boom in self.explosions:
            boom.t += dt
        self.explosions = [b for b in self.explosions if not b.done]

        if not self.alive:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                if self.lives > 0:
                    self.alive = True
                    self.player_x = (WIDTH - PLAYER_WIDTH) // 2
                    self.player_y = PLAYER_BOTTOM
                    self.invulnerable = INVULNERABLE_TIME
                else:
                    self.over = True

        if not self.enemies and self.intermission is None:
            self.intermission = INTERMISSION_TIME
        if self.intermission is not None:
            self.intermission -= dt
            if self.intermission <= 0:
                self.intermission = None
                self._next_wave()

    def _update_bullets(self, dt):
        remaining = []
        for bullet in self.bullets:
            old_y = bullet[1]
            bullet[1] -= BULLET_SPEED * dt
            rows = range(math.floor(bullet[1]), math.floor(old_y) + 1)
            target = next((e for e in self.enemies
                           if any((round(bullet[0]), r) in e.cells() for r in rows)), None)
            if target:
                self._kill(target)
            elif bullet[1] >= 0:
                remaining.append(bullet)
        self.bullets = remaining

    def _kill(self, enemy):
        self.enemies.remove(enemy)
        self.score += enemy.points
        self.explosions.append(Explosion(round(enemy.x) + enemy.width // 2 - 1, round(enemy.y), SMALL_BOOM))

    def _update_enemies(self, dt):
        sway = self.sway
        for e in self.enemies:
            if e.state == "formation":
                e.x, e.y = e.home_x + sway, e.home_y
            elif e.state == "dive":
                e.t += dt
                e.y += (DIVE_SPEED + 0.5 * self.wave) * dt
                target = self.player_x + PLAYER_WIDTH / 2 - e.width / 2
                e.x += _clamp(target - e.x, -1, 1) * 6 * dt + math.sin(e.t * 4) * 8 * dt
                e.x = _clamp(e.x, 0, WIDTH - e.width)
                if not e.shot and e.t >= e.shot_at:
                    e.shot = True
                    self._enemy_fire(e)
                if e.y > HEIGHT:
                    e.state, e.y = "return", -1.0
            else:  # return to formation from the top
                tx, ty = e.home_x + sway, e.home_y
                step = RETURN_SPEED * dt
                e.x += _clamp(tx - e.x, -step, step)
                e.y += _clamp(ty - e.y, -step, step)
                if abs(tx - e.x) < 0.5 and abs(ty - e.y) < 0.5:
                    e.state = "formation"

        if self.banner > 0 or not self.alive:
            return
        speedup = 1 + 0.15 * (self.wave - 1)
        in_formation = [e for e in self.enemies if e.state == "formation"]

        self._dive_timer -= dt
        if self._dive_timer <= 0:
            self._dive_timer = self.rng.uniform(1.2, 2.6) / speedup
            divers = sum(1 for e in self.enemies if e.state != "formation")
            if in_formation and divers < min(4, 1 + self.wave // 2):
                diver = self.rng.choice(in_formation)
                diver.state, diver.t, diver.shot = "dive", 0.0, False
                diver.shot_at = self.rng.uniform(0.3, 0.9)

        self._fire_timer -= dt
        if self._fire_timer <= 0:
            self._fire_timer = self.rng.uniform(0.5, 1.3) / speedup
            if in_formation:
                self._enemy_fire(self.rng.choice(in_formation))

    def _enemy_fire(self, enemy):
        if len(self.enemy_bullets) < 2 + self.wave:
            self.enemy_bullets.append([round(enemy.x) + enemy.width // 2, enemy.y + 1])

    def _update_enemy_bullets(self, dt):
        remaining = []
        player = self.player_cells() if self.alive and not self.invulnerable else set()
        for bullet in self.enemy_bullets:
            old_y = bullet[1]
            bullet[1] += ENEMY_BULLET_SPEED * dt
            rows = range(math.floor(old_y), math.floor(bullet[1]) + 1)
            if player and any((round(bullet[0]), r) in player for r in rows):
                self._player_hit()
                player = set()
            elif bullet[1] < HEIGHT:
                remaining.append(bullet)
        self.enemy_bullets = remaining

    def _collide_divers(self):
        if not self.alive or self.invulnerable:
            return
        player = self.player_cells()
        for e in self.enemies:
            if e.state != "formation" and e.cells() & player:
                self._kill(e)
                self._player_hit()
                return

    def _player_hit(self):
        self.alive = False
        self.lives -= 1
        self.respawn_timer = RESPAWN_DELAY
        self.explosions.append(Explosion(self.player_x, self.player_y, BIG_BOOM))
