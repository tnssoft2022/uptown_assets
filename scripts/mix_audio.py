#!/usr/bin/env python3
"""Mix a cut's sound: voice-over on top, music ducked under it, loud enough for Reels, TikTok and Shorts.

    python3 scripts/mix_audio.py --duration 30 --out <dir>/mix.wav
        [--voice <dir>/voiceover.wav] [--timing <dir>/voice/timing.json]
        [--music brand/music/standard.mp3] [--music-start 0] [--fade 1.0]

- Music: from --music-start, trimmed to the cut, faded out over the last --fade seconds, its bed set to
  about -19 LUFS, and pushed down (sidechain) wherever the voice speaks, so the voice sits 12-18 dB over it.
- Voice: as voiceover.py levelled it (-16 LUFS per line), with a gentle de-esser; never ducked.
- Whole mix: two-pass loudnorm to -14 LUFS integrated, -1 dBTP true peak (what the platforms play at), so
  the app neither turns it down hard nor up into distortion.
- Check, printed and written next to the mix as mix.json: integrated loudness, true peak, duration, and for
  each voice line (from --timing) the voice's loudness against the ducked music under it; the voice must be
  at least 10 dB above the music (reported as a problem if not).

Python 3.9, standard library only; needs ffmpeg.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

SR = 44100
TARGET_I, TARGET_TP, TARGET_LRA = -14.0, -1.0, 11.0
BED_LUFS = -19.0
MIN_GAP_DB = 10.0   # voice over the ducked music, per line; 12-18 dB is the aim


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("ffmpeg failed: " + r.stderr.strip()[-800:])
    return r


def ebur(path, start=None, end=None):
    cmd = ["ffmpeg", "-nostats"]
    if start is not None:
        cmd += ["-ss", "%.3f" % start, "-to", "%.3f" % end]
    cmd += ["-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d\.]+|-inf) LUFS", r.stderr)
    p = re.findall(r"Peak:\s+(-?[\d\.]+|-inf) dBFS", r.stderr)
    f = lambda v: None if not v or v[-1] == "-inf" else float(v[-1])
    return f(i), f(p)


def loudnorm_two_pass(src, dst, i, tp, lra, channels, dur=None):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", src, "-af",
                        "loudnorm=I=%s:TP=%s:LRA=%s:print_format=json" % (i, tp, lra), "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
    af = ("loudnorm=I=%s:TP=%s:LRA=%s:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:"
          "offset=%s:linear=true" % (i, tp, lra, m["input_i"], m["input_tp"], m["input_lra"],
                                     m["input_thresh"], m["target_offset"]))
    if dur:   # loudnorm resamples internally and can shorten the file slightly: pad/trim to the cut
        af += ",apad=whole_dur=%.3f,atrim=0:%.3f" % (dur, dur)
    run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-ar", str(SR), "-ac", str(channels), dst])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice")
    ap.add_argument("--timing")
    ap.add_argument("--music")
    ap.add_argument("--music-start", type=float, default=0.0)
    ap.add_argument("--fade", type=float, default=1.0)
    a = ap.parse_args()
    D = a.duration
    report = {"duration": D, "problems": []}
    with tempfile.TemporaryDirectory() as tmp:
        music = voice = None
        if a.music:
            raw = os.path.join(tmp, "m_raw.wav")
            run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % a.music_start, "-i", a.music, "-t", "%.3f" % D,
                 "-af", "apad=whole_dur=%.3f,afade=t=out:st=%.3f:d=%.3f" % (D, max(0, D - a.fade), a.fade),
                 "-ar", str(SR), "-ac", "2", raw])
            music = os.path.join(tmp, "m_bed.wav")
            loudnorm_two_pass(raw, music, BED_LUFS if a.voice else TARGET_I, -2, TARGET_LRA, 2, D)
        if a.voice:
            voice = os.path.join(tmp, "v.wav")
            run(["ffmpeg", "-v", "error", "-y", "-i", a.voice, "-af",
                 "apad=whole_dur=%.3f,atrim=0:%.3f,deesser=i=0.4" % (D, D), "-ar", str(SR), "-ac", "2", voice])
        pre = os.path.join(tmp, "pre.wav")
        ducked = os.path.join(tmp, "ducked.wav")
        if music and voice:
            # the voice keys the compressor on the music: about 10-12 dB down while it speaks
            run(["ffmpeg", "-v", "error", "-y", "-i", music, "-i", voice, "-filter_complex",
                 "[1]asplit=2[key][v];[0][key]sidechaincompress=threshold=0.03:ratio=5:attack=15:release=350:"
                 "makeup=1[md];[md]asplit=2[mo][mm];[mm][v]amix=inputs=2:duration=first:normalize=0[o]",
                 "-map", "[o]", "-ar", str(SR), pre, "-map", "[mo]", "-ar", str(SR), ducked])
        elif music:
            run(["ffmpeg", "-v", "error", "-y", "-i", music, "-c", "copy", pre])
        elif voice:
            run(["ffmpeg", "-v", "error", "-y", "-i", voice, "-c", "copy", pre])
        else:
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", "%.3f" % D, "-i",
                 "anullsrc=r=%d:cl=stereo" % SR, pre])
        out = os.path.abspath(a.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if music or voice:
            loudnorm_two_pass(pre, out, TARGET_I, TARGET_TP, TARGET_LRA, 2, D)
        else:
            run(["ffmpeg", "-v", "error", "-y", "-i", pre, out])
        # voice over music, per line
        if music and voice and a.timing:
            with open(a.timing, encoding="utf-8") as f:
                lines = json.load(f).get("lines", [])
            report["lines"] = []
            for ln in lines:
                s, e = ln["start"], ln["end"]
                if e - s < 0.45:
                    continue
                vi, _ = ebur(voice, s, e)
                mi, _ = ebur(ducked, s, e)
                gap = None if vi is None or mi is None else round(vi - mi, 1)
                report["lines"].append({"shot": ln["shot"], "voice_lufs": vi, "music_lufs": mi, "gap_db": gap})
                if gap is not None and gap < MIN_GAP_DB:
                    report["problems"].append("shot %d: voice only %.1f dB over the music" % (ln["shot"], gap))
    i, p = ebur(out)
    dur = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]).stdout)
    report.update({"path": out, "integrated_lufs": i, "true_peak_db": p, "real_duration": round(dur, 3)})
    if i is not None and abs(i - TARGET_I) > 1.0:
        report["problems"].append("integrated %.1f LUFS, target %.0f" % (i, TARGET_I))
    if p is not None and p > TARGET_TP + 0.3:
        report["problems"].append("peak %.1f dB over %.0f dBTP" % (p, TARGET_TP))
    if abs(dur - D) > 0.05:
        report["problems"].append("length %.3f s, cut is %.3f s" % (dur, D))
    with open(os.path.splitext(out)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("mix: %s  %.2f s  %s LUFS  peak %s dB" % (out, dur, i, p))
    for ln in report.get("lines", []):
        print("  shot %-3d voice %6s  music %6s  gap %s dB" % (ln["shot"], ln["voice_lufs"], ln["music_lufs"], ln["gap_db"]))
    for pr in report["problems"]:
        print("PROBLEM: " + pr)


if __name__ == "__main__":
    main()
