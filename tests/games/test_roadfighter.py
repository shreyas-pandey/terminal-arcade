import random
import unittest

from games.roadfighter.game import (
    EXTREME_STAGE, cruise_speed, hazard_weights, intensity, max_per_row, spawn_gap,
    LANE_X, SPRITES,
    CRASH_TIME, INVULNERABLE_TIME, MIN_SPEED, OVERTAKE_SCORE, PLAYER_MAX_X, PLAYER_MIN_X, PLAYER_Y,
    STAGE_LENGTH, START_LIVES, Obstacle, RoadGame, lane_left,
)

TICK = 1 / 60


def new_game(seed=1):
    game = RoadGame(rng=random.Random(seed))
    game._next_spawn = float("inf")  # no random traffic unless a test wants it
    return game


def run(game, seconds):
    for _ in range(round(seconds / TICK)):
        game.update(TICK)


def obstacle_on_player(game, kind, speed=0.0):
    return Obstacle(kind, 2, game.player_x, PLAYER_Y, speed)


class DrivingTests(unittest.TestCase):
    def test_no_safe_column_between_lanes(self):
        # Wherever you steer, some lane's traffic overlaps your car.
        spans = [set(range(lane_left(lane, 3), lane_left(lane, 3) + 3)) for lane in range(len(LANE_X))]
        for x in range(PLAYER_MIN_X, PLAYER_MAX_X + 1):
            car = set(range(x, x + 3))
            self.assertTrue(any(car & span for span in spans), f"x={x} dodges every lane")

    def test_every_obstacle_fits_its_lane(self):
        for kind, sprite in SPRITES.items():
            self.assertEqual(len(sprite[0]), 3, kind)

    def test_steering_is_clamped_to_the_road(self):
        game = new_game()
        for _ in range(50):
            game.steer(-1)
        self.assertEqual(game.player_x, PLAYER_MIN_X)
        for _ in range(50):
            game.steer(1)
        self.assertEqual(game.player_x, PLAYER_MAX_X)

    def test_accelerate_and_brake(self):
        game = new_game()
        cruise = game.speed
        game.accelerating = True
        run(game, 2)
        self.assertGreater(game.speed, cruise)
        game.accelerating, game.braking = False, True
        run(game, 2)
        self.assertEqual(game.speed, MIN_SPEED)
        game.braking = False
        run(game, 3)
        self.assertAlmostEqual(game.speed, game.cruise_speed)

    def test_taps_work_without_held_keys(self):
        game = new_game()
        cruise = game.speed
        game.tap_accelerate()
        run(game, 0.2)
        self.assertGreater(game.speed, cruise)

    def test_distance_scores_and_stages_advance(self):
        game = new_game()
        game.distance = STAGE_LENGTH - 1
        run(game, 0.5)
        self.assertEqual(game.stage, 2)
        self.assertGreater(game.stage_banner, 0)
        self.assertGreater(game.cruise_speed, RoadGame(rng=random.Random(1)).cruise_speed)
        self.assertGreaterEqual(game.score, int(STAGE_LENGTH))


class HazardTests(unittest.TestCase):
    def test_car_crash_costs_a_life_then_respawns_shielded(self):
        game = new_game()
        game.obstacles = [obstacle_on_player(game, "car", speed=5.0)]
        game.update(TICK)
        self.assertFalse(game.alive)
        self.assertEqual(game.lives, START_LIVES - 1)
        run(game, CRASH_TIME + 0.1)
        self.assertTrue(game.alive)
        self.assertGreater(game.invulnerable, 0)
        game.obstacles = [obstacle_on_player(game, "blockade")]
        game.update(TICK)
        self.assertTrue(game.alive)  # shielded
        run(game, INVULNERABLE_TIME)

    def test_blockade_crashes(self):
        game = new_game()
        game.obstacles = [obstacle_on_player(game, "blockade")]
        game.update(TICK)
        self.assertFalse(game.alive)

    def test_pothole_skids_instead_of_crashing(self):
        game = new_game()
        speed = game.speed
        game.obstacles = [obstacle_on_player(game, "pothole")]
        game.update(TICK)
        self.assertTrue(game.alive)
        self.assertGreater(game.skid, 0)
        self.assertLess(game.speed, speed)
        skid_speed = game.speed
        game.update(TICK)  # the same pothole only counts once
        self.assertGreaterEqual(game.speed, skid_speed)

    def test_game_over_after_last_life(self):
        game = new_game()
        game.lives = 1
        game._crash()
        run(game, CRASH_TIME + 0.1)
        self.assertTrue(game.over)

    def test_overtaking_scores_a_bonus(self):
        game = new_game()
        game.player_x = lane_left(3, 3)
        game.obstacles = [Obstacle("car", 2, lane_left(2, 3), PLAYER_Y - 1, speed=4.0)]
        run(game, 1.0)
        self.assertEqual(game.bonus, OVERTAKE_SCORE)
        self.assertTrue(game.alive)


