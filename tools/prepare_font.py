"""Create OFL-licensed static fonts with readable weights and GB2312 coverage.

Developer-only dependency: fonttools. Runtime users get the generated fonts.
Source: Noto Sans SC (Google Fonts). Derivatives are renamed ArrowOrder Sans.
"""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "assets" / "fonts"


def main():
    chars = set(chr(i) for i in range(32, 127))
    for first in range(0xA1, 0xF8):
        for second in range(0xA1, 0xFF):
            try:
                chars.update(bytes((first, second)).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    chars.update("→←↑↓×·—！？，。：“”（）／")
    for source in (ROOT / "arrowgame").glob("*.py"):
        chars.update(source.read_text(encoding="utf-8"))
    for weight, style in ((450, "Regular"), (650, "Semibold")):
        font = TTFont(DEST / "NotoSansSC.ttf")
        selector = subset.Subsetter()
        selector.populate(unicodes=[ord(char) for char in chars])
        selector.subset(font)
        font = instantiateVariableFont(font, {"wght": weight}, inplace=True)
        family = "ArrowOrder Sans"
        names = {1: family, 2: style, 3: f"{family} {style} 1.0", 4: f"{family} {style}", 6: f"ArrowOrderSans-{style}", 16: family, 17: style}
        for name in font["name"].names:
            if name.nameID in names:
                name.string = names[name.nameID].encode(name.getEncoding())
        output = DEST / f"ArrowOrder-{style}.ttf"
        font.save(output)
        print(f"{output.name}: {output.stat().st_size:,} bytes; weight {weight}")


if __name__ == "__main__":
    main()
