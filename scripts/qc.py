#!/usr/bin/env python3
"""Quality control for one cut, before its preview goes to the user and again before the full render.

    python3 scripts/qc.py <listing-dir> [--hf output/hyperframes] [--no-frames]

Reads the cut's composition (output/hyperframes/index.html), listing.md, output/analysis/plan.json,
output/voice/timing.json and output/mix.json (or the mix.json next to a mix the editor names in the
composition folder), whichever exist, and checks:

 1. Thai spelling: words from SPELLING.md's "ผิด | ใช้" tables, tone marks and vowels in the wrong order or
    doubled, a split sara am, zero-width characters, Thai digits, ไม้ยมก without spaces. Every line of text
    is listed in the report so Claude reads them all (no Thai spell checker on this Mac).
 2. Facts: every number on screen, in a caption or in the voice-over (prices, areas, rooms, distances,
    phone numbers, codes) is found in listing.md; no ✗ item from listing.md's checklists is mentioned (an
    item that is ✗ in a checklist but stated in the listing's own text is a conflict to ask about).
 3. Text over the subject: renders each shot's middle frame with and without its text, takes the
    difference as the text's footprint, and checks it against the shot's focus point (plan.json); also
    text outside the safe zone of the composition's aspect.
 4. Crop: where each photo's focus lands in the frame, from the photo's inline crop in the composition;
    off the frame or out of the area the style keeps for the subject is a problem.
 5. Sound and timing: the mix's loudness and voice-over-music gap (mix.json); voice lines against shots,
    text and captions (captions never ahead of the voice, text lands within 0.25 s of its line, no cut
    inside a phrase, a quiet hook second and end card); text on screen at least 1.2 s (captions 0.8 s);
    total length; and HyperFrames' own check (layout, motion, contrast).

Writes <listing-dir>/output/qc/qc.md (Thai summary, every finding and every text line), qc.json and
qc_sheet.jpg (each shot's middle frame with its focus point marked). Exit code 1 when there is any error
(❌); warnings (⚠️) need a look but don't block.

Python 3.9, standard library only; needs node + the HyperFrames skill (frames), ffmpeg and ffprobe.
"""
import argparse
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HF = ["node", os.path.expanduser("~/.claude/skills/hyperframes/scripts/plugin-cli.mjs")]
SAFE = {  # text safe area per aspect: (x0, x1, y0, y1) and the narrower right edge from y_rail down
    (1080, 1920): dict(x0=120, x1=888, y0=380, y1=1248, rail_y=840, rail_x1=780, subj=(120, 960, 380, 1100)),
    (1920, 1080): dict(x0=96, x1=1824, y0=54, y1=1026, rail_y=None, rail_x1=None, subj=(96, 1824, 54, 1026)),
    (1080, 1080): dict(x0=60, x1=1020, y0=60, y1=1020, rail_y=None, rail_x1=None, subj=(60, 1020, 60, 1020)),
}
NUM = r"\d[\d,]*(?:\.\d+)?"


class Findings:
    def __init__(self):
        self.items = []

    def add(self, level, area, msg):
        self.items.append({"level": level, "area": area, "msg": msg})

    def err(self, area, msg):
        self.add("error", area, msg)

    def warn(self, area, msg):
        self.add("warn", area, msg)

    def ok(self, area, msg):
        self.add("ok", area, msg)


# ---------- composition parsing ----------

