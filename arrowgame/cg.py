"""Offline CG images and pre-decoded GIF playback without a runtime decoder."""
from bisect import bisect_right
import json
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'cg'


def load_image(name, width):
    try:
        image = pygame.image.load(str(ROOT / name)).convert_alpha()
        height = round(width * image.get_height() / image.get_width())
        return pygame.transform.smoothscale(image, (width, height))
    except (OSError, pygame.error):
        return None


class AnimatedSticker:
    def __init__(self):
        self.frames, self.ends = [], []
        try:
            sheet = pygame.image.load(str(ROOT / 'dance_sheet.png')).convert_alpha()
            data = json.loads((ROOT / 'dance_frames.json').read_text(encoding='utf-8'))
            tile, columns = data['tile'], data['columns']
            total = 0
            for index, duration in enumerate(data['durations_ms']):
                frame = sheet.subsurface((index % columns * tile, index // columns * tile, tile, tile))
                self.frames.append(pygame.transform.smoothscale(frame, (480, 480)))
                total += duration
                self.ends.append(total)
        except (OSError, ValueError, KeyError, pygame.error):
            self.frames, self.ends = [], []

    def frame(self, elapsed):
        if not self.frames:
            return None
        milliseconds = max(0, elapsed * 1000) % self.ends[-1]
        return self.frames[bisect_right(self.ends, milliseconds)]
