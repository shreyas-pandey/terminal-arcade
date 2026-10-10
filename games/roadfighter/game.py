"""Road Fighter rules: a top-down racer on a two-way road.

Pure logic with no I/O; time enters through `update(dt)`. The field is
measured in characters: x across (0..WIDTH-1), y down (0..HEIGHT-1). Speeds
are in rows of road per second. Your car stays near the bottom while the
road scrolls down past it.

Lanes 0-1 carry oncoming traffic, lanes 2-3 carry slower traffic going your
way. Potholes make you skid; everything else is a crash.

Difficulty follows one dial, `intensity(stage)`: 0 at stage 1, rising evenly
to 1 at EXTREME_STAGE and flat after that. Every tuning knob reads from it.
"""

import random
from dataclasses import dataclass

WIDTH = 40
HEIGHT = 20

# Lanes are exactly one car wide, so traffic in neighbouring lanes is at most
# 2 columns apart (a ':' divider or the '||' centre line). Your 3-wide car
# can't fit in between: there is no safe column anywhere on the road.
ROAD_LEFT = 11  # column of the left edge line
LANE_WIDTH = 3
LANE_X = (ROAD_LEFT + 1, ROAD_LEFT + 5, ROAD_LEFT + 10, ROAD_LEFT + 14)  # left column of each lane
CENTER_X = ROAD_LEFT + 8  # the double centre line occupies this column and the next
ROAD_RIGHT = ROAD_LEFT + 17  # column of the right edge line
ONCOMING_LANES = (0, 1)
SAME_LANES = (2, 3)

CAR_WIDTH = 3
PLAYER_Y = HEIGHT - 4
PLAYER_MIN_X = ROAD_LEFT + 1
PLAYER_MAX_X = ROAD_RIGHT - CAR_WIDTH

START_LIVES = 3
EXTREME_STAGE = 8  # full traffic from here on
CRUISE_EASY, CRUISE_EXTREME = 10.0, 19.0
SPAWN_GAP_EASY, SPAWN_GAP_EXTREME = 10.0, 3.0  # rows of road between spawn rows
ONCOMING_EXTRA_EXTREME = 5.0  # added to oncoming speed at full intensity
MAX_SPEED_FACTOR = 1.7
MIN_SPEED = 4.0
ACCELERATION = 10.0
DECELERATION = 20.0
STAGE_LENGTH = 500.0  # rows of road per stage
STAGE_BANNER_TIME = 1.6
CRASH_TIME = 1.6
INVULNERABLE_TIME = 2.0
SKID_TIME = 0.7
SKID_SLOWDOWN = 0.55
OVERTAKE_SCORE = 25
TAP_TIME = 0.35  # how long one accelerate/brake key event lasts without held-key detection

SPRITES = {
    "player": ("/^\\", "|#|", "[=]"),
    "car": ("[^]", "|o|", "[_]"),  # same direction as you
    "oncoming": ("[=]", "|o|", "[v]"),
    "truck": ("[^]", "|H|", "|H|", "[_]"),
    "pothole": ("(_)",),
    "blockade": ("[X]",),
}
CARS = ("car", "oncoming", "truck")
CRASH_FRAMES = (("\\|/", "-*-", "/|\\"), (" * ", "*#*", " * "), (". .", " . ", ". ."))
CRASH_FRAME_TIME = 0.12


def _clamp(value, low, high):
    return max(low, min(high, value))


def _lerp(easy, extreme, t):
    return easy + (extreme - easy) * t


def intensity(stage):
    """0.0 at stage 1, rising evenly to 1.0 at EXTREME_STAGE, then flat."""
    return min(1.0, (stage - 1) / (EXTREME_STAGE - 1))


def cruise_speed(stage):
    return _lerp(CRUISE_EASY, CRUISE_EXTREME, intensity(stage))


def spawn_gap(stage):
    return _lerp(SPAWN_GAP_EASY, SPAWN_GAP_EXTREME, intensity(stage))


def max_per_row(stage):
    """Obstacles per spawn row; at least one lane always stays open."""
    return 1 if stage <= 3 else 2 if stage < EXTREME_STAGE else 3


def hazard_weights(lane, stage):
    """Relative odds of each obstacle kind; hazards unlock and thicken with the stage."""
    t = intensity(stage)
    pothole = _lerp(1, 3, t) if stage >= 2 else 0
    blockade = _lerp(1, 3, t) if stage >= 4 else 0
    if lane in ONCOMING_LANES:
        return {"oncoming": 6, "pothole": pothole, "blockade": blockade / 2}
    return {"car": 6, "truck": _lerp(1, 3, t) if stage >= 3 else 0, "pothole": pothole, "blockade": blockade}


