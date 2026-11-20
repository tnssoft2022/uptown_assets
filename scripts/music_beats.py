#!/usr/bin/env python3
"""Find the beat grid of a music track, so the editor can put cuts on the beat.

Writes <track>.beats.json next to each track: {"bpm", "first_beat", "beats": [seconds...]}, times measured
from the start of the file. The brand tracks are steady-tempo AI music, so one tempo and one phase fit the
whole track: the tempo and phase are those of the beat grid (60-180 BPM) that lands on the most onsets.

Usage: python3 scripts/music_beats.py [--out-dir DIR] [track.mp3 ...]   (default: every brand/music/*.mp3)
A listing's own music (in its assets/, which is never written to) needs --out-dir, e.g. the scratch folder.
Python 3.9, standard library; needs ffmpeg.
"""
import array
import glob
import json
import math
import os
import subprocess
import sys

SR = 22050
HOP = 512                     # ~23 ms frames
FPS = SR / HOP


def onset_envelope(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         stdout=subprocess.PIPE, check=True).stdout
    x = array.array("h", raw)
    env, prev, last = [], 0.0, 0
    for i in range(0, len(x) - HOP, HOP):
        e = 0.0
        for j in range(i, i + HOP):           # pre-emphasis: favours drums and plucks over pads
            d = x[j] - last
            last = x[j]
            e += d * d
        v = math.log1p(e / HOP)
        env.append(max(0.0, v - prev))
        prev = v
    m = sum(env) / len(env)
    return [max(0.0, v - m) for v in env]


def comb(env, bpm, off):
    """Mean onset strength on a beat grid (bpm, first beat at `off` frames)."""
    period = FPS * 60 / bpm
    s, n, t = 0.0, 0, off
    while t < len(env) - 1:
        i = int(t)
        f = t - i
        s += env[i] * (1 - f) + env[i + 1] * f
        n += 1
        t += period
    return s / max(n, 1)


def fit(env):
    """Tempo and phase of the grid that lands on the most onsets.

    A direct comb fit over 60-180 BPM (0.05 steps) rather than autocorrelation: a grid that is a fraction
    of a BPM off drifts a beat out of phase over a 40 s track, and the comb score punishes that drift.
    Between a tempo and its double the slower one wins only if it scores higher.
    """
    best = (-1.0, 0.0, 0.0)
    for b in range(1200, 3601):               # 60.00-180.00 BPM in 0.05 steps
        bpm = b / 20
        period = FPS * 60 / bpm
        for k in range(32):
            off = period * k / 32
            sc = comb(env, bpm, off)
            if sc > best[0]:
                best = (sc, bpm, off)
    # fine phase
    sc, bpm, off = best
    period = FPS * 60 / bpm
    for k in range(-16, 17):
        o = off + period * k / 512
        if o >= 0:
            v = comb(env, bpm, o)
            if v > sc:
                sc, off = v, o
    return bpm, off / FPS


def main(paths, out_dir=None):
    for p in paths:
        env = onset_envelope(p)
        dur = len(env) / FPS
        bpm, first = fit(env)
        step = 60 / bpm
        beats = []
        t = first
        while t < dur:
            beats.append(round(t, 3))
            t += step
        base = os.path.splitext(os.path.basename(p))[0] + ".beats.json"
        out = os.path.join(out_dir, base) if out_dir else os.path.splitext(p)[0] + ".beats.json"
        with open(out, "w") as f:
            json.dump({"track": os.path.basename(p), "bpm": round(bpm, 2), "first_beat": round(first, 3),
                       "beats": beats}, f, indent=1)
        print(f"{os.path.basename(p)}: {bpm:.2f} BPM, first beat {first:.3f} s, {len(beats)} beats -> {out}")


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    args = sys.argv[1:]
    out_dir = None
    if "--out-dir" in args:
        i = args.index("--out-dir")
        out_dir = args[i + 1]
        del args[i:i + 2]
        os.makedirs(out_dir, exist_ok=True)
    main(args or sorted(glob.glob(os.path.join(root, "brand", "music", "*.mp3"))), out_dir)
