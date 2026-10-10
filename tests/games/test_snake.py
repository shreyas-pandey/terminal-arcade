import random
import unittest
from collections import deque

from games.snake.game import FOOD_SCORE, HEIGHT, START_INTERVAL, START_LENGTH, WIDTH, SnakeGame


def new_game():
    return SnakeGame(rng=random.Random(1))


class SnakeTests(unittest.TestCase):
    def test_moves_one_cell_per_interval(self):
        game = new_game()
        x, y = game.head
        game.food = (0, 0)
        game.update(START_INTERVAL * 0.5)
        self.assertEqual(game.head, (x, y))
        game.update(START_INTERVAL * 0.6)
        self.assertEqual(game.head, (x + 1, y))
        self.assertEqual(len(game.body), START_LENGTH)

    def test_eating_grows_and_scores(self):
        game = new_game()
        x, y = game.head
        game.food = (x + 1, y)
        game.step()
        self.assertEqual(len(game.body), START_LENGTH + 1)
        self.assertEqual(game.score, FOOD_SCORE)
        self.assertNotIn(game.food, game.body)
        self.assertLess(game.interval, START_INTERVAL)

    def test_reverse_turn_ignored_and_turns_queue(self):
        game = new_game()
        self.assertFalse(game.turn("left"))  # heading right
        self.assertTrue(game.turn("up"))
        self.assertTrue(game.turn("left"))
        self.assertFalse(game.turn("down"))  # queue full
        game.food = (0, 0)
        x, y = game.head
        game.step()
        game.step()
        self.assertEqual(game.head, (x - 1, y - 1))

    def test_wall_kills(self):
        game = new_game()
        game.body = deque([(WIDTH - 1, 5), (WIDTH - 2, 5)])
        game.step()
        self.assertTrue(game.over)

    def test_biting_self_kills(self):
        game = new_game()
        game.body = deque([(5, 5), (6, 5), (6, 6), (5, 6), (4, 6)])
        game.direction = (0, 1)  # down into its own body
        game.food = (0, 0)
        game.step()
        self.assertTrue(game.over)

    def test_moving_into_vacating_tail_is_allowed(self):
        game = new_game()
        game.body = deque([(5, 5), (6, 5), (6, 6), (5, 6)])
        game.direction = (0, 1)  # the tail at (5, 6) moves away this step
        game.food = (0, 0)
        game.step()
        self.assertFalse(game.over)

    def test_filling_the_board_wins(self):
        game = new_game()
        cells = [(x, y) for y in range(HEIGHT) for x in range(WIDTH)]
        game.body = deque(cells[:-1])
        game._place_food()
        self.assertEqual(game.food, cells[-1])
        game.body = deque(cells)
        game._place_food()
        self.assertTrue(game.won)


if __name__ == "__main__":
    unittest.main()
