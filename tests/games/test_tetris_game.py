import random
import unittest

from games.tetris.board import WIDTH
from games.tetris.game import (
    LINE_CLEAR_TIME, LOCK_RESET_LIMIT, Game, Piece, gravity_interval,
)
from games.tetris.pieces import KINDS


def new_game(**kwargs):
    return Game(rng=random.Random(1), **kwargs)


def fill_row(game, y, except_cols=()):
    for x in range(WIDTH):
        if x not in except_cols:
            game.board.grid[y][x] = True


def place_vertical_i_at_column_0(game):
    # I in state R occupies box column 2, so x = -2 puts it in board column 0.
    game.piece = Piece("I", 1, -2, 0)


class BagTests(unittest.TestCase):
    def test_each_bag_contains_every_piece_once(self):
        game = new_game()
        game._bag = []
        draws = [game._draw() for _ in range(21)]
        for i in range(0, 21, 7):
            self.assertEqual(sorted(draws[i:i + 7]), sorted(KINDS))

    def test_queue_has_three_pieces(self):
        self.assertEqual(len(new_game().queue), 3)


class GravityTests(unittest.TestCase):
    def test_guideline_values(self):
        self.assertAlmostEqual(gravity_interval(0), 1.0)
        self.assertAlmostEqual(gravity_interval(1), 0.793, places=3)
        self.assertAlmostEqual(gravity_interval(8), 0.094, places=3)

    def test_capped(self):
        self.assertEqual(gravity_interval(30), gravity_interval(15))

    def test_piece_falls_one_row_per_interval(self):
        game = new_game()
        y = game.piece.y
        game.update(0.5)
        self.assertEqual(game.piece.y, y)
        game.update(0.6)
        self.assertEqual(game.piece.y, y + 1)


class RotationTests(unittest.TestCase):
    def test_t_wall_kick_off_left_wall(self):
        game = new_game()
        game.piece = Piece("T", 1, -1, 10)  # pointing right, flush with left wall
        self.assertTrue(game.rotate(-1))
        self.assertEqual((game.piece.rot, game.piece.x, game.piece.y), (0, 0, 10))

    def test_i_wall_kick_off_left_wall(self):
        game = new_game()
        game.piece = Piece("I", 3, -1, 10)  # vertical in column 0
        self.assertTrue(game.rotate(1))
        self.assertEqual((game.piece.rot, game.piece.x, game.piece.y), (0, 0, 10))

    def test_rotation_blocked(self):
        game = new_game()
        for y in range(10, 22):
            fill_row(game, y, except_cols=(0,))
        place_vertical_i_at_column_0(game)
        game.piece.y = 14
        self.assertFalse(game.rotate(1))
        self.assertEqual(game.piece.rot, 1)


class ScoringTests(unittest.TestCase):
    def test_tetris_with_hard_drop(self):
        game = new_game()
        for y in range(18, 22):
            fill_row(game, y, except_cols=(0,))
        place_vertical_i_at_column_0(game)
        game.hard_drop()
        self.assertEqual(game.score, 2 * 18 + 800)
        self.assertEqual(game.lines, 4)
        self.assertEqual(game.clearing_rows, [18, 19, 20, 21])

        game.update(LINE_CLEAR_TIME + 0.01)
        self.assertEqual(game.clearing_rows, [])
        self.assertEqual(sum(map(sum, game.board.grid)), 0)
        self.assertIsNotNone(game.piece)

    def test_single_scales_with_level(self):
        game = new_game(start_level=3)
        fill_row(game, 21, except_cols=(0,))
        place_vertical_i_at_column_0(game)
        game.hard_drop()
        self.assertEqual(game.score, 2 * 18 + 100 * 4)
        self.assertEqual(game.level, 3)

    def test_level_up_every_ten_lines(self):
        game = new_game()
        game.lines = 9
        fill_row(game, 21, except_cols=(0,))
        place_vertical_i_at_column_0(game)
        game.hard_drop()
        self.assertEqual(game.level, 1)

    def test_high_start_level_is_kept(self):
        game = new_game(start_level=5)
        game.lines = 9
        fill_row(game, 21, except_cols=(0,))
        place_vertical_i_at_column_0(game)
        game.hard_drop()
        self.assertEqual(game.level, 5)

    def test_soft_drop_scores_per_row(self):
        game = new_game()
        game.soft_drop_step()
        game.soft_drop_step()
        self.assertEqual(game.score, 2)


class LockDelayTests(unittest.TestCase):
    def test_locks_after_delay(self):
        game = new_game()
        game.piece = Piece("O", 0, 4, 20)
        game.update(0.4)
        self.assertFalse(game.board.grid[21][4])
        game.update(0.15)
        self.assertTrue(game.board.grid[21][4])

    def test_reset_limit(self):
        game = new_game()
        game.piece = Piece("O", 0, 4, 20)
        game.update(0.01)
        for i in range(LOCK_RESET_LIMIT - 1):
            self.assertTrue(game.move(1 if i % 2 == 0 else -1))
            game.update(0.01)
            self.assertFalse(any(game.board.grid[21]), f"locked after {i + 1} resets")
        game.move(1)
        game.update(0.01)
        self.assertTrue(any(game.board.grid[21]))


class HoldTests(unittest.TestCase):
    def test_hold_once_per_piece(self):
        game = new_game()
        first = game.piece.kind
        upcoming = game.queue[0]
        self.assertTrue(game.hold())
        self.assertEqual(game.hold_kind, first)
        self.assertEqual(game.piece.kind, upcoming)
        self.assertFalse(game.hold())

        game.hard_drop()
        self.assertFalse(game.hold_used)
        current = game.piece.kind
        self.assertTrue(game.hold())
        self.assertEqual(game.piece.kind, first)
        self.assertEqual(game.hold_kind, current)


class GameOverTests(unittest.TestCase):
    def test_block_out(self):
        game = new_game()
        fill_row(game, 0, except_cols=(9,))
        fill_row(game, 1, except_cols=(9,))
        game._spawn("T")
        self.assertTrue(game.over)

    def test_lock_out(self):
        game = new_game()
        game.piece = Piece("O", 0, 4, 0)
        fill_row(game, 2, except_cols=(9,))
        game.hard_drop()
        self.assertTrue(game.over)


if __name__ == "__main__":
    unittest.main()
