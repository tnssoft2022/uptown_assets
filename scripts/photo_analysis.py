#!/usr/bin/env python3
"""Photo analysis for one listing: measure every photo, then draw the analysis sheet.

    python3 scripts/photo_analysis.py measure <listing-dir>
    python3 scripts/photo_analysis.py sheet   <listing-dir>

measure: reads every photo in <listing-dir>/assets/ (never changes it) and writes
  <listing-dir>/output/analysis/measure.json with what a script can measure:
  size, orientation, sharpness, brightness, blown highlights, crushed shadows, colour cast and
  near-duplicates. The brief agent reads it, looks at every photo itself and writes photos.json.

sheet: reads <listing-dir>/output/analysis/photos.json (written by the brief agent: room, scores,
  focus point, camera move, per photo) and
  - totals the scores (0-100) and ranks the photos, picks the Hero Shot (highest total among rooms
    that may open a video) unless the agent set "hero": true on one,
  - works out the 9:16 crop around the focus at the start and the end of the camera move,
  - checks each text band of the 1080x1920 frame (top, centre, lower, caption, and the layouts' head,
    mid, bottom) over that crop for busy detail and brightness, and recommends where the text goes
    (with "layout": "A"|"B"|"C" the layout's band is kept and only the advice changes),
  - writes the results to <listing-dir>/output/analysis/plan.json and draws
    <listing-dir>/output/analysis/photo_analysis.jpg (one tile per photo: crop boxes, focus,
    text band, scores, Hero star).

Python 3.9, standard library only; needs ffmpeg and ffprobe (Thai text via fontconfig "Sarabun").
"""
import json
import math
import os
import subprocess
import sys
import tempfile

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".tif", ".tiff", ".bmp"}
CLIP_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}

# Room labels (the brief agent's words) -> the six groups the user sorts by, Thai room name.
ROOMS = {
    "exterior": ("ภายนอก", "ภายนอก"),
    "drone": ("ภายนอก", "มุมสูง"),
    "entry": ("ภายใน", "ทางเข้า"),
    "living": ("ภายใน", "ห้องนั่งเล่น"),
    "dining": ("ภายใน", "ห้องทานข้าว"),
    "kitchen": ("ห้องครัว", "ห้องครัว"),
    "primary suite": ("ห้องนอน", "ห้องนอนใหญ่"),
    "bedroom": ("ห้องนอน", "ห้องนอน"),
    "bathroom": ("ห้องน้ำ", "ห้องน้ำ"),
    "outdoor": ("พื้นที่รอบบ้าน", "พื้นที่รอบบ้าน"),
    "view": ("พื้นที่รอบบ้าน", "วิว"),
    "amenity": ("พื้นที่รอบบ้าน", "ส่วนกลาง"),
    "neighborhood": ("พื้นที่รอบบ้าน", "ย่าน"),
    "floor plan": ("อื่น ๆ", "แปลน"),
    "other": ("อื่น ๆ", "อื่น ๆ"),
}
GROUP_ORDER = ["ภายนอก", "ภายใน", "ห้องนอน", "ห้องน้ำ", "ห้องครัว", "พื้นที่รอบบ้าน", "อื่น ๆ"]
# Rooms a video may open on (brief.md hook rules: never a bathroom, plan or "other").
HERO_ROOMS = {"exterior", "drone", "entry", "living", "dining", "kitchen", "primary suite",
              "bedroom", "outdoor", "view", "amenity"}

# Score weights (each score is 1-5); the total is scaled to 0-100.
WEIGHTS = {"sharp": 2.0, "light": 1.5, "angle": 1.5, "tidy": 1.0, "fit": 1.0, "appeal": 2.0}
SCORE_TH = {"sharp": "คม", "light": "แสง", "angle": "มุม", "tidy": "เรียบร้อย", "fit": "แนวตั้ง", "appeal": "ดึงดูด"}

