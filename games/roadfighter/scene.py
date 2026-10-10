"""Road Fighter scene: title, playing, paused and game-over screens."""

import math

from engine.canvas import Canvas
from engine.controls import Controls
from engine.loop import Scene
from engine.text import draw_big_centered, draw_box

from .game import (
    CENTER_X, HEIGHT, LANE_X, LANE_WIDTH, PLAYER_Y, ROAD_LEFT, ROAD_RIGHT, SPRITES, WIDTH, RoadGame,
)

KEY = "roadfighter"
PANEL_X = WIDTH + 5
KMH_PER_ROW = 8  # speed shown on the dashboard

KEYMAP = {
    "LEFT": "left", "a": "left",
    "RIGHT": "right", "d": "right",
    "UP": "accelerate", "w": "accelerate",
    "DOWN": "brake", "s": "brake",
    "p": "pause", "ESC": "pause",
}

CONTROLS = (
    "LEFT RIGHT / A D   steer",
    "UP / W (hold)      accelerate",
    "DOWN / S (hold)    brake",
    "P / ESC            pause",
)

ROLES = {"player": "car_player", "car": "car_same", "oncoming": "car_oncoming",
         "truck": "truck", "pothole": "pothole", "blockade": "blockade"}


def _scenery(ground_row, x):
    """Deterministic roadside detail for a road row and a shoulder column."""
    h = (ground_row * 2654435761 + x * 40503) & 0xFFFF
    if h % 37 == 0:
        return "^", "tree"
    if h % 19 == 0:
        return "*", "tree"
    if h % 9 == 0:
        return ".", "grass"
    return None


class RoadFighterScene(Scene):
    def __init__(self, ctx):
        self.ctx = ctx
        self.controls = Controls(KEYMAP, ctx.is_down, repeat=("left", "right"),
                                 held=("accelerate", "brake"), das=0.08, arr=0.03)
        self.state = "title"
        self.game = None
        self.new_high = False
        self.clock = 0.0

    def enter(self):
        self.controls.reset()

    @property
    def best(self):
        return self.ctx.saves.best(KEY)

    def handle(self, keys, now):
        if self.state in ("title", "over"):
            if "ENTER" in keys:
                self._start()
            elif "q" in keys or "ESC" in keys:
                self.next_scene = self.ctx.exit_from(self)
            return
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
                game.steer(-1)
            elif action == "right":
                game.steer(1)
            elif action == "accelerate":  # only without key-held detection
                game.tap_accelerate()
            elif action == "brake":
                game.tap_brake()
        game.accelerating = self.controls.held("accelerate")
        game.braking = self.controls.held("brake")

    def _start(self):
        self.game = RoadGame()
        self.controls.reset()
        self.new_high = False
        self.state = "playing"

    def _record(self):
        game = self.game
        rank = self.ctx.saves.add_score(KEY, game.score, stage=game.stage)
        self.new_high = rank == 0

    def update(self, dt):
        self.clock += dt
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
        c = Canvas(56, 23)
        draw_big_centered(c, 0, "ROAD", role=lambda i: f"logo{i}")
        draw_big_centered(c, 6, "FIGHTER", role=lambda i: f"logo{(i + 2) % 6}")
        scroll = int(self.clock * 12)
        for row in range(4):
            y = 12 + row
            c.put(19, y, "|", "road_edge")
            c.put(36, y, "|", "road_edge")
            c.put(27, y, "||", "road_center")
            if (row - scroll) % 4 < 2:
                c.put(23, y, ":", "road_line")
                c.put(32, y, ":", "road_line")
        car_x = 31 + round(2 * math.sin(self.clock * 2))  # weaves within your own lanes
        c.sprite(car_x, 12, SPRITES["player"], "car_player")
        c.center(17, f"HIGH SCORE  {self.best:07d}")
        for i, line in enumerate(CONTROLS):
            c.put(14, 18 + i, line, "dim")
        c.center(22, "ENTER start   ESC back")
        return c

    def _playfield(self):
        game = self.game
        c = Canvas(PANEL_X + 12, HEIGHT + 2)
        edge = "+" + "-" * WIDTH + "+"
        c.put(0, 0, edge, "frame")
        c.put(0, HEIGHT + 1, edge, "frame")
        for y in range(HEIGHT):
            c.put(0, y + 1, "|", "frame")
            c.put(WIDTH + 1, y + 1, "|", "frame")

        def put(x, y, text, role):  # field coordinates -> canvas, clipped to the field
            for i, ch in enumerate(text):
                fx = x + i
                if ch != " " and 0 <= fx < WIDTH and 0 <= y < HEIGHT:
                    c.put(1 + fx, 1 + y, ch, role)

        if game.paused:
            draw_box(c, 9, 7, 24, ["PAUSED", "", "P  resume", "Q  quit"])
        else:
            self._draw_road(put, game)
            for o in game.obstacles:
                for dy, row in enumerate(o.sprite):
                    put(round(o.x), round(o.y) + dy, row, ROLES[o.kind])
            if game.alive and (not game.invulnerable or int(game.time * 10) % 2 == 0):
                for dy, row in enumerate(SPRITES["player"]):
                    put(game.player_x, PLAYER_Y + dy, row, "car_player")
            frame = game.crash_frame
            if frame:
                for dy, row in enumerate(frame):
                    put(game.crash_x, PLAYER_Y + dy, row, "explosion")

            message = None
            if not game.alive and game.lives > 0:
                message = "CRASH!" if game.crash_timer > 0.8 else "GET READY"
            elif game.stage_banner > 0:
                message = f"STAGE {game.stage}"
            elif game.skid > 0:
                message = "SKID!"
            if message and self.state != "over":
                c.put(1 + (WIDTH - len(message)) // 2, 1 + HEIGHT // 2 - 3, message, "bright")

            if self.state == "over":
                draw_box(c, 8, 5, 26, [
                    "GAME OVER", "",
                    f"SCORE {game.score:07d}",
                    "NEW HIGH SCORE!" if self.new_high else "",
                    "",
                    "ENTER  play again",
                    "Q  quit",
                ])

        x = PANEL_X
        c.put(x, 1, "SCORE")
        c.put(x, 2, f"{game.score:07d}", "bright")
        c.put(x, 4, "HI SCORE")
        c.put(x, 5, f"{max(self.best, game.score):07d}", "bright")
        c.put(x, 7, f"STAGE {game.stage:02d}")
        c.put(x, 8, f"SPEED {round(game.speed * KMH_PER_ROW):03d}")
        c.put(x, 9, "      km/h", "dim")
        c.put(x, 11, "LIVES")
        for i in range(game.lives):
            c.put(x + 4 * i, 12, "[#]", "car_player")
        return c

    @staticmethod
    def _draw_road(put, game):
        scroll = int(game.distance)
        for y in range(HEIGHT):
            ground = y - scroll  # rows scroll down as the road moves
            for x in list(range(0, ROAD_LEFT)) + list(range(ROAD_RIGHT + 1, WIDTH)):
                detail = _scenery(ground, x)
                if detail:
                    put(x, y, *detail)
            put(ROAD_LEFT, y, "|", "road_edge")
            put(ROAD_RIGHT, y, "|", "road_edge")
            put(CENTER_X, y, "||", "road_center")
            if ground % 4 < 2:
                put(LANE_X[0] + LANE_WIDTH, y, ":", "road_line")
                put(LANE_X[2] + LANE_WIDTH, y, ":", "road_line")
