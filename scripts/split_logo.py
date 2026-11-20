#!/usr/bin/env python3
"""Split brand/logo.png into layers for the animated logo (brand/logo_layers/).

The logo is a ring around a white disc holding the U mark and two lines of wordmark. The parts never
overlap, so they are cut by position (no AI, no redrawing): ring = the annulus outside the white disc,
mark / uptown / assets = bands of rows inside the disc. Inside the disc the white is turned into
transparency ("colour to alpha", exact for anti-aliased edges over white), so each part can move on its
own; the animation puts a white disc back underneath.

Usage: python3 scripts/split_logo.py   (Python 3.9, standard library; needs ffmpeg)
"""
import math
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "brand", "logo.png")
OUT = os.path.join(ROOT, "brand", "logo_layers")
W = H = 848
CX = CY = 424
DISC_R = 404          # white disc ends ~407, ring is ~407-424
BANDS = {             # rows (y0, y1) of each part inside the disc
    "mark": (60, 546),
    "uptown": (546, 652),
    "assets": (652, 800),
}


def ffmpeg(args, data=None):
    return subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, input=data,
                          stdout=subprocess.PIPE, check=True).stdout


def save(name, buf):
    ffmpeg(["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-i", "-",
            os.path.join(OUT, name + ".png")], bytes(buf))


def main():
    if not os.path.exists(SRC):
        sys.exit("brand/logo.png not found")
    os.makedirs(OUT, exist_ok=True)
    src = ffmpeg(["-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgba", "-"])
    ring = bytearray(W * H * 4)
    parts = {k: bytearray(W * H * 4) for k in BANDS}
    for y in range(H):
        part = next((k for k, (a, b) in BANDS.items() if a <= y < b), None)
        for x in range(W):
            i = (y * W + x) * 4
            r, g, b, a = src[i:i + 4]
            if a == 0:
                continue
            if math.hypot(x - CX, y - CY) > DISC_R:
                ring[i:i + 4] = bytes((r, g, b, a))
                continue
            if part is None:
                continue
            # colour to alpha against white
            al = max(255 - r, 255 - g, 255 - b) / 255.0
            if al <= 0.02:
                continue
            un = lambda c: max(0, min(255, round((c - (1 - al) * 255) / al)))
            parts[part][i:i + 4] = bytes((un(r), un(g), un(b), round(al * a)))
    save("ring", ring)
    for k, buf in parts.items():
        save(k, buf)
    print("wrote", ", ".join(["ring"] + list(BANDS)), "to", OUT)


if __name__ == "__main__":
    main()
