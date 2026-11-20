# Transitions: blocks for the editor

How shots change in every cut. The style's "ทรานสิชัน" row in `STYLES.md` says which transition goes
where; this file says how to build them. The helpers are in `brand/transition_fx/transition_fx.js`, the
beat grids in `brand/music/<track>.beats.json` (from `scripts/music_beats.py`).

Rules that hold for every transition:
- Nothing bends, warps or breaks the photo: transitions slide, scale evenly, fade, or lay light over it. No
  glitch, swirl, ripple, burn, lens, 3D flip or shatter, whatever the registry offers.
- No transition longer than 0.6 s (0.9 s for a light leak, which plays over a crossfade).
- Whip pans on at most one in three cuts, and only between rooms; inside a room keep the style's plain cut.
- Motion blur comes from a pre-made blurred copy (`.mb`), never a CSS or SVG filter on the photo.
- A light leak peaks at 70% and is gone within 0.9 s, at most 3 per video.

## Setup

Copy `brand/transition_fx/transition_fx.js` into the cut as `assets/transition_fx.js` and load it after GSAP.
Every shot gets an inner `.mv` wrapper; the Ken Burns tween stays on the `<img>` as before:

```css
.mv { position: absolute; left: 0; top: 0; width: 100%; height: 100%; transform-origin: 50% 50%; }
.mb { opacity: 0; }   /* the whip's blurred copy: same inline crop as the photo */
.flash { position: absolute; inset: 0;
  background: radial-gradient(ellipse 80% 60% at 50% 45%, #fffaf0 0%, #fff1dc 60%, #ffe6c4 100%); }
.wash { position: absolute; inset: 0; background: #f4ede2; }   /* cream; #4a141c (wine) on dark cuts */
.leak { position: absolute; inset: 0; mix-blend-mode: screen; overflow: hidden; }
.lk { position: absolute; inset: -20%; }
.lk1 { background: radial-gradient(ellipse 45% 80% at 15% 55%, rgba(255,241,197,0.9), rgba(255,160,80,0.5) 40%, transparent 70%); }
.lk2 { background: radial-gradient(ellipse 50% 70% at 80% 30%, rgba(255,110,70,0.55), transparent 70%); }
.lk3 { background: linear-gradient(104deg, transparent 25%, rgba(255,200,120,0.35) 42%, rgba(255,247,205,0.6) 51%, transparent 75%); }
```

```html
<div id="s2" class="clip shot" data-start="2.304" data-duration="2.725" data-track-index="2" style="z-index:2">
  <div class="mv">
    <img id="s2i" src="assets/photo-02.jpg" style="(the crop)" alt="">
    <img class="mb" src="assets/photo-02-mb.jpg" style="(the same crop)" alt="">  <!-- only for a whip -->
  </div>
</div>
<!-- overlays, above the shots and below the logo and text -->
<div id="fl1" class="clip flash" data-start="6.529" data-duration="0.3" data-track-index="6" style="z-index:30"></div>
<div id="wa1" class="clip wash" data-start="8.179" data-duration="0.6" data-track-index="6" style="z-index:30"></div>
<div id="lk1" class="clip leak" data-start="9.829" data-duration="0.9" data-track-index="7" style="z-index:31">
  <div class="lk lk1"></div><div class="lk lk2"></div><div class="lk lk3"></div></div>
```

Whip blur copy: `ffmpeg -i photo-02.jpg -vf "avgblur=sizeX=60:sizeY=1" photo-02-mb.jpg`, made from the same
source file as the photo (it goes in `assets/` beside it).

## Timeline

`t` is where the transition starts; the "cut" is its midpoint (overlaps) or its peak (flash, wash).

| Helper | Use | Clips |
|---|---|---|
| `tr.crossfade(tl, "#s1", "#s2", t, d)` | the style's plain crossfade | overlap d |
| `tr.zoom(tl, "#s1", "#s2", t, 0.35)` | มาตรฐาน: hook → shot 2 | overlap 0.35 |
| `tr.whip(tl, "#s2", "#s3", t, dir, 0.3)` | มาตรฐาน / เดินชมห้อง: between rooms; dir 1 enters from the right, -1 from the left | overlap 0.3; both shots need `.mb` |
| `tr.flash(tl, "#fl1", cut, 0.3)` | เดินชมห้อง: room change (warm flash, replaces the plain white flash) | hard cut, flash clip cut ± 0.15 |
| `tr.fadeThrough(tl, "#wa1", cut, 0.6)` | เรียบหรู: room change | hard cut, wash clip cut ± 0.3 |
| `tr.leak(tl, "#lk1", cut, 0.9)` | เรียบหรู: over 2–3 crossfades | leak clip cut ± 0.45 |
| `tr.push(tl, "#f1", "#f2", t, 0.35, 960)` | การ์ดข้อมูล: photos inside the frame | overlap 0.35, frame `overflow: hidden` |
| `tr.lift(tl, "#f2", "#f3", t, 0.4, 90)` | การ์ดข้อมูล: section change | overlap 0.4 |

Whip direction: alternate left and right, or follow the camera in a walk-through clip (camera moving right
→ `dir` 1). Total length: overlaps shorten the video by their length (as crossfades do); flash and wash
don't.

## On the beat

When the cut uses a track from `brand/music/`, read its `.beats.json` and move each cut (the midpoint or
peak above) to the nearest beat, by at most 0.15 s: lengthen or shorten the two neighbouring shots, keep the
total length and every text and caption's minimum time on screen. Beat times count from the track's start,
so if the music starts later in the track (an offset), subtract the offset. The hook's first cut and the
end card's start go on a beat too. A music file from the listing's `assets/` has no grid: run
`python3 scripts/music_beats.py --out-dir <scratch> <file>` first (never write into `assets/`), or keep the
brief's timings if it fails.
