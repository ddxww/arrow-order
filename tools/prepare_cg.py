"""Pre-render the supplied animated GIF and emoji; Pillow is build-time only."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageSequence

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets' / 'cg'


def main():
    frames, durations = [], []
    with Image.open(DEST / 'author_dance.gif') as source:
        for frame in ImageSequence.Iterator(source):
            # Pillow composites disposal/transparency before conversion.
            image = frame.convert('RGBA')
            image.thumbnail((256, 256), Image.Resampling.LANCZOS)
            tile = Image.new('RGBA', (256, 256))
            tile.alpha_composite(image, ((256-image.width)//2, (256-image.height)//2))
            frames.append(tile)
            durations.append(max(20, frame.info.get('duration', 100)))
    columns = min(8, len(frames))
    sheet = Image.new('RGBA', (columns*256, ((len(frames)+columns-1)//columns)*256))
    for index, frame in enumerate(frames):
        sheet.alpha_composite(frame, ((index % columns)*256, (index//columns)*256))
    sheet.save(DEST / 'dance_sheet.png')
    (DEST / 'dance_frames.json').write_text(json.dumps({'tile': 256, 'columns': columns, 'durations_ms': durations}), encoding='utf-8')
    emoji = Image.new('RGBA', (100, 100))
    draw = ImageDraw.Draw(emoji)
    font = ImageFont.truetype('C:/Windows/Fonts/seguiemj.ttf', 80)
    draw.text((50, 50), '\U0001f9e7', font=font, anchor='mm', embedded_color=True)
    emoji.save(DEST / 'red_envelope.png')
    print(f'Prepared {len(frames)} frames, {sum(durations)} ms loop, and red-envelope emoji')


if __name__ == '__main__':
    main()
