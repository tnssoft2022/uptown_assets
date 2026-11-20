# Motion graphics: blocks for the editor

Typography, the price highlight, animated feature icons and parallax for every cut. Text effects for the
plain lines stay in `brand/text_fx/`, transitions in `brand/transition_fx/`. The style's rows in
`STYLES.md` ("ฟอนต์", "ราคา", "ไอคอน", "Parallax") say which variant it uses.

`motion_fx_preview.mp4` (7 s) shows them on the 4615 pool villa photos: a head line and three icons with
parallax over a push-in, then the price highlight over a pan.

## Rules for every cut

- **Two points per scene at most.** A scene (one shot, or one run of fast shots) carries at most two text
  elements besides the voice-over caption and the logo: e.g. a head line + a sub-line, a head line + an
  icon row, or the price block (label, price and one sub-line count as one). An icon row holds 2–4 icons
  of one kind of fact (the spec: beds, baths, area; or amenities; or nearby places).
- **Restraint.** One accent per scene (a highlight bar, the price sheen, a sticker): never two. Entrances
  last 0.6 s at most per element and are done within 1.2 s of the scene's start; then everything holds
  still (only the slow Ken Burns and parallax keep going) and stays on screen at least 1.2 s. No loops,
  bounces after landing, shakes, spins, glitches, counting numbers or text that moves along a path. Fast
  shots get no entrance of their own: their text arrives with the first shot of the run.
- **Safe zone** (Reels, TikTok, Shorts): every text, icon and price block inside x 60–930 and y 380–1470
  (the editor's safe zone: clear of the top 150 px, the bottom 450 px and the right 150 px, plus the logo
  box at x 40–200, y 170–330). Parallax drift counts: keep the block 24 px clear of those edges.
- **Readable on any photo.** White text uses `.on-photo` (outline) or `.on-photo-soft` (shadow, by the
  style). Where `output/analysis/plan.json` says the text band is "พอใช้ ใส่เงา" or "พื้นรก ใส่แถบเข้ม", put a
  `.scrim-band` behind the block.
- **Facts only.** Every number, icon and price comes from the brief, which takes it from the listing.

## Setup

Copy into the cut: `brand/motion_fx/typography.css` → `assets/typography.css`, `brand/motion_fx/motion_fx.js`
→ `assets/motion_fx.js`, `brand/fonts/kanit/*.ttf` → `assets/fonts/`. Load them after GSAP:

```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script src="assets/text_fx.js"></script>
<script src="assets/motion_fx.js"></script>
<link rel="stylesheet" href="assets/typography.css">
```

## Typography

Kanit for the hook, head lines, prices and icon labels; Sarabun for lines, sub-lines, captions, chips and
card items. Classes (px on 1080×1920; a style may change weight, size or colour):

| Class | Font | Size | Use |
|---|---|---|---|
| `.t-hook` | Kanit Bold | 96 | the hook line (one per video) |
| `.t-head` | Kanit SemiBold | 72 | a scene's main line |
| `.t-line` | Sarabun Bold | 66 | a plain line (มาตรฐาน lower third) |
| `.t-sub` | Sarabun SemiBold | 50 | the second point of a scene |
| `.t-price` | Kanit Bold | 112 | the price in the price block |
| `.t-label` | Kanit Medium | 42 | small label over a number ("ราคาขาย") |
| `.t-icon` | Kanit Medium | 40 | icon labels; numbers in `<span class="v">` turn gold |
| `.t-cap` | Sarabun Bold | 48 | voice-over captions |
| `.t-chip` | Sarabun Bold | 34 | chips (การ์ดข้อมูล) |

Thai: one element per line, broken only where the brief breaks it; no letter-spacing; line-height 1.25 or
more; nothing under 34 px. Wrap `.lux` around the cut's root for เรียบหรู (Light weights). Lines that use
`fx.rise` keep their `.w` word spans as in `brand/text_fx/SNIPPETS.md`.

## Price highlight

```html
<div id="p1" class="clip" data-start="24" data-duration="3" data-track-index="3"
     style="position:absolute; left:0; top:0; width:1080px; height:1920px; z-index:50">
  <div class="px" id="p1fg">
    <div class="pr" style="top:760px">
      <div class="pr-lbl t-label on-photo">ราคาขาย</div>
      <div class="pr-plate"><div class="pr-bg"></div><span class="pr-num t-price">10 ล้านบาท</span>
        <div class="pr-sheen" data-layout-allow-overflow><div class="pr-band"></div></div></div>
      <div class="pr-sub t-sub on-photo">ค่าโอนคนละครึ่ง</div>
    </div>
  </div>
</div>
```

`mfx.price(tl, "#p1", t)`: label rises, gold plate wipes in from the left, the number pops in at its final
value, one sheen crosses the plate, the sub-line rises (about 1.2 s). Variants: `pr pr--yellow` (เดินชมห้อง);
`pr pr--quiet` for เรียบหรู: leave out `.pr-bg` and `.pr-sheen`, add `<div class="pr-rule"></div>` inside
`.pr-plate` (the number over a thin gold rule). In the hook (price within the first 3 s) the price is a
second line or chip with `fx.num`, not the full block; the block is for the price shot before the CTA. The
sub-line is optional and only a fact from the listing (ค่าโอน, ส่วนลด, "ต่อเดือน").

## Feature icons

A row (2–4 items, under a head line):

```html
<div id="i1" class="ic-row" style="top:1090px">
  <div class="ic"><div class="ic-badge"><div class="ic-ring"></div><!-- paste brand/icons/bed-double.svg --></div>
    <div class="ic-lbl t-icon"><span class="v">8</span> ห้องนอน</div></div>
  ...
</div>
```

A list (cards: ส่วนกลาง, ใกล้; up to 4 rows): the same items in `<div class="ic-list">`, each label the
card's line as the brief writes it ("สระว่ายน้ำ", "BTS อ่อนนุช · 300 ม.").

`mfx.icons(tl, "#i1", t)`: each ring pops, its icon draws itself stroke by stroke, then its label rises;
items 0.12 s apart. Paste the `<svg>` from `brand/icons/<name>.svg` without its comment line and `class`;
`brand/icons/ICONS.md` says which icon goes with which fact.

## Smooth zoom and pan

The Ken Burns move on the `<img>` (as in the editor's rules) stays linear (`ease: "none"`) for the whole
shot, starts on the shot's first frame and never stops or changes speed inside the shot. One move per shot
(zoom or pan, not both). Zoom 3–6% per shot; pan at most about 40 px per second on the 1080 frame. Slow
shots use the smaller end. Neighbouring shots alternate direction.

## Parallax (graphic layers)

Wrap the scene's text/icon block in `<div class="px" id="…fg">` inside its clip, and optionally a middle
layer (a `.scrim-band`, the card frame of การ์ดข้อมูล, a blurred background copy) in another `.px`. Then:

```js
mfx.parallax(tl, { fg: "#g1fg", mid: "#s1mid" }, shotStart, shotDuration, "up", 18);
```

The photo keeps its own Ken Burns; the fg block drifts the same way the photo's content moves on screen
(push-in: "up"; pan right, where content moves left: "left"), 14–24 px over the shot, linear; the middle
layer half that. Use it on slow shots, the price shot and text cards, not on fast shots, hook shots that
must read in one glance, shots with a whip in or out, or the end card. The photo itself is never split into
layers or warped.
