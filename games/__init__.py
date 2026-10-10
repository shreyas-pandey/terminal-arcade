"""The cartridges: every game the arcade can launch."""

from dataclasses import dataclass
from typing import Callable

from .roadfighter.scene import KEY as ROADFIGHTER_KEY, RoadFighterScene
from .snake.scene import KEY as SNAKE_KEY, SnakeScene
from .starfighter.scene import KEY as STARFIGHTER_KEY, StarfighterScene
from .tetris.scene import KEY as TETRIS_KEY, TetrisScene


@dataclass(frozen=True)
class GameInfo:
    key: str
    title: str
    blurb: str
    create: Callable  # (ctx) -> Scene


GAMES = (
    GameInfo(TETRIS_KEY, "TETRIS", "stack the falling blocks", TetrisScene),
    GameInfo(SNAKE_KEY, "SNAKE", "eat, grow, don't bite yourself", SnakeScene),
    GameInfo(STARFIGHTER_KEY, "STARFIGHTER", "hold the line against the swarm", StarfighterScene),
    GameInfo(ROADFIGHTER_KEY, "ROAD FIGHTER", "dodge the traffic, beat the road", RoadFighterScene),
)
