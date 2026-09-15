"""Cached low-health vignette and shared heartbeat timing."""
import math
import time

import pygame

HEARTBEAT_PERIOD = .8
HEARTBEAT_PULSES = ((.04, .23, .55), (.32, .19, .43))


def heartbeat_strength(elapsed):
    phase = elapsed % HEARTBEAT_PERIOD
    strength = 0.0
    for start, duration, gain in HEARTBEAT_PULSES:
        local = phase - start
        if 0 <= local < duration:
            strength += gain * math.sin(math.pi * local / duration) ** 2 * math.exp(-local * 4)
    return min(1.0, strength / .36)


class DangerVignette:
    """Red at the screen edges, transparent over the board, softly pulsing."""
    FADE_IN = .8
    FADE_OUT = .5

    def __init__(self, size):
        # Build once at low resolution, then smoothly scale to the canvas.
        small = pygame.Surface((240, 200), pygame.SRCALPHA)
        width, height = small.get_size()
        for y in range(height):
            vertical = max(0, 1 - min(y, height - 1 - y) / (height * .18))
            vertical = vertical * vertical * (3 - 2 * vertical)
            for x in range(width):
                horizontal = max(0, 1 - min(x, width - 1 - x) / (width * .22))
                horizontal = horizontal * horizontal * (3 - 2 * horizontal)
                edge = max(horizontal, vertical)
                corner = horizontal * vertical
                small.set_at((x, y), (174, 20, 38, round(175 * edge + 35 * corner)))
        self.surface = pygame.transform.smoothscale(small, size)
        self.active = False
        self.started = None
        self.ended = None
        self.exit_level = 0.0

    def set_active(self, active, heartbeat_started=None):
        if active == self.active:
            return
        now = time.monotonic()
        if active:
            self.started = now
            self.ended = None
        else:
            self.exit_level = self.level(now, heartbeat_started)
            self.ended = now
        self.active = active

    def level(self, now, heartbeat_started=None):
        if self.active:
            fade = max(0.0, min(1.0, (now - self.started) / self.FADE_IN))
            fade = fade * fade * (3 - 2 * fade)
            beat_start = self.started if heartbeat_started is None else heartbeat_started
            return fade * (.42 + .36 * heartbeat_strength(now - beat_start))
        if self.ended is not None:
            fade = max(0.0, min(1.0, (now - self.ended) / self.FADE_OUT))
            return self.exit_level * (1 - fade * fade * (3 - 2 * fade))
        return 0.0

    def draw(self, canvas, heartbeat_started=None):
        alpha = round(255 * self.level(time.monotonic(), heartbeat_started))
        if alpha:
            self.surface.set_alpha(alpha)
            canvas.blit(self.surface, (0, 0))
