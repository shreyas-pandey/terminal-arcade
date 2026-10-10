# Contributing

Bug reports, fixes and new games are all welcome. Open an issue first for anything big so we can agree on the shape of it.

## Ground rules

- **Python standard library only.** No third-party packages, ever: `python arcade.py` must work on a fresh Python 3.10+.
- **Pure ASCII.** No Unicode box-drawing or block characters.
- **Draw with roles, not colours.** Games tag text with a role (`"player"`, `"enemy_boss"`, `"frame"`) and the display mode turns it into a colour. Never write ANSI codes yourself.
- **Fit in 60×24.** That's the smallest terminal the arcade supports.
- **Keep the rules pure.** A game's `game.py` does no I/O and takes time only through `update(dt)`, so it can be unit-tested.

## Add your own cartridge

A game is one package under `games/` with two modules, plus tests. Look at `games/snake/` for the smallest complete example.

```
games/<name>/
├── __init__.py
├── game.py      # rules: state, update(dt), actions. No I/O.
├── scene.py     # title / playing / paused / game-over screens, input, drawing
└── media/       # optional demo GIFs
tests/games/test_<name>.py
```

**1. Write the rules** in `game.py`: a class holding the game state, methods for player actions (`steer`, `fire`, ...), `update(dt)`, and `paused` / `over` flags. Pass in a `random.Random` so tests are deterministic.

**2. Write the scene** in `scene.py`, a subclass of `engine.loop.Scene`:

```python
KEY = "<name>"  # save file name and command-line name

class MyGameScene(Scene):
    def __init__(self, ctx): ...           # ctx gives you is_down, saves, theme
    def handle(self, keys, now): ...       # key names like "LEFT", "ENTER", "p"
    def update(self, dt): ...
    def render(self, theme): ...           # build an engine.canvas.Canvas, return canvas.lines(theme)
```

- Map keys to actions with `engine.controls.Controls`. It handles auto-repeat (`repeat=`), keys held down (`held=`) and one-shot presses for you.
- Record a finished game with `ctx.saves.add_score(KEY, score, **details)`. It returns the rank (0 means a new high score).
- Leave the game with `self.next_scene = ctx.exit_from(self)`. That returns to the arcade, or quits when the game was started on its own.
- Follow the other games' conventions: `ENTER` start, `P` / `Esc` pause, `Q` quit while paused, `Esc` back from the title screen.

**3. Give your roles colours** in `engine/theme.py`: add them to `_CGA`, and to `_MONO_BRIGHT` (what the player controls) or `_MONO_DIM` (background detail) for PHOSPHOR. Unknown roles fall back to normal green or light grey.

**4. Register the cartridge** by adding a `GameInfo` line to `GAMES` in `games/__init__.py`. It then shows up in the launcher, the boot screen, the high-score ticker and `python arcade.py <name>`.

**5. Test it** in `tests/games/test_<name>.py`: movement, scoring, how the game ends, and anything tricky. Then run everything:

```
python -m unittest
```

**6. Optionally add demo GIFs** as `games/<name>/media/<name>-phosphor.gif` and `<name>-cga.gif`: 10 seconds of gameplay, matching the other games' tiles. If you can't record them, say so in the PR and they can be made for you.

Finally, add a tile and a controls row to the README.