# Text bands in the 1080x1920 frame (y from-to), x 120-780: the safe zone TikTok, Reels and Shorts all
# leave clear (STYLES.md "เขตปลอดภัย", the editor's safe zone).
BANDS = {
    "top": (400, 620),
    "centre": (700, 960),
    "lower": (960, 1130),
    "caption": (1150, 1248),
    # bands of the text layouts A/B/C (STYLES.md "การจัดวางข้อความ"), which use the wider zone y 80-1840
    "head": (90, 290),
    "mid": (860, 1060),
    "bottom": (1480, 1840),
}
BAND_TH = {"top": "บน", "centre": "กลาง", "lower": "ล่าง", "caption": "ซับ",
           "head": "หัวบน", "mid": "กลางจอ", "bottom": "ชิดล่าง"}
LAYOUT_BAND = {"A": "mid", "B": "bottom", "C": "bottom"}  # the main text band of each layout
BAND_X = (120, 780)
CALM_LIMIT = 18.0     # mean gradient (0-255 scale) at or below which a band is calm
BUSY_LIMIT = 28.0     # above this the band is too busy: text needs a dark band behind it
BRIGHT_LIMIT = 185.0  # mean luma above which white text needs a darker shadow or scrim

ANALYSIS_LONG = 640   # long side of the image the measurements run on


def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(1)


def probe_size(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation", "-of", "json", path],
        capture_output=True, text=True)
    if out.returncode != 0:
        return None
    s = json.loads(out.stdout).get("streams", [{}])[0]
    w, h = s.get("width"), s.get("height")
    rot = 0
    for sd in s.get("side_data_list", []) or []:
        rot = int(sd.get("rotation", 0) or 0)
    if abs(rot) in (90, 270):
        w, h = h, w
    return w, h


def load_pixels(path, w, h, fmt="gray"):
    """Return (aw, ah, bytes) of the photo scaled so its long side is ANALYSIS_LONG."""
    if w >= h:
        aw, ah = ANALYSIS_LONG, max(2, round(h * ANALYSIS_LONG / w))
    else:
        ah, aw = ANALYSIS_LONG, max(2, round(w * ANALYSIS_LONG / h))
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-vf",
         "scale=%d:%d:flags=area,format=%s" % (aw, ah, fmt), "-f", "rawvideo", "-"],
        capture_output=True)
    if out.returncode != 0:
        return None
    return aw, ah, out.stdout


def gradient_map(aw, ah, g):
    """Per-pixel |dx|+|dy| as a list (row-major), border = 0."""
    grad = [0] * (aw * ah)
    for y in range(1, ah - 1):
        row = y * aw
        for x in range(1, aw - 1):
            i = row + x
            grad[i] = abs(g[i + 1] - g[i - 1]) + abs(g[i + aw] - g[i - aw])
    return grad


def measure_photo(path):
    size = probe_size(path)
    if not size:
        return {"error": "ffprobe can't read it"}
    w, h = size
    px = load_pixels(path, w, h, "rgb24")
    if not px:
        return {"error": "ffmpeg can't decode it"}
    aw, ah, rgb = px
    n = aw * ah
    g = [0] * n
    rs = gs = bs = 0
    hi = lo = 0
    for i in range(n):
        r, gg, b = rgb[3 * i], rgb[3 * i + 1], rgb[3 * i + 2]
        y = (299 * r + 587 * gg + 114 * b) // 1000
        g[i] = y
        rs += r
        gs += gg
        bs += b
        if y >= 250:
            hi += 1
        elif y <= 8:
            lo += 1
    # Sharpness: variance of the Laplacian.
    total = total2 = cnt = 0
    for y in range(1, ah - 1):
        row = y * aw
        for x in range(1, aw - 1):
            i = row + x
            lap = 4 * g[i] - g[i - 1] - g[i + 1] - g[i - aw] - g[i + aw]
            total += lap
            total2 += lap * lap
            cnt += 1
    mean = total / cnt
    sharp = total2 / cnt - mean * mean
    # dHash (9x8 gray) for near-duplicates.
    small = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-vf",
         "scale=9:8:flags=area,format=gray", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    bits = 0
    for yy in range(8):
        for xx in range(8):
            bits = (bits << 1) | (1 if small[yy * 9 + xx] > small[yy * 9 + xx + 1] else 0)
    rm, gm, bm = rs / n, gs / n, bs / n
    return {
        "width": w,
        "height": h,
        "orientation": "vertical" if h > w else ("square" if h == w else "horizontal"),
        "short_side": min(w, h),
        "low_res": min(w, h) < 1080,
        "sharpness": round(sharp, 1),
        "brightness": round(sum(g) / n, 1),
        "highlights_pct": round(100.0 * hi / n, 2),
        "shadows_pct": round(100.0 * lo / n, 2),
        "cast": {"r_minus_g": round(rm - gm, 1), "b_minus_g": round(bm - gm, 1)},
        "dhash": "%016x" % bits,
    }


