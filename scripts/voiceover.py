#!/usr/bin/env python3
"""Thai voice-over for one cut: speak each approved line, fit it to its shot, place it on the timeline.

    python3 scripts/voiceover.py <script.json> <output-dir>

<script.json> (the director writes it from the approved voice-over table):
    {"total": 30.0, "engine": "kanya", "voice": "Kanya", "pace": 1.0, "lead": 0.2,
     "lines": [{"shot": 2, "start": 3.0, "duration": 2.6, "text": "พูลวิลล่า ชะอำ ที่ดิน 1 ไร่"}, ...]}
  start/duration: the shot's place on the video timeline (seconds). A line starts `lead` s after its shot
  starts (or at "at" if the line gives one) and must end 0.2 s before the shot ends ("may_overrun": true
  lets the last line run on).

Writes to <output-dir>:
  voiceover.wav     44.1 kHz mono, exactly `total` s, every line at its time, speech at -16 LUFS
  voice/shotNN.wav  each line alone (trimmed, paced, levelled)
  voice/timing.json every line's real start/end, its speed, the spoken text, the spelling changes made
                    for the engine, and phrase timings (one per space-separated phrase) for the captions

The approved text is never reworded. Only how it is spelled for the engine changes (numbers, units,
abbreviations: see SPOKEN below), and every change is listed in timing.json and printed.

Engines: "kanya" (macOS `say`, offline, free). To connect a Thai text-to-speech API later, add a function
to ENGINES that writes the text's speech to a WAV path (see `speak_kanya`), with its key read from an
environment variable, never from this file.

Python 3.9, standard library only; needs ffmpeg, ffprobe and (for kanya) macOS `say`.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

SR = 44100
TARGET_LUFS = -16.0
MAX_SPEEDUP = 1.15     # on top of the pace, to fit a long line into its shot
END_GAP = 0.2          # a line ends at least this long before its shot ends
PHRASE_PAUSE_MS = 0    # extra pause at each space (Kanya already pauses there)

# ---------- spoken form (Thai) ----------

DIGITS = ["ศูนย์", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]
PLACES = ["", "สิบ", "ร้อย", "พัน", "หมื่น", "แสน"]


def thai_int(n):
    """Integer to Thai words (ล้าน groups recursively)."""
    if n == 0:
        return DIGITS[0]
    if n >= 1000000:
        hi, lo = divmod(n, 1000000)
        return thai_int(hi) + "ล้าน" + (thai_int(lo) if lo else "")
    out = ""
    s = str(n)
    L = len(s)
    for i, ch in enumerate(s):
        d = int(ch)
        pos = L - i - 1
        if d == 0:
            continue
        if pos == 1 and d == 1:
            out += "สิบ"
        elif pos == 1 and d == 2:
            out += "ยี่สิบ"
        elif pos == 0 and d == 1 and L > 1:
            out += "เอ็ด"
        else:
            out += DIGITS[d] + PLACES[pos]
    return out


def thai_number(tok):
    """'5.5' -> ห้าจุดห้า, '3,800,000' -> สามล้านแปดแสน, '0645144624' (phone) -> digit by digit."""
    raw = tok.replace(",", "")
    if len(raw) > 1 and raw.startswith("0") and "." not in raw:   # phones, codes: digit by digit
        return "".join(DIGITS[int(c)] for c in raw)
    if "." in raw:
        a, b = raw.split(".", 1)
        return thai_int(int(a or 0)) + "จุด" + "".join(DIGITS[int(c)] for c in b)
    return thai_int(int(raw))


# Abbreviations and Latin names the engine misreads -> how to say them. Order matters (longer first).
SPOKEN = [
    ("ตร.ม.", "ตารางเมตร"), ("ตร.ว.", "ตารางวา"), ("ตร.กม.", "ตารางกิโลเมตร"),
    ("กม.", "กิโลเมตร"), ("ชม.", "ชั่วโมง"), ("รปภ.", "รอปอภอ"), ("กทม.", "กรุงเทพมหานคร"),
    ("BTS", "บีทีเอส"), ("MRT", "เอ็มอาร์ที"), ("ARL", "แอร์พอร์ตเรลลิงก์"), ("Airport Rail Link", "แอร์พอร์ตเรลลิงก์"),
    ("Wi-Fi", "ไวไฟ"), ("WiFi", "ไวไฟ"), ("CCTV", "ซีซีทีวี"), ("%", " เปอร์เซ็นต์"),
]


UNITS = ("ล้าน", "แสน", "หมื่น", "บาท", "ตารางเมตร", "ตารางวา", "ตารางกิโลเมตร", "เมตร", "กิโลเมตร", "ไร่",
         "งาน", "ห้อง", "นาที", "ชั่วโมง", "เปอร์เซ็นต์", "คัน", "ชั้น", "ตร.", "กม.", "ม.")
NUM_RE = r"\d[\d,]*(?:\.\d+)?"


def phrases_of(text):
    """Caption phrases: the line's space-separated parts, with a number kept together with its unit
    ("5.5 ล้านบาท" is one phrase), as the engine says them without a pause."""
    toks = text.split()
    out = []
    for t in toks:
        if out and re.fullmatch(NUM_RE, out[-1].split()[-1]) and t.startswith(UNITS):
            out[-1] = out[-1] + " " + t
        else:
            out.append(t)
    return out


def spoken_form(text):
    """Return (spoken text, [(from, to), ...]) without changing any word's meaning."""
    changes = []
    out = text
    for a, b in SPOKEN:
        if a in out:
            out = out.replace(a, b)
            changes.append((a, b))
    # "ม." right after a number is metres ("200 ม."); elsewhere it may be หมู่/มหาวิทยาลัย: leave it.
    def metre(m):
        changes.append((m.group(0), m.group(1) + " เมตร"))
        return m.group(1) + " เมตร"   # the number itself is spelled out below
    out = re.sub(r"(\d[\d,\.]*)\s*ม\.(?![ก-๙])", metre, out)
    # "50:50" -> ห้าสิบ ห้าสิบ
    def ratio(m):
        r = thai_number(m.group(1)) + " " + thai_number(m.group(2))
        changes.append((m.group(0), r))
        return r
    out = re.sub(r"(\d+):(\d+)", ratio, out)
    # phone numbers 0XX-XXX-XXXX
    def phone(m):
        r = thai_number(m.group(0).replace("-", ""))
        changes.append((m.group(0), r))
        return r
    out = re.sub(r"0\d{1,2}-\d{3}-\d{3,4}", phone, out)
    # every other number
    def num(m):
        r = thai_number(m.group(0))
        changes.append((m.group(0), r))
        return r + "\x01"
    out = re.sub(NUM_RE, num, out)
    # say a number and its unit in one breath: no pause between "ห้าจุดห้า" and "ล้านบาท"
    out = re.sub(r"\x01\s+(?=(%s))" % "|".join(re.escape(u) for u in UNITS), "", out)
    out = out.replace("\x01", "")
    return out, changes


