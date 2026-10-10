import random
import unittest

from games.starfighter.game import (
    ENEMY_TYPES, FORMATION, HEIGHT, INVULNERABLE_TIME, PLAYER_BOTTOM, PLAYER_TOP, PLAYER_WIDTH,
    RESPAWN_DELAY, START_LIVES, WIDTH, Enemy, StarfighterGame,
)

TICK = 1 / 60


def new_game():
    game = StarfighterGame(rng=random.Random(2))
    game.banner = 0.0
    game._dive_timer = game._fire_timer = 99.0  # keep enemies quiet unless a test wants them
    return game


def run(game, seconds):
    for _ in range(round(seconds / TICK)):
        game.update(TICK)


class FormationTests(unittest.TestCase):
    def test_full_formation_fits_the_field(self):
        game = new_game()
        self.assertEqual(len(game.enemies), sum(count for _, count, _ in FORMATION))
        for e in game.enemies:
            self.assertGreaterEqual(e.x - 3, 0)
            self.assertLessEqual(e.x + e.width + 3, WIDTH)


class PlayerTests(unittest.TestCase):
    def test_movement_is_clamped(self):
        game = new_game()
        for _ in range(60):
            game.move(-1)
        self.assertEqual(game.player_x, 0)
        for _ in range(60):
            game.move(1)
        self.assertEqual(game.player_x, WIDTH - PLAYER_WIDTH)
        for _ in range(10):
            game.move_vertical(-1)
            game.update(0.1)
        self.assertEqual(game.player_y, PLAYER_TOP)

    def test_fire_cooldown_and_bullet_cap(self):
        game = new_game()
        self.assertTrue(game.fire())
        self.assertFalse(game.fire())  # cooling down
        game.enemies = []
        game.intermission = 99
        for _ in range(5):
            game.update(0.2)
            game.fire()
        self.assertLessEqual(len(game.bullets), 3)

    def test_bullet_destroys_enemy_and_scores(self):
        game = new_game()
        target = Enemy("grunt", 20, 10, 20, 10)
        game.enemies = [target]
        game.bullets = [[21, 12.0]]
        run(game, 0.2)
        self.assertEqual(game.enemies, [])
        self.assertEqual(game.score, ENEMY_TYPES["grunt"][1])
        self.assertEqual(game.bullets, [])

    def test_diving_enemies_score_double(self):
        game = new_game()
        diver = Enemy("wing", 5, 5, 20, 10, state="dive", shot=True)
        game.enemies = [diver]
        game.bullets = [[21, 11.0]]
        game.update(TICK)
        self.assertEqual(game.score, 2 * ENEMY_TYPES["wing"][1])


class DamageTests(unittest.TestCase):
    def test_hit_costs_a_life_then_respawns_shielded(self):
        game = new_game()
        game.enemy_bullets = [[game.player_x + 2, game.player_y - 1.0]]
        run(game, 0.2)
        self.assertFalse(game.alive)
        self.assertEqual(game.lives, START_LIVES - 1)
        run(game, RESPAWN_DELAY + 0.1)
        self.assertTrue(game.alive)
        self.assertGreater(game.invulnerable, 0)
        game.enemy_bullets = [[game.player_x + 2, game.player_y - 1.0]]
        run(game, 0.2)
        self.assertTrue(game.alive)  # shield absorbs it
        run(game, INVULNERABLE_TIME)

    def test_diver_collision_kills_both(self):
        game = new_game()
        game.enemies = [Enemy("grunt", 0, 0, game.player_x + 1, PLAYER_BOTTOM + 1, state="dive", shot=True)]
        game.update(TICK)
        self.assertFalse(game.alive)
        self.assertEqual(game.enemies, [])

    def test_game_over_after_last_life(self):
        game = new_game()
        game.lives = 1
        game._player_hit()
        run(game, RESPAWN_DELAY + 0.1)
        self.assertTrue(game.over)


class WaveTests(unittest.TestCase):
    def test_clearing_a_wave_starts_the_next(self):
        game = new_game()
        game.enemies = []
        game.update(TICK)
        self.assertIsNotNone(game.intermission)
        run(game, 2.0)
        self.assertEqual(game.wave, 2)
        self.assertEqual(len(game.enemies), sum(count for _, count, _ in FORMATION))

    def test_divers_leave_and_return(self):
        game = new_game()
        game._dive_timer = 0.0
        game.update(TICK)
        divers = [e for e in game.enemies if e.state == "dive"]
        self.assertEqual(len(divers), 1)
        diver = divers[0]
        game.invulnerable = 999  # don't let it hit us
        for _ in range(60 * 10):
            game.update(TICK)
            if diver.state == "formation":
                break
        self.assertEqual(diver.state, "formation")
        self.assertLess(diver.y, HEIGHT)


if __name__ == "__main__":
    unittest.main()
