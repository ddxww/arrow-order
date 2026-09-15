import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import json
import random
import tempfile
import unittest
from unittest.mock import Mock, patch
import pygame
from arrowgame.endless import generate_level, dependency_depth
from arrowgame.levels import LEVELS
from arrowgame.rules import can_exit, validate_board
from game import Game, INTRO_DURATION


class GeneratorTests(unittest.TestCase):
    def test_random_boards_stay_solvable_and_within_reference_limits(self):
        for tier, reference in enumerate(LEVELS, 1):
            seen = set()
            for seed in range(20):
                level = generate_level(seed+1, random.Random(seed), tier)
                validate_board(level.rows, require_all_directions=True)
                self.assertEqual((level.size, level.arrows), (reference.size, reference.arrows))
                self.assertGreaterEqual(dependency_depth(level.rows), 2)
                self.assertLessEqual(dependency_depth(level.rows), dependency_depth(reference.rows))
                seen.add(level.rows)
            self.assertGreater(len(seen), 10)

    def test_bounded_fallback_preserves_solvability(self):
        rng = Mock()
        rng.choice.side_effect = lambda choices: choices[0]
        rng.randrange.return_value = 1
        level = generate_level(1, rng, tier=6)
        validate_board(level.rows, require_all_directions=True)
        self.assertEqual(level.arrows, LEVELS[5].arrows)
        self.assertEqual(dependency_depth(level.rows), dependency_depth(LEVELS[5].rows))


class EndlessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.game = Game(self.temp.name)
        self.game.endless_rng.seed(2026)

    def tearDown(self):
        pygame.quit()
        self.temp.cleanup()

    def clear_current(self, now):
        for row, col in self.game.current_level.solution:
            self.game.select_arrow(row, col)
            now.return_value += .4
            self.game.update()

    def test_third_clear_unlocks_cg_once_and_does_not_change_campaign(self):
        game = self.game
        game.best = {'0': {'mistakes': 1, 'hints': 1, 'elapsed_ms': 20000, 'stars': 3}}
        before = json.dumps(game.best, sort_keys=True)
        game.render()
        self.assertIn('endless', [action for rect, action in game.regions])
        with patch('game.time.monotonic') as now:
            now.return_value = 100
            game.action('endless')
            for completed in range(1, 5):
                game.render()
                self.assertFalse(any('星' in text for text, rect in game.painter.text_bounds))
                self.clear_current(now)
                self.assertEqual(game.endless_clears, completed)
                self.assertEqual(game.result_stars, 0)
                self.assertIsNone(game.result_record)
                self.assertEqual(game.scene, 'endless_cg' if completed == 3 else 'endless_win')
                now.return_value += 10
                game.update()
                game.render()
                self.assertFalse(any('星' in text for text, rect in game.painter.text_bounds))
                if completed < 4:
                    game.action('endless_next')
                    self.assertEqual(game.mistakes, 3)
                    self.assertEqual(game.hints, 3)
                    self.assertEqual(game.timer.elapsed_ms(), 0)
            self.assertEqual(json.dumps(game.best, sort_keys=True), before)
            self.assertEqual(game.unlocked, 1)
            game.action('show_cg')
            self.assertEqual(game.scene, 'endless_cg')
            self.assertEqual(game.endless_clears, 4)
            game.action('home')
            game.action('endless')
            self.assertEqual(game.endless_clears, 0)
            self.assertFalse(game.endless_reward_shown)
            game.action('home')
            game.action(('level', 0))
            self.assertEqual(game.mode, 'campaign')

    def test_failure_retry_preserves_board_and_clears(self):
        game = self.game
        with patch('game.time.monotonic') as now:
            now.return_value = 100
            game.action('endless')
            self.clear_current(now)
            game.action('endless_next')
            original = game.current_level.rows
            blocked = next((r, c) for r, row in enumerate(game.board) for c, value in enumerate(row)
                           if value != '.' and not can_exit(game.board, r, c))
            game.mistakes = 1
            game.select_arrow(*blocked)
            now.return_value += .3
            game.update()
            now.return_value += INTRO_DURATION + .01
            game.update()
            self.assertEqual(game.scene, 'fail')
            game.render()
            game.action('restart')
            self.assertEqual(tuple(''.join(row) for row in game.board), original)
            self.assertEqual(game.endless_clears, 1)
            self.assertEqual(game.mistakes, 3)
            game.action('endless_next')  # Cannot skip a level via stale button input.
            self.assertEqual(game.endless_round, 2)

    def test_gif_animates_and_preserves_its_loop_duration(self):
        sticker = self.game.cg_sticker
        self.assertEqual(len(sticker.frames), 12)
        self.assertEqual(sticker.ends[-1], 1960)
        first = pygame.image.tobytes(sticker.frame(0), 'RGBA')
        later = pygame.image.tobytes(sticker.frame(.4), 'RGBA')
        self.assertNotEqual(first, later)
        self.assertEqual(first, pygame.image.tobytes(sticker.frame(1.96), 'RGBA'))
        self.assertIsNotNone(self.game.cg_wechat)
        self.assertIsNotNone(self.game.cg_emoji)


if __name__ == '__main__':
    unittest.main()