# ---------- engines ----------

def speak_kanya(text, wav, voice, tmp):
    aiff = os.path.join(tmp, "say.aiff")
    if PHRASE_PAUSE_MS:
        text = re.sub(r"\s+", " [[slnc %d]] " % PHRASE_PAUSE_MS, text.strip())
    r = subprocess.run(["say", "-v", voice or "Kanya", "-o", aiff, text], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("say failed: " + r.stderr.strip())
    run(["ffmpeg", "-v", "error", "-y", "-i", aiff, "-ac", "1", "-ar", str(SR), wav])


ENGINES = {"kanya": speak_kanya}

# ---------- audio helpers ----------


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(cmd[:4]) + "...: " + r.stderr.strip()[-600:])
    return r


def duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path])
    return float(r.stdout.strip())


def silences(path, noise="-38dB", d=0.07):
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-af", "silencedetect=noise=%s:d=%s" % (noise, d),
                        "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d\.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d\.]+)", r.stderr)]
    return list(zip(starts, ends))


def loudness(path):
    r = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d\.]+) LUFS", r.stderr)
    p = re.findall(r"Peak:\s+(-?[\d\.]+) dBFS", r.stderr)
    return (float(i[-1]) if i else None, float(p[-1]) if p else None)


def phrase_times(wav, phrases, offset):
    """Start/end of each space-separated phrase, from the pauses the engine leaves at the spaces;
    falls back to splitting the line by character count when the pauses don't match."""
    total = duration(wav)
    gaps = [(s, e) for s, e in silences(wav) if 0.05 < s < total - 0.05]
    n = len(phrases)
    if n == 1:
        return [[round(offset, 2), round(offset + total, 2)]]
    if len(gaps) >= n - 1:
        gaps = sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)[:n - 1]
        gaps.sort()
        bounds = [0.0]
        for s, e in gaps:
            bounds += [s, e]
        bounds.append(total)
        return [[round(offset + bounds[2 * i], 2), round(offset + bounds[2 * i + 1], 2)] for i in range(n)]
    weights = [max(1, len(p)) for p in phrases]
    tot = float(sum(weights))
    out, t = [], 0.0
    for w in weights:
        d = total * w / tot
        out.append([round(offset + t, 2), round(offset + t + d, 2)])
        t += d
    return out


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    with open(sys.argv[1], encoding="utf-8") as f:
        sc = json.load(f)
    outdir = os.path.abspath(sys.argv[2])
    total = float(sc["total"])
    engine = sc.get("engine", "kanya")
    if engine not in ENGINES:
        sys.exit("engine must be one of: " + ", ".join(ENGINES))
    speak = ENGINES[engine]
    voice = sc.get("voice", "Kanya")
    pace = float(sc.get("pace", 1.0))
    lead = float(sc.get("lead", 0.2))
    os.makedirs(os.path.join(outdir, "voice"), exist_ok=True)
    report = {"engine": engine, "voice": voice, "pace": pace, "total": total, "lines": [], "problems": []}
    placed = []
    with tempfile.TemporaryDirectory() as tmp:
        for ln in sc["lines"]:
            text = ln["text"].strip()
            if not text:
                continue
            shot = int(ln["shot"])
            spoken, changes = spoken_form(text)
            raw = os.path.join(tmp, "raw_%02d.wav" % shot)
            speak(spoken, raw, voice, tmp)
            # trim leading/trailing silence
            trimmed = os.path.join(tmp, "trim_%02d.wav" % shot)
            run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                 "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,"
                 "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse",
                 trimmed])
            natural = duration(trimmed)
            at = float(ln.get("at", float(ln["start"]) + lead))
            room = float(ln["start"]) + float(ln["duration"]) - END_GAP - at
            speed = pace
            if not ln.get("may_overrun") and natural / pace > room:
                speed = min(natural / max(room, 0.1), pace * MAX_SPEEDUP)
            # tempo, a gentle voice EQ (cut rumble, a little presence), level to TARGET_LUFS
            shaped = os.path.join(tmp, "shaped_%02d.wav" % shot)
            run(["ffmpeg", "-v", "error", "-y", "-i", trimmed, "-af",
                 "atempo=%.4f,highpass=f=80,equalizer=f=3000:t=q:w=1.2:g=2,"
                 "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=80" % speed, "-ar", str(SR), shaped])
            final = os.path.join(outdir, "voice", "shot%02d.wav" % shot)
            run(["ffmpeg", "-v", "error", "-y", "-i", shaped, "-af",
                 "loudnorm=I=%s:TP=-2:LRA=7" % TARGET_LUFS, "-ar", str(SR), "-ac", "1", final])
            d = duration(final)
            end = at + d
            limit = float(ln["start"]) + float(ln["duration"]) - END_GAP
            over = round(end - limit, 2) if (end > limit + 0.01 and not ln.get("may_overrun")) else 0
            if over:
                report["problems"].append("shot %d: runs %.2f s past its shot even at %.2fx; shorten the line"
                                          % (shot, over, speed))
            phrases = phrases_of(text)
            entry = {"shot": shot, "start": round(at, 2), "end": round(end, 2), "speed": round(speed, 3),
                     "text": text, "spoken": spoken, "changes": [{"from": a, "to": b} for a, b in changes],
                     "phrases": [{"text": p, "start": t[0], "end": t[1]}
                                 for p, t in zip(phrases, phrase_times(final, phrases, at))],
                     "overrun": over}
            report["lines"].append(entry)
            placed.append((at, final))
        # overlap check
        ordered = sorted(report["lines"], key=lambda e: e["start"])
        for a, b in zip(ordered, ordered[1:]):
            if a["end"] > b["start"]:
                report["problems"].append("shots %d and %d overlap by %.2f s" % (a["shot"], b["shot"], a["end"] - b["start"]))
        # assemble
        out = os.path.join(outdir, "voiceover.wav")
        if placed:
            cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", "%.3f" % total,
                   "-i", "anullsrc=r=%d:cl=mono" % SR]
            parts = []
            for i, (at, path) in enumerate(placed, 1):
                cmd += ["-i", path]
                ms = int(round(at * 1000))
                parts.append("[%d]adelay=%d|%d[d%d]" % (i, ms, ms, i))
            mix = "".join("[d%d]" % i for i in range(1, len(placed) + 1))
            fc = ";".join(parts) + ";[0]%samix=inputs=%d:duration=first:normalize=0,atrim=0:%.3f[o]" % (
                mix, len(placed) + 1, total)
            run(cmd + ["-filter_complex", fc, "-map", "[o]", "-ar", str(SR), "-ac", "1", out])
        else:
            run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-t", "%.3f" % total,
                 "-i", "anullsrc=r=%d:cl=mono" % SR, out])
    lufs, peak = loudness(out)
    report["voiceover"] = {"path": out, "duration": round(duration(out), 3), "speech_lufs_each_line": TARGET_LUFS,
                           "integrated_lufs": lufs, "peak_dbfs": peak}
    with open(os.path.join(outdir, "voice", "timing.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("%-5s %-6s %-6s %-6s %s" % ("shot", "start", "end", "speed", "text"))
    for e in report["lines"]:
        print("%-5d %-6.2f %-6.2f %-6.3f %s" % (e["shot"], e["start"], e["end"], e["speed"], e["text"]))
        for c in e["changes"]:
            print("      spelled for the engine: %s -> %s" % (c["from"], c["to"]))
    for p in report["problems"]:
        print("PROBLEM: " + p)
    print("wrote %s (%.2f s, peak %s dBFS) and voice/timing.json" % (out, report["voiceover"]["duration"], peak))


if __name__ == "__main__":
    main()