def listing_paths(listing):
    listing = os.path.abspath(listing)
    assets = os.path.join(listing, "assets")
    if not os.path.isdir(assets):
        die("no assets/ folder in " + listing)
    out = os.path.join(listing, "output", "analysis")
    os.makedirs(out, exist_ok=True)
    return listing, assets, out


def cmd_measure(listing):
    listing, assets, out = listing_paths(listing)
    photos, clips, other = [], [], []
    for name in sorted(os.listdir(assets)):
        if name.startswith("."):
            continue
        ext = os.path.splitext(name)[1].lower()
        rel = "assets/" + name
        if ext in PHOTO_EXT:
            m = measure_photo(os.path.join(assets, name))
            m["file"] = rel
            photos.append(m)
            print("measured " + rel, file=sys.stderr)
        elif ext in CLIP_EXT:
            clips.append(rel)
        else:
            other.append(rel)
    ok = [p for p in photos if "error" not in p]
    sharp_sorted = sorted(p["sharpness"] for p in ok)
    median = sharp_sorted[len(sharp_sorted) // 2] if sharp_sorted else 0
    for p in ok:
        notes = []
        if p["low_res"]:
            notes.append("low resolution (short side %d px)" % p["short_side"])
        if median and p["sharpness"] < 0.35 * median:
            notes.append("much softer than the other photos")
        if p["brightness"] < 85:
            notes.append("dark")
        if p["highlights_pct"] > 8:
            notes.append("blown highlights %.0f%%" % p["highlights_pct"])
        if p["shadows_pct"] > 8:
            notes.append("crushed shadows %.0f%%" % p["shadows_pct"])
        c = p["cast"]
        if abs(c["r_minus_g"]) > 18 or abs(c["b_minus_g"]) > 18:
            warm = c["r_minus_g"] - c["b_minus_g"]
            notes.append("colour cast (%s)" % ("warm/yellow" if warm > 0 else "cool/blue"))
        p["sharpness_vs_median"] = round(p["sharpness"] / median, 2) if median else None
        p["notes"] = notes
    # Near-duplicates: dHash Hamming distance <= 10 of 64.
    for i, a in enumerate(ok):
        a.setdefault("near_duplicates", [])
        for b in ok[i + 1:]:
            b.setdefault("near_duplicates", [])
            d = bin(int(a["dhash"], 16) ^ int(b["dhash"], 16)).count("1")
            if d <= 10:
                a["near_duplicates"].append(b["file"])
                b["near_duplicates"].append(a["file"])
    result = {"listing": os.path.basename(listing), "median_sharpness": median,
              "photos": photos, "clips": clips, "other_files": other}
    path = os.path.join(out, "measure.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("%-22s %10s %-10s %7s %6s %5s  %s" % ("file", "size", "orient", "sharp", "bright", "hi%", "notes"))
    for p in photos:
        if "error" in p:
            print("%-22s ERROR %s" % (p["file"], p["error"]))
            continue
        print("%-22s %10s %-10s %7.2f %6.0f %5.1f  %s" % (
            p["file"], "%dx%d" % (p["width"], p["height"]), p["orientation"],
            p["sharpness_vs_median"] or 0, p["brightness"], p["highlights_pct"],
            "; ".join(p["notes"] + (["near-duplicate of " + ", ".join(p["near_duplicates"])]
                                    if p["near_duplicates"] else []))))
    if clips:
        print("clips (not measured; look at their frames): " + ", ".join(clips))
    print("wrote " + path)


# ---------- sheet ----------

def crop_rect(w, h, fx, fy, zoom=1.0):
    """9:16 crop of a w x h photo centred on focus (fractions), shrunk by zoom (>1 = tighter)."""
    cw = min(w, h * 9.0 / 16.0)
    ch = cw * 16.0 / 9.0
    cw, ch = cw / zoom, ch / zoom
    cx = min(max(fx * w, cw / 2), w - cw / 2)
    cy = min(max(fy * h, ch / 2), h - ch / 2)
    return [cx - cw / 2, cy - ch / 2, cw, ch]


def move_crops(w, h, focus, move):
    fx, fy = focus
    kind = (move or {}).get("type", "none")
    pct = float((move or {}).get("pct", 0) or 0)
    z = 1.0 + pct / 100.0
    if kind == "push-in":
        return crop_rect(w, h, fx, fy), crop_in(crop_rect(w, h, fx, fy), fx * w, fy * h, z)
    if kind == "pull-out":
        return crop_in(crop_rect(w, h, fx, fy), fx * w, fy * h, z), crop_rect(w, h, fx, fy)
    if kind == "pan":
        # The editor scales the photo up by the pan % so the frame can travel; draw it as a crop
        # that is pct% tighter and slides across the full crop.
        base = crop_rect(w, h, fx, fy)
        c = crop_in(base, base[0] + base[2] / 2, base[1] + base[3] / 2, z)
        shift = base[2] - c[2]
        d = (move or {}).get("dir", "right")
        s = [base[0], c[1], c[2], c[3]]
        e = [base[0] + shift, c[1], c[2], c[3]]
        if d in ("up", "down"):
            shift = base[3] - c[3]
            s = [c[0], base[1], c[2], c[3]]
            e = [c[0], base[1] + shift, c[2], c[3]]
        if d in ("left", "up"):
            s, e = e, s
        return s, e
    r = crop_rect(w, h, fx, fy)
    return r, r


def crop_in(rect, ox, oy, z):
    """Scale a crop rect by 1/z around (ox, oy), like transform-origin on the focus."""
    x, y, cw, ch = rect
    nw, nh = cw / z, ch / z
    nx = ox - (ox - x) / z
    ny = oy - (oy - y) / z
    return [nx, ny, nw, nh]


def band_rect(crop, band):
    """A text band of the 1080x1920 frame mapped into photo pixels for a given crop."""
    x, y, cw, ch = crop
    y0, y1 = BANDS[band]
    return [x + cw * BAND_X[0] / 1080.0, y + ch * y0 / 1920.0,
            cw * (BAND_X[1] - BAND_X[0]) / 1080.0, ch * (y1 - y0) / 1920.0]


def region_stats(aw, ah, g, grad, scale, rect):
    x, y, rw, rh = [v * scale for v in rect]
    x0, y0 = max(1, int(x)), max(1, int(y))
    x1, y1 = min(aw - 1, int(x + rw)), min(ah - 1, int(y + rh))
    if x1 <= x0 or y1 <= y0:
        return 0.0, 0.0
    gs = ls = n = 0
    for yy in range(y0, y1):
        row = yy * aw
        for xx in range(x0, x1):
            gs += grad[row + xx]
            ls += g[row + xx]
            n += 1
    return gs / n, ls / n


def total_score(scores):
    s = sum(WEIGHTS[k] * float(scores.get(k, 0)) for k in WEIGHTS)
    return round(100.0 * s / (5.0 * sum(WEIGHTS.values())))


def esc_path(p):
    return p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_tile(src, w, h, item, tile_path, tmp, idx):
    T = 480       # photo area is T x T
    CAP = 190     # caption strip
    s = min(T / w, T / h)
    dw, dh = int(round(w * s)) // 2 * 2, int(round(h * s)) // 2 * 2
    ox, oy = (T - dw) // 2, (T - dh) // 2

    def box(r, color, t):
        x, y, bw, bh = r
        return "drawbox=x=%d:y=%d:w=%d:h=%d:color=%s:t=%s" % (
            ox + x * s, oy + y * s, max(2, bw * s), max(2, bh * s), color, t)

    used = item.get("use", True)
    f = ["scale=%d:%d" % (dw, dh), "format=rgb24"]
    if not used:
        f.append("eq=brightness=-0.25:saturation=0.3")
    f.append("pad=%d:%d:%d:%d:color=0x1b1b1b" % (T, T + CAP, ox, oy))
    if used:
        tb = item["text_band"]
        f.append(box(band_rect(item["crop_start"], tb), "0x2ecc71@0.45", "fill"))
        f.append(box(item["crop_start"], "white@0.95", 3))
        if item["crop_end"] != item["crop_start"]:
            f.append(box(item["crop_end"], "0xffd23f@0.95", 3))
        fx, fy = item["focus"]
        f.append("drawbox=x=%d:y=%d:w=12:h=12:color=0xff3b3b:t=fill" % (ox + fx * w * s - 6, oy + fy * h * s - 6))
    if item.get("hero"):
        f.append("drawbox=x=0:y=0:w=%d:h=%d:color=0xc9a063:t=8" % (T, T))
    lines = item["caption_lines"]
    txt = os.path.join(tmp, "cap_%02d.txt" % idx)
    with open(txt, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    f.append("drawtext=font=Sarabun:textfile='%s':x=14:y=%d:fontsize=21:fontcolor=white:line_spacing=7:expansion=none"
             % (esc_path(txt), T + 10))
    if item.get("hero"):
        f.append("drawtext=font='Sarabun\\:style=Bold':text='HERO':x=%d:y=14:fontsize=30:"
                 "fontcolor=0xc9a063:box=1:boxcolor=black@0.6:boxborderw=8" % (T - 110))
    f.append("drawtext=font='Sarabun\\:style=Bold':text='%d':x=12:y=10:fontsize=30:fontcolor=white:"
             "box=1:boxcolor=black@0.6:boxborderw=6" % item["rank"])
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-frames:v", "1",
                        "-vf", ",".join(f), tile_path], capture_output=True, text=True)
    if r.returncode != 0:
        die("ffmpeg tile for %s: %s" % (src, r.stderr.strip()))


def legend_tile(tile_path, tmp, groups):
    txt = os.path.join(tmp, "legend.txt")
    lines = ["วิธีอ่าน",
             "กรอบขาว = เฟรม 9:16 ตอนเริ่ม",
             "กรอบเหลือง = เฟรมตอนจบการเคลื่อนกล้อง",
             "แถบเขียว = ที่วางข้อความ",
             "จุดแดง = จุดโฟกัส",
             "กรอบทอง HERO = ภาพเปิดคลิป",
             "ภาพมืด = ไม่ใช้",
             "* = ย้ายข้อความจากตำแหน่งของสไตล์",
             "",
             "จำนวนภาพตามหมวด"]
    lines += ["%s %d" % (g, n) for g, n in groups]
    with open(txt, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    vf = ("drawtext=font=Sarabun:textfile='%s':x=24:y=24:fontsize=24:fontcolor=white:line_spacing=10:expansion=none"
          % esc_path(txt))
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x262626:s=480x670",
                        "-frames:v", "1", "-vf", vf, tile_path], capture_output=True, text=True)
    if r.returncode != 0:
        die("ffmpeg legend: " + r.stderr.strip())


