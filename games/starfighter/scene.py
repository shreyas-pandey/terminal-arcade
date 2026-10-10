"""Starfighter scene: title, playing, paused and game-over screens."""

import math

from engine.canvas import Canvas
from engine.controls import Controls
from engine.loop import Scene
from engine.text import draw_big_centered, draw_box

from .game import ENEMY_TYPES, HEIGHT, PLAYER_SPRITE, WIDTH, StarfighterGame

KEY = "starfighter"
PANEL_X = WIDTH + 5

KEYMAP = {
    "LEFT": "left", "a": "left",
    "RIGHT": "right", "d": "right",
    "UP": "up", "w": "up",
    "DOWN": "down", "s": "down",
    "SPACE": "fire",
    "p": "pause", "ESC": "pause",
}

CONTROLS = (
    "ARROWS / W A S D   fly",
    "SPACE (hold)       fire",
    "P / ESC            pause",
)


class StarfighterScene(Scene):
    def __init__(self, ctx):
        self.ctx = ctx
        self.controls = Controls(KEYMAP, ctx.is_down, repeat=("left", "right", "up", "down"),
                                 held=("fire",), das=0.12, arr=0.03)
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
                game.move(-1)
            elif action == "right":
                game.move(1)
            elif action == "up":
                game.move_vertical(-1)
            elif action == "down":
                game.move_vertical(1)
            elif action == "fire":  # only without key-held detection
                game.fire()
        game.firing = self.controls.held("fire")

    def _start(self):
        self.game = StarfighterGame()
        self.controls.reset()
        self.new_high = False
        self.state = "playing"

    def _record(self):
        game = self.game
        rank = self.ctx.saves.add_score(KEY, game.score, wave=game.wave)
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
        c = Canvas(56, 21)
        draw_big_centered(c, 0, "STAR", role=lambda i: f"logo{i}")
        draw_big_centered(c, 6, "FIGHTER", role=lambda i: f"logo{(i + 4) % 6}")
        ship_x = 25 + round(12 * math.sin(self.clock * 1.5))
        c.sprite(ship_x, 12, PLAYER_SPRITE, "player")
        if int(self.clock * 6) % 3 == 0:
            c.put(ship_x + 2, 11, "|", "bullet")
        c.center(15, f"HIGH SCORE  {self.best:07d}")
        for i, line in enumerate(CONTROLS):
            c.put(15, 16 + i, line, "dim")
        c.center(20, "ENTER start   ESC back")
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
            for sx, sy, speed in game.stars:
                put(int(sx), int(sy), ".", "star_bright" if speed > 3 else "star")
            frame = int(game.time * 3) % 2
            for e in game.enemies:
                put(round(e.x), round(e.y), ENEMY_TYPES[e.kind][0][frame], f"enemy_{e.kind}")
            for x, y in game.bullets:
                put(round(x), int(y), "|", "bullet")
            for x, y in game.enemy_bullets:
                put(round(x), int(y), "*", "enemy_bullet")
            if game.alive and (not game.invulnerable or int(game.time * 10) % 2 == 0):
                for dy, row in enumerate(PLAYER_SPRITE):
                    put(game.player_x, game.player_y + dy, row, "player")
            for boom in game.explosions:
                put(boom.x, boom.y, boom.frames[boom.frame], "explosion")

            message = None
            if game.banner > 0:
                message = f"WAVE {game.wave}"
            elif game.intermission is not None:
                message = "WAVE CLEAR"
            elif not game.alive and game.lives > 0:
                message = "GET READY"
            if message and self.state != "over":
                c.put(1 + (WIDTH - len(message)) // 2, 1 + HEIGHT // 2, message, "bright")

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
        c.put(x, 7, f"WAVE {game.wave:02d}")
        c.put(x, 9, "LIVES")
        for i in range(game.lives):
            c.put(x + 4 * i, 10, "/^\\", "player")
        return c