def lane_left(lane, width):
    """x of a sprite of `width` centred in `lane`."""
    return LANE_X[lane] + (LANE_WIDTH - width) // 2


def sibling_lane(lane):
    return {0: 1, 1: 0, 2: 3, 3: 2}[lane]


@dataclass
class Obstacle:
    kind: str
    lane: int
    x: float
    y: float
    speed: float = 0.0  # ground speed: + same direction as you, - oncoming
    target_lane: int = None
    hit: bool = False
    passed: bool = False

    @property
    def sprite(self):
        return SPRITES[self.kind]

    @property
    def width(self):
        return len(self.sprite[0])

    @property
    def height(self):
        return len(self.sprite)

    @property
    def is_car(self):
        return self.kind in CARS

    def cells(self):
        ox, oy = round(self.x), round(self.y)
        return {
            (ox + dx, oy + dy)
            for dy, row in enumerate(self.sprite)
            for dx, ch in enumerate(row)
            if ch != " "
        }


class RoadGame:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.time = 0.0
        self.distance = 0.0
        self.bonus = 0
        self.lives = START_LIVES
        self.paused = False
        self.over = False

        self.player_x = lane_left(2, CAR_WIDTH)
        self.speed = self.cruise_speed
        self.alive = True
        self.crash_timer = 0.0
        self.crash_x = 0
        self.invulnerable = 0.0
        self.skid = 0.0
        self._skid_step = 0.0
        self.accelerating = False
        self.braking = False
        self._accel_tap = 0.0
        self._brake_tap = 0.0

        self.obstacles = []
        self._next_spawn = 12.0
        self.stage_banner = STAGE_BANNER_TIME
        self._stage = 1

    # --- derived ------------------------------------------------------

    @property
    def stage(self):
        return 1 + int(self.distance // STAGE_LENGTH)

    @property
    def score(self):
        return int(self.distance) + self.bonus

    @property
    def cruise_speed(self):
        return cruise_speed(self.stage)

    @property
    def max_speed(self):
        return self.cruise_speed * MAX_SPEED_FACTOR

    def player_cells(self):
        return {
            (self.player_x + dx, PLAYER_Y + dy)
            for dy, row in enumerate(SPRITES["player"])
            for dx, ch in enumerate(row)
            if ch != " "
        }

    # --- player -------------------------------------------------------

    def _can_drive(self):
        return self.alive and not self.over and not self.paused

    def steer(self, dx):
        if self._can_drive():
            self.player_x = _clamp(self.player_x + dx, PLAYER_MIN_X, PLAYER_MAX_X)

    def tap_accelerate(self):
        """One accelerate key event, for terminals without held-key detection."""
        self._accel_tap = TAP_TIME

    def tap_brake(self):
        self._brake_tap = TAP_TIME

    # --- time ---------------------------------------------------------

    def update(self, dt):
        if self.over or self.paused:
            return
        self.time += dt
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.stage_banner = max(0.0, self.stage_banner - dt)
        self._accel_tap = max(0.0, self._accel_tap - dt)
        self._brake_tap = max(0.0, self._brake_tap - dt)

        self._update_speed(dt)
        self.distance += self.speed * dt
        if self.stage != self._stage:
            self._stage = self.stage
            self.stage_banner = STAGE_BANNER_TIME

        self._move_traffic(dt)
        self._spawn()
        self._score_overtakes()
        self._collide()

        if not self.alive:
            self.crash_timer -= dt
            if self.crash_timer <= 0:
                if self.lives > 0:
                    self._respawn()
                else:
                    self.over = True

    def _update_speed(self, dt):
        if not self.alive:
            target = 0.0
        elif self.accelerating or self._accel_tap:
            target = self.max_speed
        elif self.braking or self._brake_tap:
            target = MIN_SPEED
        else:
            target = self.cruise_speed
        if self.speed < target:
            self.speed = min(target, self.speed + ACCELERATION * dt)
        else:
            self.speed = max(target, self.speed - DECELERATION * dt)

        if self.skid > 0 and self.alive:
            self.skid -= dt
            self._skid_step -= dt
            if self._skid_step <= 0:
                self._skid_step = 0.1
                self.player_x = _clamp(self.player_x + self.rng.choice((-1, 1)), PLAYER_MIN_X, PLAYER_MAX_X)

    def _move_traffic(self, dt):
        for o in self.obstacles:
            o.y += (self.speed - o.speed) * dt
            if o.target_lane is not None:
                tx = lane_left(o.target_lane, o.width)
                step = 8.0 * dt
                o.x += _clamp(tx - o.x, -step, step)
                if abs(tx - o.x) < 0.05:
                    o.x, o.lane, o.target_lane = tx, o.target_lane, None
        self._avoid_collisions()
        if self.stage >= 5:  # drivers start changing lanes on their own
            rate = 0.25 * intensity(self.stage)
            for o in self.obstacles:
                if o.kind == "car" and o.target_lane is None and self.rng.random() < rate * dt:
                    self._try_lane_change(o)
        self.obstacles = [o for o in self.obstacles if -12 < o.y < HEIGHT + 1]

    def _lane_free(self, lane, y, height, ignore):
        if self.alive and self._player_in_lane(lane) and PLAYER_Y - 2 < y + height and y < PLAYER_Y + 5:
            return False  # drivers never cut in on you
        return not any(
            o is not ignore and lane in (o.lane, o.target_lane) and o.y < y + height + 2 and y < o.y + o.height + 2
            for o in self.obstacles
        )

    def _player_in_lane(self, lane):
        left = LANE_X[lane]
        return self.player_x < left + LANE_WIDTH and left < self.player_x + CAR_WIDTH

    def _try_lane_change(self, car):
        other = sibling_lane(car.lane)
        if self._lane_free(other, car.y, car.height, car):
            car.target_lane = other
            return True
        return False

    def _avoid_collisions(self):
        """Cars closing on something in their lane change lanes, or slow to follow it."""
        for car in self.obstacles:
            if not car.is_car or car.target_lane is not None:
                continue
            for other in self.obstacles:
                if other is car or car.lane not in (other.lane, other.target_lane):
                    continue
                gap = other.y - car.y  # positive: other is below the car on screen
                car_closing = 0 < gap < car.height + 4 and car.speed < other.speed
                being_closed = 0 < -gap < other.height + 4 and other.speed < car.speed
                if not (car_closing or being_closed):
                    continue
                if not self._try_lane_change(car) and car_closing and other.is_car:
                    car.speed = other.speed  # stuck behind it: follow
                break

    def _spawn(self):
        if self.distance < self._next_spawn:
            return
        stage = self.stage
        self._next_spawn = self.distance + spawn_gap(stage) * self.rng.uniform(0.7, 1.3)

        for lane in self.rng.sample(range(4), self.rng.randint(1, max_per_row(stage))):
            kind = self._pick_kind(lane, stage)
            width, height = len(SPRITES[kind][0]), len(SPRITES[kind])
            y = -height - 1.0
            if not self._lane_free(lane, y, height, None):
                continue
            speed = 0.0
            if kind == "oncoming":
                speed = -(self.rng.uniform(3.0, 5.0) + ONCOMING_EXTRA_EXTREME * intensity(stage))
            elif kind == "car":
                speed = self.rng.uniform(0.35, 0.65) * self.cruise_speed
            elif kind == "truck":
                speed = self.rng.uniform(0.3, 0.45) * self.cruise_speed
            self.obstacles.append(Obstacle(kind, lane, lane_left(lane, width), y, speed))

    def _pick_kind(self, lane, stage):
        weights = hazard_weights(lane, stage)
        kinds = [k for k, w in weights.items() if w]
        return self.rng.choices(kinds, [weights[k] for k in kinds])[0]

    def _score_overtakes(self):
        for o in self.obstacles:
            if o.kind in ("car", "truck") and not o.passed and o.y > PLAYER_Y + len(SPRITES["player"]):
                o.passed = True
                if self.alive:
                    self.bonus += OVERTAKE_SCORE * self.stage

    def _collide(self):
        if not self.alive or self.invulnerable:
            return
        player = self.player_cells()
        for o in self.obstacles:
            if not o.cells() & player:
                continue
            if o.kind == "pothole":
                if not o.hit:
                    o.hit = True
                    self.skid = SKID_TIME
                    self.speed *= SKID_SLOWDOWN
                continue
            self.obstacles.remove(o)
            self._crash()
            return

    def _crash(self):
        self.alive = False
        self.lives -= 1
        self.crash_timer = CRASH_TIME
        self.crash_x = self.player_x
        self.skid = 0.0

    def _respawn(self):
        self.alive = True
        self.invulnerable = INVULNERABLE_TIME
        self.speed = self.cruise_speed * 0.5
        self.obstacles = [o for o in self.obstacles if o.y + o.height < PLAYER_Y - 6]

    @property
    def crash_frame(self):
        """The crash animation frame to draw, or None."""
        if self.alive:
            return None
        index = int((CRASH_TIME - self.crash_timer) / CRASH_FRAME_TIME)
        return CRASH_FRAMES[min(index, len(CRASH_FRAMES) - 1)]
