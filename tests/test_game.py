"""Audio format regressions and timed failure flow; no window/audio required."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import json
import math
from array import array
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pygame
from game import Game, SoundKit, INTRO_DURATION
from arrowgame.levels import LEVELS


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.game = Game(self.temp.name)

    def tearDown(self):
        pygame.quit()
        self.temp.cleanup()

    def test_audio_length_with_default_and_preinitialised_mixers(self):
        for rate, channels in ((22050, 2), (44100, 2), (22050, 1)):
            pygame.mixer.quit()
            pygame.mixer.init(frequency=rate, size=-16, channels=channels)
            sound = SoundKit()
            self.assertAlmostEqual(sound.music.get_length(), 40, places=2)
            self.assertAlmostEqual(sound.sounds['click'].get_length(), .07, places=3)
            self.assertAlmostEqual(sound.heartbeat.get_length(), .8, places=3)
            self.assertAlmostEqual(sound.sounds['win'].get_length(), 1.65, places=3)
            sound.start_music()
            for _ in range(5):
                sound.toggle_music()
                sound.toggle_music()
            self.assertTrue(sound.music_channel.get_busy())
            self.assertEqual(sound.music_channel.get_sound(), sound.music)
            for _ in range(12):
                sound.play('hit')
            self.assertEqual(sound.music_channel.get_sound(), sound.music)
            sound.set_danger(True)
            for _ in range(12):
                sound.play('hit')
            self.assertEqual(sound.heartbeat_channel.get_sound(), sound.heartbeat)

    def test_audio_settings_are_independent_and_saved(self):
        self.game.action('music')
        data = json.loads(self.game.progress_file.read_text(encoding='utf-8'))
        self.assertFalse(data['music'])
        self.assertTrue(data['sound'])
        self.game.sound.music_enabled = True
        self.game.load_progress()
        self.assertFalse(self.game.sound.music_enabled)

    def test_missing_audio_device_does_not_enable_saved_audio(self):
        self.game.save_progress()
        pygame.mixer.quit()
        with patch('pygame.mixer.init', side_effect=pygame.error('no device')):
            self.game.sound = SoundKit()
        self.game.load_progress()
        self.game.action('music')
        self.game.action('sound')
        self.assertFalse(self.game.sound.enabled)
        self.assertFalse(self.game.sound.music_enabled)
        self.game.render()

    def test_third_collision_holds_fades_and_returns_to_original_result(self):
        game = self.game
        game.reset_level(0)
        with patch('game.time.monotonic') as now:
            for mistake in range(3):
                now.return_value = 100 + mistake * 3
                game.select_arrow(2, 2)
                now.return_value += .3
                game.update()
                self.assertEqual(game.scene, ('playing', 'last_chance', 'fail_intro')[mistake])
                if mistake == 1:
                    now.return_value += INTRO_DURATION + .01
                    game.update()
                    self.assertEqual(game.scene, 'playing')
            start = game.fail_intro_started
            for elapsed, alpha in ((0, 0), (.3, 128), (.6, 255), (1.59, 255)):
                now.return_value = start + elapsed
                game.update()
                game.render()
                self.assertAlmostEqual(game.fail_overlay.get_alpha(), alpha, delta=1)
                self.assertEqual(game.regions, [])
            now.return_value = start + .99
            game.update()
            game.render()
            self.assertEqual(game.fail_overlay.get_alpha(), 255)
            self.assertEqual(game.regions, [])
            game.action('restart')
            game.click((480, 510))
            self.assertEqual(game.scene, 'fail_intro')
            now.return_value = start + 1.95
            game.update()
            game.render()
            self.assertAlmostEqual(game.fail_overlay.get_alpha(), 128, delta=1)
            now.return_value = start + INTRO_DURATION + .01
            game.update()
            game.render()
            self.assertEqual(game.scene, 'fail')
            self.assertIn('restart', [action for rect, action in game.regions])
            game.action('restart')
            self.assertEqual(game.scene, 'playing')
            self.assertEqual(game.mistakes, 3)
            self.assertIsNone(game.fail_intro_started)

    def enter_last_chance(self):
        game = self.game
        game.reset_level(0)
        for _ in range(2):
            game.select_arrow(2, 2)
            game.animation['start'] -= 1
            game.update()
        self.assertEqual(game.scene, 'last_chance')

    def finish_last_chance(self):
        self.game.last_chance_started -= INTRO_DURATION + .01
        self.game.update()
        self.assertEqual(self.game.scene, 'playing')

    def test_last_chance_holds_fades_and_does_not_retrigger_after_legal_move(self):
        game = self.game
        self.enter_last_chance()
        self.assertTrue(game.sound.heartbeat_channel.get_busy())
        with patch('game.time.monotonic') as now:
            start = game.last_chance_started
            for elapsed, alpha in ((0, 0), (.3, 128), (.6, 255), (1.59, 255)):
                now.return_value = start + elapsed
                game.update()
                game.render()
                self.assertAlmostEqual(game.last_chance_overlay.get_alpha(), alpha, delta=1)
                self.assertEqual(game.regions, [])
            now.return_value = start + .99
            game.update()
            game.render()
            self.assertEqual(game.last_chance_overlay.get_alpha(), 255)
            self.assertEqual(game.regions, [])
            game.click((480, 435))
            game.action('restart')
            game.select_arrow(2, 2)
            self.assertEqual(game.mistakes, 1)
            self.assertEqual(game.scene, 'last_chance')
            now.return_value = start + 1.95
            game.update()
            game.render()
            self.assertAlmostEqual(game.last_chance_overlay.get_alpha(), 128, delta=1)
            now.return_value = start + INTRO_DURATION + .01
            game.update()
            self.assertEqual(game.scene, 'playing')
            self.assertTrue(game.sound.heartbeat_channel.get_busy())
            game.select_arrow(0, 0)
            now.return_value += .4
            game.update()
            self.assertEqual(game.scene, 'playing')
            self.assertEqual(game.board[0][0], '.')
            self.assertTrue(game.sound.danger)

    def test_heartbeat_is_audible_without_clipping_and_has_two_separate_beats(self):
        samples = array('h', self.game.sound.heartbeat.get_raw())[::2]
        rms = math.sqrt(sum((v / 32768) ** 2 for v in samples) / len(samples))
        self.assertGreater(rms, .07)
        self.assertLess(max(map(abs, samples)) / 32768, .65)
        # Each pulse is followed by silence, including across the loop join.
        rate = pygame.mixer.get_init()[0]
        for start, end in ((0, .04), (.27, .32), (.51, .8)):
            self.assertLessEqual(max(map(abs, samples[round(start*rate):round(end*rate)])), 1)

    def test_red_edges_fade_in_pulse_and_preserve_board_readability(self):
        game = self.game
        game.reset_level(0)
        with patch('game.time.monotonic') as now:
            now.return_value = 100
            game.mistakes = 1
            baseline = game.render().copy()
            game.sync_game_audio()
            first = game.render()
            self.assertEqual(pygame.image.tobytes(first, 'RGB'), pygame.image.tobytes(baseline, 'RGB'))
            now.return_value = 100.92  # Strong beat after the entrance fade.
            strong = game.render()
            now.return_value = 101.40  # Between beats.
            quiet = game.render()
            strong_edge = strong.get_at((4, 400))
            quiet_edge = quiet.get_at((4, 400))
            baseline_edge = baseline.get_at((4, 400))
            self.assertGreater(strong_edge.r, quiet_edge.r)
            self.assertGreater(quiet_edge.r, baseline_edge.r)
            self.assertGreater(strong_edge.r - strong_edge.g,
                               quiet_edge.r - quiet_edge.g)
            board_rect = pygame.Rect(285, 243, 390, 390)
            self.assertEqual(pygame.image.tobytes(strong.subsurface(board_rect), 'RGB'),
                             pygame.image.tobytes(baseline.subsurface(board_rect), 'RGB'))
            # Muting audio keeps the warning, then leaving fades it out.
            game.action('music')
            self.assertTrue(game.danger_effect.active)
            game.action('levels')
            self.assertFalse(game.danger_effect.active)
            self.assertGreater(game.danger_effect.level(now.return_value), 0)
            now.return_value += .51
            self.assertEqual(game.danger_effect.level(now.return_value), 0)

    def test_visual_pulse_uses_restarted_heartbeat_clock(self):
        game = self.game
        game.reset_level(0)
        with patch('game.time.monotonic') as now:
            now.return_value = 100
            game.mistakes = 1
            game.sync_game_audio()
            self.assertEqual(game.sound.heartbeat_started, 100)
            now.return_value = 101
            game.action('music')
            self.assertIsNone(game.sound.heartbeat_started)
            now.return_value = 102
            game.action('music')
            self.assertEqual(game.sound.heartbeat_started, 102)
            self.assertGreater(game.danger_effect.level(102.12, game.sound.heartbeat_started),
                               game.danger_effect.level(102.6, game.sound.heartbeat_started))
            game.action('restart')
            now.return_value += .51
            self.assertEqual(game.danger_effect.level(now.return_value), 0)

    def test_heartbeat_follows_music_switch_and_stops_after_leaving(self):
        game = self.game
        self.enter_last_chance()
        self.finish_last_chance()
        game.action('music')
        self.assertFalse(game.sound.heartbeat_channel.get_busy())
        game.action('music')
        self.assertTrue(game.sound.heartbeat_channel.get_busy())
        game.action('sound')
        self.assertTrue(game.sound.heartbeat_channel.get_busy())
        game.action('levels')
        self.assertFalse(game.sound.heartbeat_channel.get_busy())
        self.assertFalse(game.sound.danger)
        self.enter_last_chance()
        self.finish_last_chance()
        game.action('restart')
        self.assertFalse(game.sound.heartbeat_channel.get_busy())
        self.assertEqual(game.mistakes, 3)
        self.enter_last_chance()
        self.finish_last_chance()
        game.action('home')
        self.assertFalse(game.sound.heartbeat_channel.get_busy())

    def test_heartbeat_stops_on_win_and_failure(self):
        game = self.game
        self.enter_last_chance()
        self.finish_last_chance()
        game.select_arrow(2, 2)
        self.assertFalse(game.sound.heartbeat_channel.get_busy())
        game.animation['start'] -= 1
        game.update()
        self.assertEqual(game.scene, 'fail_intro')
        self.enter_last_chance()
        self.finish_last_chance()
        game.board = [['U']]
        game.select_arrow(0, 0)
        game.animation['start'] -= 1
        game.update()
        self.assertEqual(game.scene, 'win')
        self.assertFalse(game.sound.heartbeat_channel.get_busy())

    def test_missing_last_chance_image_keeps_heartbeat_and_gameplay(self):
        game = self.game
        game.reset_level(0)
        game.last_chance_overlay = None
        game.mistakes = 2
        game.select_arrow(2, 2)
        game.animation['start'] -= 1
        game.update()
        self.assertEqual(game.scene, 'playing')
        self.assertTrue(game.sound.heartbeat_channel.get_busy())

    def test_missing_photo_falls_back_to_result(self):
        game = self.game
        game.reset_level(0)
        game.fail_overlay = None
        game.mistakes = 1
        game.select_arrow(2, 2)
        game.animation['start'] -= 1
        game.update()
        self.assertEqual(game.scene, 'fail')
        game.render()

    def test_level_clock_pauses_during_meme_and_resumes_after(self):
        game = self.game
        with patch('game.time.monotonic') as now:
            now.return_value = 100
            game.reset_level(0)
            game.mistakes = 2
            now.return_value = 105
            game.select_arrow(2, 2)
            now.return_value = 105.3
            game.update()
            held = game.timer.elapsed_ms()
            now.return_value = 106
            game.update()
            self.assertEqual(game.timer.elapsed_ms(), held)
            now.return_value = 108
            game.update()
            self.assertEqual(game.timer.elapsed_ms(), held)
            now.return_value = 109
            self.assertEqual(game.timer.elapsed_ms(), held+1000)
            game.action('levels')
            now.return_value = 150
            self.assertEqual(game.timer.elapsed_ms(), held+1000)

    def test_all_levels_award_save_and_freeze_three_stars(self):
        game = self.game
        with patch('game.time.monotonic') as now:
            for index, level in enumerate(LEVELS):
                now.return_value = 1000+index*100
                game.reset_level(index)
                with patch.object(game.sound, 'play', wraps=game.sound.play) as play:
                    for row, col in level.solution:
                        game.select_arrow(row, col)
                        now.return_value += .4
                        game.update()
                    self.assertEqual(sum(call.args == ('win',) for call in play.call_args_list), 1)
                self.assertEqual(game.result_stars, 3)
                self.assertEqual(game.scene, 'complete' if index == 5 else 'win')
                elapsed = game.timer.elapsed_ms()
                now.return_value += 10
                game.update()
                game.render()
                self.assertEqual(game.timer.elapsed_ms(), elapsed)
                self.assertEqual(game.best[str(index)]['stars'], 3)
            game.load_progress()
            self.assertEqual(len(game.best), 6)
            self.assertTrue(all(record['stars'] == 3 for record in game.best.values()))
            game.action('first')
            self.assertEqual(game.result_stars, 0)
            self.assertEqual(game.timer.elapsed_ms(), 0)

    def test_auto_solve_plays_current_level_without_player_mistakes(self):
        game = self.game
        game.reset_level(0)
        game.action('auto_solve')
        self.assertIsNotNone(game.auto_solve_queue)
        self.assertIsNotNone(game.animation)

        for _ in range(LEVELS[0].arrows):
            self.assertIsNotNone(game.animation)
            game.animation['start'] -= 1
            game.update()

        self.assertEqual(game.scene, 'win')
        self.assertIsNone(game.animation)
        self.assertIsNone(game.auto_solve_queue)
        self.assertEqual(game.mistakes, 3)
        self.assertEqual(game.hints, 3)

    def test_auto_solve_blocks_board_clicks_but_restart_remains_available(self):
        game = self.game
        game.reset_level(0)
        game.render()
        game.action('auto_solve')
        remaining = game.count_arrows()
        game.click((480, 435))
        self.assertEqual(game.count_arrows(), remaining)
        self.assertEqual(game.mistakes, 3)
        game.action('restart')
        self.assertIsNone(game.auto_solve_queue)
        self.assertIsNone(game.animation)
        self.assertEqual(game.count_arrows(), LEVELS[0].arrows)

    def test_old_progress_keeps_unlocks_without_fabricating_times(self):
        old = {'unlocked': 4, 'best': {'0': {'mistakes': 0, 'hints': 1}}, 'sound': False}
        self.game.progress_file.write_text(json.dumps(old), encoding='utf-8')
        self.game.load_progress()
        self.assertEqual(self.game.unlocked, 4)
        self.assertEqual(self.game.best['0'], old['best']['0'])
        self.game.scene = 'levels'
        self.game.render()

    def test_victory_sound_has_headroom_and_respects_effects_mute(self):
        sound = self.game.sound
        pcm = array('h', sound.sounds['win'].get_raw())
        self.assertLess(max(map(abs, pcm)), 25000)
        self.assertGreater(max(map(abs, pcm)), 1000)
        pygame.mixer.stop()
        sound.enabled = False
        sound.play('win')
        self.assertFalse(pygame.mixer.get_busy())


if __name__ == '__main__':
    unittest.main()
