#!/usr/bin/env python3
"""Render a cut with HyperFrames and finish it with ffmpeg: a preview first, the full file after approval.

    python3 scripts/render_cut.py preview <hyperframes-dir> --mix <mix.wav> --out <name>_preview.mp4
    python3 scripts/render_cut.py final   <hyperframes-dir> --mix <mix.wav> --out <name>.mp4
    python3 scripts/render_cut.py check   <file.mp4> [--aspect 9:16|16:9|1:1] [--duration <s>]

preview: HyperFrames draft render (about half the time), scaled to half size, a small "PREVIEW" tag in
  the corner, with the real mix, so timing, text, voice and music can be judged. Not for posting.
final: HyperFrames render at CRF 18, muxed with the mix (AAC 192 kb/s, 44.1 kHz), +faststart. The picture
  is re-encoded only if HyperFrames' stream isn't H.264 High, yuv420p, 30 fps. Then `check` runs on it.
check: the delivery spec for Facebook Reels, TikTok, YouTube Shorts (9:16) and feed posts (16:9, 1:1):
  MP4, H.264 (High), yuv420p, 30 fps, the aspect's size (1080x1920, 1920x1080, 1080x1080), AAC 44.1 kHz,
  moov atom at the front (+faststart), audio as long as the picture, no more than 60 s for 9:16.
  Prints every failure and exits 1 if any.

The aspect is read from the composition's data-width/data-height (and from the file for `check`).
Python 3.9, standard library only; needs node, ffmpeg and ffprobe, and the HyperFrames skill.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

HF = ["node", os.path.expanduser("~/.claude/skills/hyperframes/scripts/plugin-cli.mjs")]
SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}


def run(cmd, quiet=True):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("failed: %s\n%s" % (" ".join(cmd[:6]), (r.stderr or r.stdout).strip()[-1500:]))
    return r


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    return json.loads(r.stdout)


def aspect_of(w, h):
    for k, (sw, sh) in SIZES.items():
        if (w, h) == (sw, sh):
            return k
    return "%dx%d" % (w, h)


def comp_size(hdir):
    with open(os.path.join(hdir, "index.html"), encoding="utf-8") as f:
        html = f.read()
    w = re.search(r'data-width="(\d+)"', html)
    h = re.search(r'data-height="(\d+)"', html)
    if not (w and h):
        sys.exit("index.html has no data-width/data-height on its root")
    return int(w.group(1)), int(h.group(1))


def moov_first(path):
    """True if the moov atom comes before mdat (faststart)."""
    with open(path, "rb") as f:
        pos = 0
        size = os.path.getsize(path)
        while pos < size:
            f.seek(pos)
            hdr = f.read(16)
            if len(hdr) < 8:
                return False
            n = int.from_bytes(hdr[:4], "big")
            kind = hdr[4:8]
            if n == 1:
                n = int.from_bytes(hdr[8:16], "big")
            if kind == b"moov":
                return True
            if kind == b"mdat":
                return False
            if n < 8:
                return False
            pos += n
    return False


def check(path, aspect=None, duration=None):
    d = probe(path)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    fails = []
    if not v:
        return ["no video stream"]
    w, h = v["width"], v["height"]
    asp = aspect or aspect_of(w, h)
    if asp not in SIZES:
        fails.append("size %dx%d is none of 1080x1920, 1920x1080, 1080x1080" % (w, h))
    elif (w, h) != SIZES[asp]:
        fails.append("size %dx%d, %s needs %dx%d" % ((w, h, asp) + SIZES[asp]))
    if v["codec_name"] != "h264":
        fails.append("video codec %s, needs h264" % v["codec_name"])
    if v.get("profile") not in ("High", "Main"):
        fails.append("H.264 profile %s, needs High" % v.get("profile"))
    if v.get("pix_fmt") != "yuv420p":
        fails.append("pixel format %s, needs yuv420p" % v.get("pix_fmt"))
    if v.get("r_frame_rate") not in ("30/1", "30000/1000"):
        fails.append("frame rate %s, needs 30" % v.get("r_frame_rate"))
    if not a:
        fails.append("no audio stream")
    else:
        if a["codec_name"] != "aac":
            fails.append("audio codec %s, needs aac" % a["codec_name"])
        if a.get("sample_rate") != "44100":
            fails.append("audio %s Hz, needs 44100" % a.get("sample_rate"))
        vd, ad = float(v.get("duration", 0)), float(a.get("duration", 0))
        if abs(vd - ad) > 0.1:
            fails.append("audio %.2f s, picture %.2f s" % (ad, vd))
    fd = float(d["format"]["duration"])
    if duration and abs(fd - duration) > 0.1:
        fails.append("length %.2f s, the cut is %.2f s" % (fd, duration))
    if asp == "9:16" and fd > 60.5:
        fails.append("9:16 cut is %.1f s, over 60 s" % fd)
    if "mp4" not in d["format"]["format_name"]:
        fails.append("container %s, needs mp4" % d["format"]["format_name"])
    if not moov_first(path):
        fails.append("moov atom after mdat: mux with -movflags +faststart")
    print("%s: %dx%d (%s) %s %s %s %s fps, audio %s %s Hz, %.2f s, %.1f MB" % (
        path, w, h, asp, v["codec_name"], v.get("profile"), v.get("pix_fmt"), v.get("r_frame_rate"),
        a and a["codec_name"], a and a.get("sample_rate"), fd, int(d["format"]["size"]) / 1e6))
    for f in fails:
        print("FAIL: " + f)
    if not fails:
        print("OK: MP4 H.264 for Reels, TikTok, Shorts" if asp == "9:16" else "OK: MP4 H.264 %s" % asp)
    return fails


def render(hdir, out, quality):
    cmd = HF + ["render", hdir, "--skill=hyperframes", "--quiet", "-o", out]
    cmd += ["--quality", "draft"] if quality == "draft" else ["--crf", "18"]
    run(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["preview", "final", "check"])
    ap.add_argument("path")
    ap.add_argument("--mix")
    ap.add_argument("--out")
    ap.add_argument("--aspect", choices=list(SIZES))
    ap.add_argument("--duration", type=float)
    a = ap.parse_args()
    if a.mode == "check":
        sys.exit(1 if check(a.path, a.aspect, a.duration) else 0)
    if not (a.mix and a.out):
        sys.exit("--mix and --out are needed")
    hdir = os.path.abspath(a.path)
    w, h = comp_size(hdir)
    asp = aspect_of(w, h)
    if asp not in SIZES:
        sys.exit("composition is %dx%d; use 1080x1920, 1920x1080 or 1080x1080" % (w, h))
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pic = os.path.join(tmp, "picture.mp4")
        if a.mode == "preview":
            render(hdir, pic, "draft")
            tag = ("drawtext=font='Sarabun\\:style=Bold':text='PREVIEW':fontsize=%d:fontcolor=white@0.85:"
                   "box=1:boxcolor=0xc62a3a@0.85:boxborderw=8:x=w-tw-%d:y=%d"
                   % (max(18, h // 60), w // 40, h // 40))
            run(["ffmpeg", "-v", "error", "-y", "-i", pic, "-i", a.mix, "-map", "0:v", "-map", "1:a",
                 "-vf", "scale=%d:%d:flags=bicubic,%s" % (w // 2, h // 2, tag),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-r", "30",
                 "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out])
            d = probe(out)
            print("preview: %s (%dx%d, %.2f s, %.1f MB) - for review only, not for posting"
                  % (out, w // 2, h // 2, float(d["format"]["duration"]), int(d["format"]["size"]) / 1e6))
            return
        render(hdir, pic, "final")
        v = next(s for s in probe(pic)["streams"] if s["codec_type"] == "video")
        ok = (v["codec_name"] == "h264" and v.get("profile") == "High" and v.get("pix_fmt") == "yuv420p"
              and v.get("r_frame_rate") == "30/1")
        vcodec = ["-c:v", "copy"] if ok else ["-c:v", "libx264", "-profile:v", "high", "-preset", "slow",
                                              "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30"]
        run(["ffmpeg", "-v", "error", "-y", "-i", pic, "-i", a.mix, "-map", "0:v", "-map", "1:a"] + vcodec +
            ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out])
    fails = check(out, asp, a.duration)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