class Comp(html.parser.HTMLParser):
    """Clips (timed elements) with their text, and the first photo <img> inside each shot clip."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # (tag, attrs, clip_index or None)
        self.clips = []
        self.skip = 0
        self.root = {}
        self.css = ""
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script",):
            self.skip += 1
        if tag == "style":
            self.in_style = True
        if a.get("data-composition-id") and not self.root:
            self.root = a
        cls = (a.get("class") or "").split()
        idx = None
        if "clip" in cls and a.get("data-start") is not None:
            parent = self.current_clip()
            idx = len(self.clips)
            self.clips.append({"id": a.get("id"), "class": cls, "start": float(a["data-start"]),
                               "dur": float(a.get("data-duration") or 0), "text": [], "img": None,
                               "tag": tag, "parent": parent, "style": a.get("style") or ""})
        if tag == "img":
            c = self.current_clip()
            if c is not None and self.clips[c]["img"] is None and "mb" not in cls:
                self.clips[c]["img"] = {"src": a.get("src"), "style": a.get("style") or "", "id": a.get("id")}
        if tag == "video":
            c = idx if idx is not None else self.current_clip()
            if c is not None:
                self.clips[c]["video"] = a.get("src")
        if tag not in ("img", "br", "source", "meta", "link", "input"):
            self.stack.append((tag, a, idx))

    def current_clip(self):
        for _, _, i in reversed(self.stack):
            if i is not None:
                return i
        return None

    def handle_endtag(self, tag):
        if tag == "script":
            self.skip -= 1
        if tag == "style":
            self.in_style = False
        while self.stack:
            t, _, _ = self.stack.pop()
            if t == tag:
                break

    def handle_data(self, data):
        if self.in_style:
            self.css += data
            return
        if self.skip:
            return
        c = self.current_clip()
        if c is not None and data.strip():
            # attribute end-text blocks to the innermost clip
            self.clips[c]["text"].append(data.strip())


def load_comp(hdir):
    p = Comp()
    with open(os.path.join(hdir, "index.html"), encoding="utf-8") as f:
        p.feed(f.read())
    for c in p.clips:
        c["text"] = re.sub(r"\s+", " ", " ".join(c["text"])).strip()
    W = int(p.root.get("data-width", 1080))
    H = int(p.root.get("data-height", 1920))
    D = float(p.root.get("data-duration", 0))
    return p.clips, (W, H), D


def is_shot(c):
    return "shot" in c["class"] or c.get("img") is not None or c.get("video") is not None and c["tag"] == "div"


def shots_of(clips):
    """Shot clips (top-level photo/clip/card shots), with their number from the id (s1, s2...)."""
    out = []
    for c in clips:
        m = re.fullmatch(r"s(\d+)", c["id"] or "")
        if m and ("shot" in c["class"] or c["tag"] == "div"):
            c["n"] = int(m.group(1))
            out.append(c)
    # video shots: the clip is the <video>, its wrapper div has the id
    for c in clips:
        m = re.fullmatch(r"s(\d+)v", c["id"] or "")
        if m and not any(s["n"] == int(m.group(1)) for s in out):
            c["n"] = int(m.group(1))
            out.append(c)
    return sorted(out, key=lambda c: c["start"])


def text_clips(clips):
    out = []
    for c in clips:
        if not c["text"] or re.fullmatch(r"s\d+v?", c["id"] or "") or (c["id"] or "").startswith("logo"):
            continue
        out.append(c)
    return out


# ---------- 1. spelling ----------

def spelling_table():
    pairs = []
    with open(os.path.join(ROOT, "SPELLING.md"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", line)
            if m and m.group(1) not in ("ผิด", "---"):
                pairs.append((m.group(1), m.group(2)))
    return pairs


def check_spelling(texts, F):
    pairs = spelling_table()
    bad = 0
    for where, t in texts:
        for wrong, right in pairs:
            if wrong in t.replace(right, "\x00"):   # the wrong form, not as part of the right one
                F.err("spelling", "%s: \"%s\" สะกดว่า \"%s\" (ใช้ \"%s\" ตาม SPELLING.md)" % (where, t, wrong, right))
                bad += 1
        checks = [
            (r"[่-๋][ัิ-ื็]", "วรรณยุกต์อยู่ก่อนสระบน (ลำดับตัวอักษรผิด จะแสดงซ้อนผิด)"),
            (r"[่-๋]{2}", "วรรณยุกต์ซ้อนสองตัว"),
            (r"([ัิ-ฺ็-๎])\1", "สระหรือเครื่องหมายซ้ำ"),
            (r"ํา", "สระอำแยกเป็นนิคหิต+สระอา (ใช้ ำ ตัวเดียว)"),
            (r"[​‌‍﻿­]", "มีช่องว่างล่องหน (zero-width)"),
            (r"[๐-๙]", "ใช้เลขไทย (ใช้เลขอารบิก)"),
            (r"(^|\s)[ัิ-ฺ็-๎]", "สระหรือวรรณยุกต์ลอยต้นคำ"),
            (r"[เแโใไ](\s|$)", "สระหน้าไม่มีพยัญชนะตาม"),
            (r"[^\s]ๆ|ๆ[^\s]", "ไม้ยมกต้องเว้นวรรคก่อนและหลัง"),
            (r"\s{2,}", "ช่องว่างซ้อน"),
        ]
        for rx, msg in checks:
            if re.search(rx, t):
                F.err("spelling", "%s: \"%s\": %s" % (where, t, msg))
                bad += 1
    if not bad:
        F.ok("spelling", "ไม่พบคำในรายการคำผิดและไม่พบความผิดพลาดของตัวอักษร (%d บรรทัด) · Claude ต้องอ่านทุกบรรทัดในหัวข้อ \"ข้อความทั้งหมด\" อีกรอบ" % len(texts))


# ---------- 2. facts ----------

def listing_numbers(listing):
    raw = listing.replace(",", "")
    nums = set(re.findall(r"\d+(?:\.\d+)?", raw))
    digits = set(re.sub(r"\D", "", m) for m in re.findall(r"0\d{1,2}-?\d{3}-?\d{3,4}", listing))
    return nums, digits, raw


def num_ok(tok, unit, nums, raw):
    v = tok.replace(",", "")
    if v in nums:
        return True
    try:
        f = float(v)
    except ValueError:
        return False
    if unit.startswith("ล้าน"):
        whole = f * 1e6
        if ("%d" % whole) in nums:
            return True
    if unit.startswith("แสน"):
        if ("%d" % (f * 1e5)) in nums:
            return True
    if f == int(f) and ("%d" % f) in nums:
        return True
    return False


def check_facts(texts, listing, F):
    nums, phones, raw = listing_numbers(listing)
    bad = 0
    seen = set()
    for where, t in texts:
        for m in re.finditer(r"0\d{1,2}-\d{3}-\d{3,4}", t):
            d = re.sub(r"\D", "", m.group(0))
            if d not in phones:
                F.err("facts", "%s: เบอร์ %s ไม่ตรงกับเบอร์ในประกาศ" % (where, m.group(0)))
                bad += 1
        t2 = re.sub(r"0\d{1,2}-\d{3}-\d{3,4}", " ", t)
        for m in re.finditer(r"(%s)\s*([^\s\d]*)" % NUM, t2):
            tok, unit = m.group(1), m.group(2)
            key = (tok, unit[:4])
            if key in seen:
                continue
            seen.add(key)
            if not num_ok(tok, unit, nums, raw):
                F.err("facts", "%s: \"%s %s\" ไม่พบตัวเลขนี้ในประกาศ (listing.md)" % (where, tok, unit))
                bad += 1
    # ✗ items
    xs = []
    for line in listing.splitlines():
        m = re.match(r"-\s*(.+?)\s*✗[^:]*:\s*(.+)$", line.strip())
        if m:
            xs += [i.strip() for i in m.group(2).split(",") if i.strip()]
    desc = "\n".join(l for l in listing.splitlines() if "✗" not in l and "✓" not in l)
    desc_body = re.sub(r"^(เฟอร์นิเจอร์|สิ่งอำนวยความสะดวก)\s*$", "", desc, flags=re.M)
    for item in xs:
        names = [n.strip() for n in item.split("/") if len(n.strip()) >= 3]
        for where, t in texts:
            for n in names:
                if n in t:
                    lines_with = [l for l in desc_body.splitlines() if n in l and l.strip() != n]
                    if lines_with:
                        F.warn("facts", "%s: \"%s\" เป็น ✗ ในเช็กลิสต์ของประกาศ แต่ข้อความประกาศเขียนว่า \"%s\": ข้อมูลขัดกัน ถามผู้ใช้"
                               % (where, n, lines_with[0].strip()[:80]))
                    else:
                        F.err("facts", "%s: \"%s\" เป็นรายการ ✗ (ไม่มี) ในประกาศ" % (where, n))
                    bad += 1
    if not bad:
        F.ok("facts", "ตัวเลข ราคา เบอร์ และรายการในคลิปตรงกับประกาศทั้งหมด")


# ---------- 3 & 4. frames, focus, text footprint ----------

def px(style, key):
    m = re.search(r"(?:^|;)\s*%s\s*:\s*(-?[\d\.]+)px" % key, style)
    return float(m.group(1)) if m else None


def photo_focus(plan, src):
    stem = os.path.splitext(os.path.basename(src or ""))[0]
    m = re.search(r"photo-\d+", stem)
    if not (plan and m):
        return None
    for p in plan.get("photos", []):
        if m.group(0) in p["file"]:
            return p
    return None


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def gray(path, w, h):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=%d:%d,format=gray" % (w, h),
                        "-f", "rawvideo", "-"], capture_output=True)
    return r.stdout


def check_frames(hdir, clips, size, plan, outdir, F, no_frames):
    W, H = size
    safe = SAFE.get(size)
    shots = shots_of(clips)
    texts = text_clips(clips)
    rows = []
    for s in shots:
        mid = s["start"] + s["dur"] / 2
        img = s.get("img")
        p = photo_focus(plan, img["src"]) if img else None
        fx = fy = None
        if img and p:
            l, t, w, h = (px(img["style"], k) for k in ("left", "top", "width", "height"))
            if None not in (l, t, w, h):
                fx = l + p["focus"][0] * w
                fy = t + p["focus"][1] * h
        rows.append({"n": s["n"], "start": s["start"], "dur": s["dur"], "mid": mid, "src": img and img["src"],
                     "focus_xy": None if fx is None else [round(fx), round(fy)], "plan": p and p["file"]})
        if fx is None:
            if img and not p and re.search(r"photo-\d+", img["src"] or ""):
                F.warn("crop", "ช็อต %d: ไม่พบรูป %s ใน plan.json ตรวจครอปเองจาก qc_sheet.jpg" % (s["n"], img["src"]))
            continue
        x0, x1, y0, y1 = safe["subj"] if safe else (0, W, 0, H)
        if not (0 <= fx <= W and 0 <= fy <= H):
            F.err("crop", "ช็อต %d: จุดโฟกัสของ %s อยู่นอกเฟรม (%d, %d): ครอปผิดตำแหน่ง" % (s["n"], p["file"], fx, fy))
        elif not (x0 <= fx <= x1 and y0 <= fy <= y1):
            F.warn("crop", "ช็อต %d: จุดโฟกัสของ %s อยู่ที่ (%d, %d) นอกช่วงที่สไตล์เก็บจุดเด่น (x %d–%d, y %d–%d)"
                   % (s["n"], p["file"], fx, fy, x0, x1, y0, y1))
    if not any(f["area"] == "crop" for f in F.items):
        F.ok("crop", "จุดโฟกัสของทุกรูปอยู่ในเฟรมและในช่วงที่เก็บจุดเด่น")
    if no_frames:
        return rows
    times = [r["mid"] for r in rows]
    if not times:
        return rows
    with tempfile.TemporaryDirectory() as tmp:
        notext = os.path.join(tmp, "notext")
        shutil.copytree(hdir, notext, ignore=shutil.ignore_patterns(".hyperframes", "renders"))
        ids = [c["id"] for c in texts if c["id"]] + ["end-text"]
        hide = ",".join("#" + i for i in ids)
        with open(os.path.join(notext, "index.html"), encoding="utf-8") as f:
            h = f.read()
        h = h.replace("</head>", "<style>%s{visibility:hidden !important}</style></head>" % hide, 1)
        with open(os.path.join(notext, "index.html"), "w", encoding="utf-8") as f:
            f.write(h)
        at = ",".join("%.3f" % t for t in times)
        for d, name in ((hdir, "with"), (notext, "without")):
            r = run(HF + ["snapshot", d, "--at", at, "--no-end", "-o", os.path.join(tmp, name)])
            if r.returncode != 0:
                F.warn("overlap", "ถ่ายเฟรมไม่ได้ (%s): ตรวจข้อความทับภาพเองจาก preview" % r.stderr.strip()[-200:])
                return rows
        def frames(dirn):
            fs = sorted(f for f in os.listdir(dirn) if f.startswith("frame-") and f.endswith(".png"))
            return [os.path.join(dirn, f) for f in fs]
        fw, fn = frames(os.path.join(tmp, "with")), frames(os.path.join(tmp, "without"))
        sw, sh = W // 4, H // 4
        tiles = []
        for r, a, b in zip(rows, fw, fn):
            ga, gb = gray(a, sw, sh), gray(b, sw, sh)
            mask = [abs(x - y) > 40 for x, y in zip(ga, gb)]
            n = sum(mask)
            r["text_px"] = n
            if n and safe:
                ys = [i // sw for i, m in enumerate(mask) if m]
                xs = [i % sw for i, m in enumerate(mask) if m]
                bx0, bx1, by0, by1 = min(xs) * 4, max(xs) * 4, min(ys) * 4, max(ys) * 4
                r["text_box"] = [bx0, by0, bx1, by1]
                out = bx0 < safe["x0"] - 8 or bx1 > safe["x1"] + 8 or by0 < safe["y0"] - 8 or by1 > safe["y1"] + 8
                if safe["rail_y"] and by1 > safe["rail_y"]:
                    # only the part below the rail line must stay left of rail_x1
                    xs_low = [i % sw for i, m in enumerate(mask) if m and (i // sw) * 4 > safe["rail_y"]]
                    if xs_low and max(xs_low) * 4 > safe["rail_x1"] + 8:
                        out = True
                if out:
                    F.err("overlap", "ช็อต %d: ข้อความออกนอกเขตปลอดภัย (กรอบข้อความ x %d–%d, y %d–%d)" % (r["n"], bx0, bx1, by0, by1))
            if r.get("focus_xy") and n:
                cx, cy = r["focus_xy"][0] // 4, r["focus_xy"][1] // 4
                rad = max(W, H) // 4 // 22   # about 87 px on 1920
                cov = tot = 0
                for yy in range(max(0, cy - rad), min(sh, cy + rad)):
                    for xx in range(max(0, cx - rad), min(sw, cx + rad)):
                        tot += 1
                        cov += mask[yy * sw + xx]
                frac = cov / float(tot or 1)
                r["focus_covered"] = round(frac, 2)
                if frac > 0.25:
                    F.err("overlap", "ช็อต %d: ข้อความทับจุดเด่นของภาพ %d%% (จุดโฟกัส %s)" % (r["n"], frac * 100, r["focus_xy"]))
                elif frac > 0.08:
                    F.warn("overlap", "ช็อต %d: ข้อความแตะจุดเด่นของภาพ %d%%" % (r["n"], frac * 100))
            # sheet tile: the frame with text, focus marked
            tp = os.path.join(tmp, "tile_%02d.png" % len(tiles))
            vf = ["scale=%d:%d" % (W // 3, H // 3)]
            if r.get("focus_xy"):
                x, y = r["focus_xy"][0] // 3, r["focus_xy"][1] // 3
                vf.append("drawbox=x=%d:y=%d:w=18:h=18:color=red:t=fill" % (x - 9, y - 9))
                vf.append("drawbox=x=%d:y=%d:w=%d:h=%d:color=red@0.9:t=3" % (x - 29, y - 29, 58, 58))
            if r.get("text_box"):
                b = [v // 3 for v in r["text_box"]]
                vf.append("drawbox=x=%d:y=%d:w=%d:h=%d:color=0x2ecc71@0.9:t=2" % (b[0], b[1], b[2] - b[0], b[3] - b[1]))
            vf.append("drawtext=font='Sarabun\\:style=Bold':text='%d':x=10:y=8:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=6" % r["n"])
            run(["ffmpeg", "-v", "error", "-y", "-i", a, "-vf", ",".join(vf), tp])
            tiles.append(tp)
        if tiles:
            cols = min(5, len(tiles))
            rws = (len(tiles) + cols - 1) // cols
            run(["ffmpeg", "-v", "error", "-y", "-start_number", "0", "-i", os.path.join(tmp, "tile_%02d.png"),
                 "-frames:v", "1", "-vf", "tile=%dx%d:padding=8:margin=8:color=0x101010" % (cols, rws), "-q:v", "3",
                 os.path.join(outdir, "qc_sheet.jpg")])
    if not any(f["area"] == "overlap" and f["level"] != "ok" for f in F.items):
        F.ok("overlap", "ข้อความไม่ทับจุดเด่นของภาพและอยู่ในเขตปลอดภัยทุกช็อต")
    return rows


# ---------- 5. sound and timing ----------

def check_timing(clips, total, timing, mixj, F, hf_check):
    shots = shots_of(clips)
    texts = text_clips(clips)
    caps = [c for c in texts if "cap" in c["class"]]
    lines = [c for c in texts if "cap" not in c["class"]]
    n0 = len(F.items)
    if total and not (29 <= total <= 31):
        F.warn("timing", "คลิปยาว %.2f วิ (เป้า 30 วิ ±1 ถ้าบรีฟไม่ได้กำหนดอื่น)" % total)
    for c in lines:
        if c["dur"] < 1.2 and c["parent"] is None:
            F.warn("timing", "ข้อความ #%s \"%s\" อยู่บนจอ %.2f วิ (ต่ำกว่า 1.2 วิ)" % (c["id"], c["text"][:30], c["dur"]))
    for c in caps:
        if c["dur"] < 0.8:
            F.warn("timing", "ซับ #%s \"%s\" อยู่บนจอ %.2f วิ (ต่ำกว่า 0.8 วิ)" % (c["id"], c["text"][:30], c["dur"]))
    if timing:
        vlines = timing.get("lines", [])
        phrases = [(p["start"], p["end"], p["text"]) for l in vlines for p in l.get("phrases", [])]
        for c in caps:
            over = [l for l in vlines if l["start"] - 0.3 <= c["start"] <= l["end"]]
            if not over:
                F.warn("timing", "ซับ #%s \"%s\" ขึ้นที่ %.2f วิ ตอนที่ไม่มีเสียงพากย์" % (c["id"], c["text"][:30], c["start"]))
            elif c["start"] < over[0]["start"] - 0.1:
                F.err("timing", "ซับ #%s ขึ้นก่อนเสียง %.2f วิ" % (c["id"], over[0]["start"] - c["start"]))
        for l in vlines:
            near = [c for c in lines if abs(c["start"] - l["start"]) <= 0.25]
            inside = [c for c in lines if c["start"] <= l["start"] <= c["start"] + c["dur"]]
            if not near and not inside:
                F.warn("timing", "เสียงพากย์ช็อต %d (%.2f วิ) ไม่มีข้อความบนจอขึ้นภายใน 0.25 วิ" % (l["shot"], l["start"]))
        for s in shots[1:]:
            for ps, pe, pt in phrases:
                if ps + 0.05 < s["start"] < pe - 0.2:
                    F.err("timing", "ตัดเข้าช็อต %d ที่ %.2f วิ กลางวลีเสียงพากย์ \"%s\" (%.2f–%.2f)" % (s["n"], s["start"], pt, ps, pe))
        if vlines and min(l["start"] for l in vlines) < 1.0:
            F.warn("timing", "มีเสียงพากย์ในวินาทีแรก (hook ควรเงียบ)")
        if shots:
            end_start = shots[-1]["start"]
            late = [l for l in vlines if l["end"] > end_start + 0.3]
            if late and not any(l.get("may_overrun") for l in vlines):
                F.warn("timing", "เสียงพากย์ช็อต %d พูดทับ end card" % late[0]["shot"])
        for p in timing.get("problems", []):
            F.err("sound", "เสียงพากย์: " + p)
    else:
        F.warn("timing", "ไม่มี voice/timing.json: ตรวจการซิงก์เสียงกับข้อความไม่ได้")
    if mixj:
        i, tp = mixj.get("integrated_lufs"), mixj.get("true_peak_db")
        if i is None or abs(i + 14) > 1:
            F.err("sound", "ความดังรวม %s LUFS (เป้า −14 ±1)" % i)
        if tp is not None and tp > -0.7:
            F.err("sound", "peak %.1f dB เกิน −1 dBTP" % tp)
        for l in mixj.get("lines", []):
            if l.get("gap_db") is not None and l["gap_db"] < 10:
                F.err("sound", "ช็อต %d: เสียงพากย์ดังกว่าเพลงแค่ %.1f dB (ต้อง ≥ 10)" % (l["shot"], l["gap_db"]))
        for p in mixj.get("problems", []):
            if not any(p in f["msg"] for f in F.items):
                F.err("sound", "มิกซ์: " + p)
        if not [f for f in F.items[n0:] if f["area"] == "sound"]:
            F.ok("sound", "ความดัง %.1f LUFS, peak %.1f dB, เสียงพากย์เหนือเพลงทุกประโยค" % (i, tp or 0))
    else:
        F.warn("sound", "ไม่มี mix.json: ตรวจความดังและระดับเสียงพากย์กับเพลงไม่ได้")
    if hf_check:
        for k in ("layout", "motion", "craft", "runtime", "lint"):
            for f in (hf_check.get(k) or {}).get("findings", []):
                code = f.get("code")
                if code in ("font_face_local_only", "timeline_track_too_dense", "nested_structure_needs_subcomposition",
                            "container_overflow", "negative_z_index", "sparse_keyframes", "film_silent",
                            "duplicate_media_discovery_risk"):
                    continue
                if code == "panel_out_of_canvas" and "logo" in (f.get("selector") or ""):
                    continue
                lvl = "error" if f.get("severity") == "error" else "warn"
                F.add(lvl, "animation" if k in ("motion", "craft") else "layout",
                      "HyperFrames %s: %s %s" % (code, f.get("selector") or "", (f.get("message") or "")[:120]))
    if not [f for f in F.items[n0:] if f["area"] in ("timing", "animation")]:
        F.ok("timing", "ซับ ข้อความ และจุดตัดตรงกับเสียงพากย์ ข้อความอยู่บนจอนานพอ")


# ---------- report ----------

AREA_TH = {"spelling": "คำสะกด", "facts": "ข้อมูลตรงประกาศ", "overlap": "ข้อความทับภาพ / เขตปลอดภัย",
           "crop": "ตำแหน่งครอป", "sound": "เสียง", "timing": "จังหวะเสียงกับภาพ", "animation": "Animation",
           "layout": "เลย์เอาต์"}
ICON = {"error": "❌", "warn": "⚠️", "ok": "✅"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("listing")
    ap.add_argument("--hf", default="output/hyperframes")
    ap.add_argument("--mix", help="mix.json (default: output/mix.json if it exists)")
    ap.add_argument("--timing", help="voice/timing.json (default: output/voice/timing.json)")
    ap.add_argument("--no-frames", action="store_true")
    a = ap.parse_args()
    L = os.path.abspath(a.listing)
    hdir = os.path.join(L, a.hf)
    if not os.path.isfile(os.path.join(hdir, "index.html")):
        sys.exit("no %s/index.html" % hdir)
    out = os.path.join(L, "output", "qc")
    os.makedirs(out, exist_ok=True)
    clips, size, total = load_comp(hdir)

    def jload(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None
    plan = jload(os.path.join(L, "output", "analysis", "plan.json"))
    timing = jload(a.timing) if a.timing else jload(os.path.join(L, "output", "voice", "timing.json"))
    mixj = jload(a.mix) if a.mix else jload(os.path.join(L, "output", "mix.json"))
    with open(os.path.join(L, "listing.md"), encoding="utf-8") as f:
        listing = f.read()
    r = run(HF + ["check", hdir, "--json"])
    try:
        hf_check = json.loads(r.stdout)
    except ValueError:
        hf_check = None

    F = Findings()
    texts = [("#%s" % c["id"], c["text"]) for c in text_clips(clips)]
    if timing:
        texts += [("เสียงพากย์ช็อต %d" % l["shot"], l["text"]) for l in timing.get("lines", [])]
    check_spelling(texts, F)
    check_facts(texts, listing, F)
    rows = check_frames(hdir, clips, size, plan, out, F, a.no_frames)
    check_timing(clips, total, timing, mixj, F, hf_check)

    errs = [f for f in F.items if f["level"] == "error"]
    warns = [f for f in F.items if f["level"] == "warn"]
    md = ["# QC: %s" % os.path.basename(L), "",
          "คอมโพสิชัน `%s` · %dx%d · %.2f วิ · ❌ %d · ⚠️ %d" % (a.hf, size[0], size[1], total, len(errs), len(warns)), "",
          "| หัวข้อ | ผล |", "|---|---|"]
    for area in ("spelling", "facts", "overlap", "crop", "sound", "timing", "animation", "layout"):
        fs = [f for f in F.items if f["area"] == area]
        if not fs:
            continue
        lv = "error" if any(f["level"] == "error" for f in fs) else "warn" if any(f["level"] == "warn" for f in fs) else "ok"
        md.append("| %s | %s %s |" % (AREA_TH[area], ICON[lv], "ผ่าน" if lv == "ok" else "%d รายการ" % sum(f["level"] == lv for f in fs)))
    md += ["", "## รายการ", ""]
    for f in sorted(F.items, key=lambda f: {"error": 0, "warn": 1, "ok": 2}[f["level"]]):
        md.append("- %s **%s**: %s" % (ICON[f["level"]], AREA_TH[f["area"]], f["msg"]))
    md += ["", "## ข้อความทั้งหมด (Claude อ่านตรวจคำสะกดและความหมายทุกบรรทัด)", ""]
    for where, t in texts:
        md.append("- %s: %s" % (where, t))
    md += ["", "## ช็อต", "", "| ช็อต | เริ่ม | ยาว | รูป | จุดโฟกัสในเฟรม | ข้อความทับจุดเด่น |", "|---|---|---|---|---|---|"]
    for r_ in rows:
        md.append("| %d | %.2f | %.2f | %s | %s | %s |" % (r_["n"], r_["start"], r_["dur"], r_.get("plan") or r_.get("src") or "-",
                                                     r_.get("focus_xy") or "-", "%d%%" % (r_["focus_covered"] * 100) if "focus_covered" in r_ else "-"))
    md += ["", "ภาพรวม: `qc_sheet.jpg` (จุดแดง = จุดโฟกัส กรอบเขียว = ข้อความ)"]
    with open(os.path.join(out, "qc.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    with open(os.path.join(out, "qc.json"), "w", encoding="utf-8") as f:
        json.dump({"errors": len(errs), "warnings": len(warns), "findings": F.items, "shots": rows,
                   "texts": [{"where": w, "text": t} for w, t in texts]}, f, ensure_ascii=False, indent=2)
    for f in errs + warns:
        print("%s %s: %s" % (ICON[f["level"]], AREA_TH[f["area"]], f["msg"]))
    print("QC: %d errors, %d warnings -> %s" % (len(errs), len(warns), os.path.join(out, "qc.md")))
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
