"""Main loop and screen state machine: title -> playing <-> paused -> over."""

import time
from pathlib import Path

from . import highscore, render
from .game import Game
from .input import Controls

FPS = 60
MAX_START_LEVEL = 9
HIGHSCORE_PATH = Path(__file__).resolve().parent.parent / "highscore.json"


class App:
    def __init__(self, term, scores_path=HIGHSCORE_PATH):
        self.term = term
        self.scores_path = scores_path
        self.scores = highscore.load(scores_path)
        self.controls = Controls(term.is_down)
        self.screen = render.Screen(term.write)
        self.state = "title"
        self.start_level = 0
        self.game = None
        self.new_high = False
        self.running = True

    @property
    def best(self):
        return self.scores[0]["score"] if self.scores else 0

    def run(self):
        frame = 1.0 / FPS
        last = time.perf_counter()
        while self.running:
            start = time.perf_counter()
            dt = min(start - last, 0.1)
            last = start

            keys = self.term.read_keys()
            if "CTRL_C" in keys:
                break
            getattr(self, f"_on_{self.state}")(keys, start)
            if self.state == "playing":
                self.game.update(dt)
                if self.game.over:
                    self._finish()

            width, height = self.term.size()
            self.screen.draw(render.build_frame(self, width, height), (width, height))

            elapsed = time.perf_counter() - start
            if elapsed < frame:
                time.sleep(frame - elapsed)

    def _on_title(self, keys, now):
        for key in keys:
            if key in ("LEFT", "a"):
                self.start_level = max(0, self.start_level - 1)
            elif key in ("RIGHT", "d"):
                self.start_level = min(MAX_START_LEVEL, self.start_level + 1)
            elif key.isdigit():
                self.start_level = int(key)
            elif key == "ENTER":
                self._start()
                return
            elif key in ("q", "ESC"):
                self.running = False
                return

    def _on_playing(self, keys, now):
        game = self.game
        if game.paused and "q" in keys:
            self.running = False
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
            elif action == "rotate_cw":
                game.rotate(1)
            elif action == "rotate_ccw":
                game.rotate(-1)
            elif action == "hard_drop":
                game.hard_drop()
            elif action == "hold":
                game.hold()
            elif action == "soft_step":
                game.soft_drop_step()
        game.soft_drop = self.controls.soft_drop

    def _on_over(self, keys, now):
        if "ENTER" in keys:
            self._start()
        elif "q" in keys or "ESC" in keys:
            self.running = False

    def _start(self):
        self.game = Game(self.start_level)
        self.controls.reset()
        self.new_high = False
        self.state = "playing"

    def _finish(self):
        game = self.game
        self.scores, rank = highscore.add(self.scores, game.score, game.lines, game.level)
        highscore.save(self.scores_path, self.scores)
        self.new_high = rank == 0 and game.score > 0
        self.state = "over"