def describe_move(m):
    kind = (m or {}).get("type", "none")
    if kind == "none":
        return "นิ่ง"
    if kind == "ai":
        return "AI motion"
    pct = (m or {}).get("pct", 0)
    if kind == "pan":
        return "แพน %s %s%%" % ({"left": "ซ้าย", "right": "ขวา", "up": "ขึ้น", "down": "ลง"}.get(m.get("dir"), m.get("dir")), pct)
    return {"push-in": "ซูมเข้า", "pull-out": "ซูมออก"}.get(kind, kind) + " %s%%" % pct


def cmd_sheet(listing):
    listing, assets, out = listing_paths(listing)
    src = os.path.join(out, "photos.json")
    if not os.path.isfile(src):
        die("write %s first (the brief agent's analysis)" % src)
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    layout = data.get("layout")
    if layout is not None and layout not in LAYOUT_BAND:
        die("layout must be one of " + ", ".join(LAYOUT_BAND))
    style_band = LAYOUT_BAND[layout] if layout else data.get("text_band", "lower")
    if style_band not in BANDS:
        die("text_band must be one of " + ", ".join(BANDS))
    items = data.get("photos", [])
    if not items:
        die("photos.json has no photos")
    for it in items:
        for k in WEIGHTS:
            v = it.get("scores", {}).get(k)
            if not isinstance(v, (int, float)) or not 1 <= v <= 5:
                die("%s: score %s must be 1-5" % (it.get("file"), k))
        if it.get("room") not in ROOMS:
            die("%s: room must be one of %s" % (it.get("file"), ", ".join(ROOMS)))
        it["total"] = total_score(it["scores"])
        it.setdefault("use", True)
        it.setdefault("focus", [0.5, 0.5])
    # Hero: the agent's pick, else the best usable photo of a room that may open the video.
    picked = [it for it in items if it.get("hero")]
    if len(picked) > 1:
        die("more than one photo has \"hero\": true")
    if picked:
        hero = picked[0]
        hero["hero_by"] = "agent"
    else:
        cands = [it for it in items if it["use"] and it["room"] in HERO_ROOMS]
        if not cands:
            die("no usable photo of a room that may open the video")
        hero = max(cands, key=lambda it: (it["total"], it["scores"]["appeal"], it["scores"]["sharp"]))
        hero["hero"] = True
        hero["hero_by"] = "score"
    ranked = sorted(items, key=lambda it: (not it["use"], -it["total"], it["file"]))
    for i, it in enumerate(ranked, 1):
        it["rank"] = i
    with tempfile.TemporaryDirectory() as tmp:
        tiles = []
        for idx, it in enumerate(ranked):
            path = os.path.join(listing, it["file"])
            if not os.path.isfile(path):
                die("missing " + it["file"])
            w, h = probe_size(path)
            it["size"] = [w, h]
            cs, ce = move_crops(w, h, it["focus"], it.get("move"))
            it["crop_start"] = [round(v, 1) for v in cs]
            it["crop_end"] = [round(v, 1) for v in ce]
            aw, ah, g = load_pixels(path, w, h, "gray")
            grad = gradient_map(aw, ah, g)
            scale = aw / float(w)
            zones = {}
            for b in BANDS:
                g1, l1 = region_stats(aw, ah, g, grad, scale, band_rect(cs, b))
                g2, l2 = region_stats(aw, ah, g, grad, scale, band_rect(ce, b))
                busy, bright = max(g1, g2), max(l1, l2)
                zones[b] = {"busy": round(busy, 1), "brightness": round(bright),
                            "level": "calm" if busy <= CALM_LIMIT else ("fair" if busy <= BUSY_LIMIT else "busy"),
                            "ok": busy <= BUSY_LIMIT,
                            "needs_shadow": bright > BRIGHT_LIMIT}
            it["text_zones"] = zones
            if layout or zones[style_band]["ok"]:
                it["text_band"] = style_band   # a layout fixes the text place
            else:
                calm = [b for b in ("lower", "centre", "top") if zones[b]["ok"]]
                it["text_band"] = calm[0] if calm else min(("lower", "centre", "top"), key=lambda b: zones[b]["busy"])
            z = zones[it["text_band"]]
            advice = {"calm": "พื้นเรียบ", "fair": "พอใช้ ใส่เงา", "busy": "พื้นรก ใส่แถบเข้ม"}[z["level"]]
            if z["needs_shadow"] and z["level"] == "calm":
                advice = "พื้นสว่าง ใส่เงา"
            it["text_advice"] = advice
            grp, name = ROOMS[it["room"]]
            sc = it["scores"]
            line2 = " ".join("%s%d" % (SCORE_TH[k], sc[k]) for k in ("sharp", "light", "angle", "tidy", "fit", "appeal"))
            if it["use"]:
                line3 = "%s · ข้อความ%s: %s" % (describe_move(it.get("move")), BAND_TH[it["text_band"]], advice)
                if it["text_band"] != style_band:
                    line3 += " *"
            else:
                line3 = "ไม่ใช้: " + (it.get("reason") or "")
            it["caption_lines"] = [
                "%s · %s   %d/100" % (os.path.basename(it["file"]), name, it["total"]),
                line2,
                line3[:46],
                (it.get("reason") or "")[:46] if it["use"] else "",
            ]
            tp = os.path.join(tmp, "tile_%02d.png" % idx)
            render_tile(path, w, h, it, tp, tmp, idx)
            tiles.append(tp)
        counts = {}
        for it in items:
            counts[ROOMS[it["room"]][0]] = counts.get(ROOMS[it["room"]][0], 0) + 1
        groups = [(g, counts.get(g, 0)) for g in GROUP_ORDER if g != "อื่น ๆ" or counts.get(g)]
        lp = os.path.join(tmp, "tile_%02d.png" % len(tiles))
        legend_tile(lp, tmp, groups)
        tiles.append(lp)
        cols = 4 if len(tiles) > 6 else 3 if len(tiles) > 2 else len(tiles)
        rows = int(math.ceil(len(tiles) / float(cols)))
        sheet = os.path.join(out, "photo_analysis.jpg")
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-start_number", "0", "-i",
                            os.path.join(tmp, "tile_%02d.png"), "-frames:v", "1", "-vf",
                            "tile=%dx%d:padding=10:margin=10:color=0x101010" % (cols, rows),
                            "-q:v", "3", sheet], capture_output=True, text=True)
        if r.returncode != 0:
            die("ffmpeg sheet: " + r.stderr.strip())
    for it in items:
        it.pop("caption_lines", None)
    plan = {"listing": os.path.basename(listing), "style": data.get("style"), "layout": layout, "style_text_band": style_band,
            "hero": hero["file"], "hero_by": hero["hero_by"],
            "groups": {g: [it["file"] for it in ranked if ROOMS[it["room"]][0] == g] for g in GROUP_ORDER},
            "photos": ranked}
    with open(os.path.join(out, "plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print("%-4s %-22s %-14s %5s %-10s %-8s %s" % ("rank", "file", "room", "score", "move", "text", "advice"))
    for it in ranked:
        print("%-4d %-22s %-14s %5d %-10s %-8s %s%s" % (
            it["rank"], it["file"], it["room"], it["total"], (it.get("move") or {}).get("type", "none"),
            it["text_band"] if it["use"] else "-", it["text_advice"] if it["use"] else "not used",
            "  HERO (%s)" % it["hero_by"] if it.get("hero") else ""))
    print("wrote %s and %s" % (os.path.join(out, "plan.json"), sheet))


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("measure", "sheet"):
        print(__doc__)
        sys.exit(2)
    (cmd_measure if sys.argv[1] == "measure" else cmd_sheet)(sys.argv[2])


if __name__ == "__main__":
    main()
