"""Transparent star rules, record migration, and a pausable level clock."""
import time


def time_target(arrows):
    # Three seconds per arrow plus observation time, rounded up to five seconds.
    return max(30, ((arrows * 3 + 15 + 4) // 5) * 5)


def award_stars(lives, elapsed_ms, target_seconds):
    if lives <= 0:
        return 0
    return 1 + int(lives >= 2) + int(elapsed_ms <= target_seconds * 1000)


def clean_record(value, target_seconds):
    if not isinstance(value, dict):
        return None
    mistakes, hints = value.get('mistakes'), value.get('hints')
    if type(mistakes) is not int or not 0 <= mistakes <= 2:
        return None
    if type(hints) is not int or not 0 <= hints <= 3:
        return None
    record = {'mistakes': mistakes, 'hints': hints}
    elapsed = value.get('elapsed_ms')
    if type(elapsed) is int and 0 <= elapsed <= 10**12:
        record.update(elapsed_ms=elapsed, stars=award_stars(3-mistakes, elapsed, target_seconds))
    return record


def better_record(candidate, previous):
    if previous is None or 'elapsed_ms' not in previous:
        return True
    def rank(record):
        return (-record['stars'], record['elapsed_ms'], record['mistakes'], record['hints'])
    return rank(candidate) < rank(previous)


def format_time(milliseconds):
    tenths = max(0, milliseconds) // 100
    minutes, seconds = divmod(tenths // 10, 60)
    return f'{minutes:02d}:{seconds:02d}.{tenths % 10}'


class LevelTimer:
    def __init__(self):
        self.accumulated = 0.0
        self.started = None

    def reset(self):
        self.accumulated = 0.0
        self.started = time.monotonic()

    def pause(self):
        if self.started is not None:
            self.accumulated += max(0.0, time.monotonic() - self.started)
            self.started = None

    def resume(self):
        if self.started is None:
            self.started = time.monotonic()

    def elapsed_ms(self):
        seconds = self.accumulated
        if self.started is not None:
            seconds += max(0.0, time.monotonic() - self.started)
        return round(seconds * 1000)
