"""Terminal Arcade.

Usage:
    python arcade.py                 boot into the arcade
    python arcade.py --no-boot       skip the power-on screen
    python arcade.py <game>          play one game directly (tetris, snake, starfighter)
"""

import sys
from pathlib import Path

from engine.loop import Context, run
from engine.saves import Saves, migrate_legacy
from engine.terminal import Terminal
from engine.theme import by_key
from games import GAMES
from launcher.boot import BootScene
from launcher.menu import Launcher

ROOT = Path(__file__).resolve().parent


def main(argv):
    flags = {a for a in argv if a.startswith("-")}
    names = [a.lower() for a in argv if not a.startswith("-")]
    games = {g.key: g for g in GAMES}
    if "-h" in flags or "--help" in flags or (names and names[0] not in games):
        print(__doc__.strip())
        return 0 if not names else 2

    saves = Saves(ROOT / "saves")
    migrate_legacy(saves, ROOT / "highscore.json", "tetris")
    try:
        with Terminal() as term:
            ctx = Context(term.is_down, saves, by_key(saves.setting("display")))
            if names:
                scene = games[names[0]].create(ctx)
            else:
                launcher = Launcher(ctx, GAMES)
                ctx.home = launcher
                scene = launcher if "--no-boot" in flags else BootScene(ctx, launcher, GAMES)
            run(term, ctx, scene)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
