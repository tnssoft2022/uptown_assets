# Text effects: blocks for the editor

How on-screen text and captions move in every cut. The style's "ข้อความเคลื่อนไหว" row in `STYLES.md` says
which effects it uses; this file says how to build them. The helpers are in `brand/text_fx/text_fx.js`.

Rules that hold for every effect:
- Thai moves by whole words or whole lines, never by character (vowels and tone marks would come apart).
  Words are the line's own space-separated parts: wrap each in `<span class="w">`; never split a Thai word
  that has no space in it.
- The hook is on screen from the first frame: `fx.hook` only settles its size, it never fades it in.
- Numbers (price, rent, area, rooms) appear at their final value with `fx.num`. Never count them up: the
  frames in between would show prices or sizes the listing doesn't state.
- The effects only move text; they never change the words, the layout positions or the safe zone.
- A highlight goes on one word per line at most, and only on a word the brief marks.

## Setup

Copy `brand/text_fx/text_fx.js` into the cut as `assets/text_fx.js` and load it after GSAP:

```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script src="assets/text_fx.js"></script>
```

Add these classes to the cut's CSS (the style's own text look, font, size and position stay as before):

```css
.tx { display: inline-block; transform-origin: 50% 50%; }
.w { display: inline-block; }
.num { display: inline-block; transform-origin: 50% 60%; }
.hl { position: relative; display: inline-block; z-index: 0; }
.hl-bar { position: absolute; left: -0.12em; right: -0.12em; top: 18%; bottom: 8%;
  background: rgba(201,160,99,0.9); border-radius: 6px; z-index: -1; transform-origin: 0 50%; }
.rv { display: inline-block; overflow: hidden; padding: 0.35em 0.2em 0.3em; vertical-align: top; }
.uline { width: 120px; height: 2px; background: #c9a063; margin: 0 auto; transform-origin: 50% 50%; }
```

## Markup

Every text line is a `.clip` (the timed element, as before) holding one `.tx` span; the helpers move the
`.tx` or its words, never the `.clip` (a `.clip` may only have its opacity tweened).

```html
<!-- a line, split into words for fx.rise -->
<div id="t2" class="clip lower" data-start="3" data-duration="3" data-track-index="2" style="z-index:50">
  <span class="tx"><span class="w">ห้องนั่งเล่น</span> <span class="w">รับแสง</span></span></div>

<!-- a highlighted word inside a line -->
<span class="w"><span class="hl"><span class="hl-bar"></span>โปร่ง</span></span>

<!-- a number line (or a number inside a line) -->
<div id="n2" class="clip lower" ...><span class="tx"><span class="num">5.5 ล้านบาท</span></span></div>

<!-- เรียบหรู: the line inside a clipping .rv, the gold rule under it -->
<div id="t3" class="clip lower" ...><span class="rv"><span class="tx">วิวเมือง</span></span><div class="uline"></div></div>
```

## Timeline

Call the helpers in the main timeline, before `window.__timelines["main"] = tl`. `t` is when the effect
starts (normally the clip's `data-start`); `fx.out` takes the time the text must be gone by (the clip's end
or the cut).

| Helper | Effect | Length |
|---|---|---|
| `fx.hook(tl, "#t1", 0)` | hook visible at once, settles 112% → 100% | 0.25 s |
| `fx.rise(tl, "#t2", t)` | words rise 30 px and fade in, 0.08 s apart (no `.w`: the whole line) | 0.25 s + stagger |
| `fx.reveal(tl, "#t3", t)` | line slides up from behind its baseline, gold rule draws under it | 0.6 s |
| `fx.sticker(tl, "#k3", t)` | label pops in tilted −6° and straightens | 0.4 s |
| `fx.num(tl, "#n2", t)` | number pops 118% → 100% at its final value | 0.3 s |
| `fx.highlight(tl, "#t2", t)` | gold bar wipes in behind the `.hl` word, left to right | 0.3 s |
| `fx.cap(tl, "#c1", t)` | caption phrase pops in at the time the voice says it | 0.15 s |
| `fx.wiggle(tl, "#r3", t)` | red sticker pops in and wiggles once | 0.67 s |
| `fx.out(tl, "#t2", end)` | slips down 16 px and fades in the last 0.2 s | 0.2 s |

Start a highlight after the line has landed (about `t + 0.45` after `fx.rise`). Keep every text on screen at
least 1.2 s counting from when it has landed, as `STYLES.md` says. With `fx.out` on a line, don't also fade
its `.clip` out at the same time.

Expected `HF check` notes: `negative_z_index` for `.hl-bar` (it sits behind its word on purpose).