class DifficultyTests(unittest.TestCase):
    def test_ramps_up_until_extreme_stage_then_holds(self):
        stages = range(1, EXTREME_STAGE + 1)
        self.assertEqual(intensity(1), 0.0)
        self.assertEqual(intensity(EXTREME_STAGE), 1.0)
        for a, b in zip(stages, stages[1:]):
            self.assertLess(cruise_speed(a), cruise_speed(b))
            self.assertGreater(spawn_gap(a), spawn_gap(b))
        for later in (EXTREME_STAGE + 1, EXTREME_STAGE + 10):
            self.assertEqual(cruise_speed(later), cruise_speed(EXTREME_STAGE))
            self.assertEqual(spawn_gap(later), spawn_gap(EXTREME_STAGE))

    def test_full_traffic_only_at_extreme_stage(self):
        self.assertEqual(max_per_row(1), 1)
        self.assertLess(max_per_row(EXTREME_STAGE - 1), 3)
        self.assertEqual(max_per_row(EXTREME_STAGE), 3)

    def test_hazards_unlock_gradually(self):
        self.assertEqual(hazard_weights(2, 1), {"car": 6, "truck": 0, "pothole": 0, "blockade": 0})
        self.assertGreater(hazard_weights(2, 2)["pothole"], 0)
        self.assertEqual(hazard_weights(2, 3)["blockade"], 0)
        self.assertGreater(hazard_weights(2, 4)["blockade"], 0)


class TrafficTests(unittest.TestCase):
    def test_spawns_always_leave_a_lane_open(self):
        game = RoadGame(rng=random.Random(5))
        game.distance = STAGE_LENGTH * 6  # deep into the hardest stages
        game._next_spawn = game.distance
        game.invulnerable = 1e9
        for _ in range(400):
            before = len(game.obstacles)
            game._spawn()
            fresh = game.obstacles[before:]
            self.assertLessEqual(len({o.lane for o in fresh}), 3)
            game._next_spawn = game.distance

    def test_car_changes_lane_to_avoid_a_blockade(self):
        game = new_game()
        game.player_x = lane_left(0, 3)
        car = Obstacle("car", 2, lane_left(2, 3), 8.0, speed=6.0)
        blockade = Obstacle("blockade", 2, lane_left(2, 3), 4.0)
        game.obstacles = [car, blockade]
        game.update(TICK)
        self.assertEqual(car.target_lane, 3)

    def test_cars_never_cut_in_on_the_player(self):
        game = new_game()
        game.player_x = lane_left(3, 3)  # alongside, in the lane the car would swerve into
        car = Obstacle("car", 2, lane_left(2, 3), PLAYER_Y - 3, speed=6.0)
        blockade = Obstacle("blockade", 2, lane_left(2, 3), PLAYER_Y - 7)
        game.obstacles = [car, blockade]
        game.update(TICK)
        self.assertIsNone(car.target_lane)

    def test_car_follows_when_it_cannot_change_lane(self):
        game = new_game()
        game.player_x = lane_left(0, 3)
        slow = Obstacle("truck", 2, lane_left(2, 3), 8.0, speed=3.0)
        fast = Obstacle("car", 2, lane_left(2, 3), 4.0, speed=2.0)  # above, closing on the truck
        blocker = Obstacle("car", 3, lane_left(3, 3), 4.0, speed=2.0)
        game.obstacles = [slow, fast, blocker]
        game.update(TICK)
        self.assertIsNone(fast.target_lane)
        self.assertEqual(fast.speed, slow.speed)


if __name__ == "__main__":
    unittest.main()
