import unittest

from games.tetris.board import HEIGHT, WIDTH, Board


class BoardTests(unittest.TestCase):
    def test_bounds(self):
        board = Board()
        self.assertTrue(board.is_free(0, 0))
        self.assertFalse(board.is_free(-1, 5))
        self.assertFalse(board.is_free(WIDTH, 5))
        self.assertFalse(board.is_free(3, HEIGHT))
        self.assertFalse(board.is_free(3, -1))

    def test_place_and_fits(self):
        board = Board()
        board.place([(2, 5)])
        self.assertFalse(board.fits([(1, 5), (2, 5)]))
        self.assertTrue(board.fits([(1, 5), (3, 5)]))

    def test_clear_non_adjacent_rows(self):
        board = Board()
        for x in range(WIDTH):
            board.grid[21][x] = True
            board.grid[19][x] = True
        board.grid[20][0] = True
        board.grid[18][3] = True

        rows = board.full_rows()
        self.assertEqual(rows, [19, 21])
        board.clear_rows(rows)

        self.assertEqual(len(board.grid), HEIGHT)
        self.assertTrue(board.grid[21][0])
        self.assertTrue(board.grid[20][3])
        self.assertEqual(sum(map(sum, board.grid)), 2)


if __name__ == "__main__":
    unittest.main()
