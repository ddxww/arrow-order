"""Render the original 'Quiet Afternoon' loop using only Python's stdlib.

Run from any directory. No samples, downloaded recordings or model services.
"""
from array import array
import math
from pathlib import Path
import sys
import wave

RATE = 22050
BPM = 72
BEAT = 60 / BPM
BARS = 12


def compose():
    length = round(RATE * BARS * 4 * BEAT)
    left, right = array('f', [0]) * length, array('f', [0]) * length

    def note(midi, beat, beats, volume, pan=0, pad=False):
        frequency = 440 * 2 ** ((midi - 69) / 12)
        start = round(beat * BEAT * RATE)
        duration = beats * BEAT
        count = round(duration * RATE)
        attack = .65 if pad else .075
        release = .8 if pad else .55
        gain_l = math.sqrt((1 - pan) / 2)
        gain_r = math.sqrt((1 + pan) / 2)
        omega = 2 * math.pi * frequency / RATE
        for i in range(count):
            t = i / RATE
            # Raised-cosine envelopes have no sharp edges at either end.
            envelope = (.5 - .5 * math.cos(math.pi * min(1, t / attack)))
            envelope *= .5 - .5 * math.cos(math.pi * min(1, (duration - t) / release))
            if not pad:
                envelope *= math.exp(-t / .9)
            phase = omega * i
            tone = math.sin(phase) + .10 * math.sin(2 * phase) + .018 * math.sin(3 * phase)
            value = volume * envelope * tone
            index = (start + i) % length  # Tails wrap naturally across the loop.
            left[index] += value * gain_l
            right[index] += value * gain_r

    # Fmaj9 / Am7 / Dm9 / Bbmaj7 / Gm9 / Csus2: close, gentle voice leading.
    chords = ((53, 57, 60, 64), (52, 55, 57, 60), (50, 53, 57, 64),
              (50, 53, 57, 58), (50, 53, 57, 62), (48, 55, 60, 62))
    # Two related phrases with rests; upper notes stay at or below C5.
    melody = ((0, 65), (2.5, 69), (5, 67), (7, 64), (8.5, 65), (11, 69),
              (12, 70), (14.5, 69), (17, 65), (19, 62), (21, 67),
              (24.5, 69), (27, 72), (29, 67), (31, 64), (32.5, 65),
              (35, 69), (36.5, 70), (39, 65), (41, 62), (44, 64), (46, 67))
    for bar in range(BARS):
        chord = chords[bar % len(chords)]
        for voice, midi in enumerate(chord):
            note(midi, bar * 4 - .3, 4.8, .025, (voice - 1.5) * .22, pad=True)
        for step, voice in ((.6, 0), (2.2, 2), (3.25, 1)):
            note(chord[voice] + 12, bar * 4 + step, 2.5, .022, -.25 if voice % 2 else .25)
    for index, (beat, midi) in enumerate(melody):
        note(midi, beat, 3.0, .065, .08 * math.sin(index))

    # Short, quiet cross-channel echoes add space without bright percussion.
    dry_l, dry_r = left[:], right[:]
    for delay, gain in ((.19, .13), (.37, .08)):
        offset = round(delay * RATE)
        for i in range(length):
            left[i] += dry_r[(i - offset) % length] * gain
            right[i] += dry_l[(i - offset) % length] * gain

    # A low-pass filter softens harmonics. Warm it using the loop's own tail.
    alpha = 1 - math.exp(-2 * math.pi * 1200 / RATE)
    for channel in (left, right):
        state = 0.0
        for value in channel[-RATE:]:
            state += alpha * (value - state)
        for i, value in enumerate(channel):
            state += alpha * (value - state)
            channel[i] = state
    peak = max(max(map(abs, left)), max(map(abs, right)))
    gain = min(1, .20 / peak)  # Ceiling at -14 dBFS; never boost a quiet mix.
    pcm = array('h')
    for l, r in zip(left, right):
        pcm.extend((round(l * gain * 32767), round(r * gain * 32767)))
    if sys.byteorder != 'little':
        pcm.byteswap()
    return pcm


def main():
    target = Path(__file__).resolve().parents[1] / 'assets' / 'audio' / 'quiet_afternoon.wav'
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), 'wb') as output:
        output.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
        output.writeframes(compose().tobytes())
    print(f'Created {target} ({BARS * 4 * BEAT:.0f} seconds, {BPM} BPM)')


if __name__ == '__main__':
    main()
