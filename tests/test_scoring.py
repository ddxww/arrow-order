import unittest
from unittest.mock import patch
from arrowgame.scoring import LevelTimer, award_stars, better_record, clean_record
from arrowgame.levels import LEVELS


class ScoringTests(unittest.TestCase):
    def test_star_boundaries(self):
        self.assertEqual(award_stars(3, 45000, 45), 3)
        self.assertEqual(award_stars(2, 45000, 45), 3)
        self.assertEqual(award_stars(2, 45001, 45), 2)
        self.assertEqual(award_stars(1, 45000, 45), 2)
        self.assertEqual(award_stars(1, 45001, 45), 1)
        self.assertEqual(award_stars(0, 0, 45), 0)

    def test_more_lives_or_faster_time_never_reduce_stars(self):
        for level in LEVELS:
            target = level.target_seconds * 1000
            for lives in range(1, 4):
                self.assertGreaterEqual(award_stars(lives, target-1, level.target_seconds),
                                        award_stars(lives, target+1, level.target_seconds))
            self.assertEqual(sorted(award_stars(l, target, level.target_seconds) for l in range(4)),
                             [award_stars(l, target, level.target_seconds) for l in range(4)])

    def test_timer_excludes_pauses_and_freezes_on_finish(self):
        timer = LevelTimer()
        with patch('arrowgame.scoring.time.monotonic') as now:
            now.return_value = 100
            timer.reset()
            now.return_value = 105
            timer.pause()
            now.return_value = 110
            self.assertEqual(timer.elapsed_ms(), 5000)
            timer.resume()
            now.return_value = 112.5
            timer.pause()
            self.assertEqual(timer.elapsed_ms(), 7500)
            now.return_value = 200
            self.assertEqual(timer.elapsed_ms(), 7500)
            timer.reset()
            self.assertEqual(timer.elapsed_ms(), 0)

    def test_legacy_records_and_untrusted_rating(self):
        old = {'mistakes': 0, 'hints': 1}
        self.assertEqual(clean_record(old, 45), old)
        self.assertEqual(clean_record(dict(old, elapsed_ms=46000, stars=99), 45)['stars'], 2)
        self.assertEqual(clean_record(dict(old, elapsed_ms=-1), 45), old)
        self.assertIsNone(clean_record({'mistakes': True, 'hints': 0}, 45))

    def test_record_prefers_stars_then_time(self):
        base = {'mistakes': 1, 'hints': 0, 'stars': 3, 'elapsed_ms': 40000}
        self.assertFalse(better_record(dict(base, stars=2, elapsed_ms=1000), base))
        self.assertTrue(better_record(dict(base, elapsed_ms=39000), base))
        self.assertFalse(better_record(dict(base, elapsed_ms=41000), base))
        self.assertTrue(better_record(base, {'mistakes': 0, 'hints': 0}))


if __name__ == '__main__':
    unittest.main()
