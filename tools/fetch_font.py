"""Fetch the redistributable font and its license from Google Fonts."""
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "assets" / "fonts"
BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for remote, local in (("NotoSansSC%5Bwght%5D.ttf", "NotoSansSC.ttf"), ("OFL.txt", "OFL.txt")):
        with urlopen(BASE + remote, timeout=90) as response:
            data = response.read()
        if local.endswith(".ttf") and data[:4] not in (b"\x00\x01\x00\x00", b"OTTO"):
            raise ValueError("Font download was not a font file")
        (DEST / local).write_bytes(data)
        print(f"{local}: {len(data):,} bytes")


if __name__ == "__main__":
    main()
