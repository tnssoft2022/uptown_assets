# Text effects: blocks for the editor

How on-screen text and captions move in every cut. The style's "ข้อความเคลื่อนไหว" row in `STYLES.md` says
which effects it uses; this file says how to build them. The helpers are in `brand/text_fx/text_fx.js`.

Rules that hold for every effect:
- Thai moves by whole words or whole lines, never by bare character (vowels and tone marks would come
  apart). Words are the line's own space-separated parts: wrap each in `<span class="w">`; never split a Thai
  word that has no space in it by hand. Two helpers split for you, safely: `fx.pop` splits an unmarked line
  into dictionary words (`Intl.Segmenter`), and `fx.type` types it on by Thai cells (a consonant with all its
  vowels, tone mark and ์; a leading เ แ โ ใ ไ joined to the consonant after it). Nothing else splits Thai.
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

For the walk-through look (`fx.type`, `fx.pop`, `fx.sparkle`, `fx.burst`) add these too. The outline is
built from text-shadows like `--outline` in `brand/motion_fx/typography.css` (never `-webkit-text-stroke`:
it eats Thai vowel marks):

```css
:root {
  --outline-light: 3px 0 0 #fff, -3px 0 0 #fff, 0 3px 0 #fff, 0 -3px 0 #fff, 2.1px 2.1px 0 #fff, -2.1px 2.1px 0 #fff,
    2.1px -2.1px 0 #fff, -2.1px -2.1px 0 #fff, 2.8px 1.2px 0 #fff, -2.8px 1.2px 0 #fff, 2.8px -1.2px 0 #fff,
    -2.8px -1.2px 0 #fff, 1.2px 2.8px 0 #fff, -1.2px 2.8px 0 #fff, 1.2px -2.8px 0 #fff, -1.2px -2.8px 0 #fff,
    0 4px 12px rgba(0,0,0,0.45);
}
.on-photo-light { text-shadow: var(--outline-light); }   /* coloured text, white outline */
.c-gold { color: #b8862f; }                              /* feature lines on bright rooms */
.w { transform-origin: 50% 70%; }                        /* fx.pop grows words from their baseline */
.spk { position: absolute; width: 56px; height: 56px; color: #fff4c2;
  filter: drop-shadow(0 0 8px rgba(255,236,170,0.9)); }
.spk svg { width: 100%; height: 100%; display: block; }
.burst { position: absolute; width: 0; height: 0; }
.burst b { position: absolute; left: 0; top: 0; width: 0; height: 0; }
.burst i { position: absolute; left: -5px; bottom: 22px; width: 10px; height: 46px; border-radius: 5px;
  background: #fff; box-shadow: 0 0 0 2px rgba(0,0,0,0.55); transform-origin: 50% 100%; }
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

<!-- fx.type / fx.pop: plain text in the .tx, nothing to wrap (both split it themselves); keep each line
     nowrap (the typography classes do) so the final layout is fixed from the first frame -->
<div id="t4" class="clip line" ...><span class="tx"><span class="t-head c-gold on-photo-light">ฟังก์ชันครบครัน</span><br>
  <span class="t-head c-gold on-photo-light">ตู้เสื้อผ้าบิลต์อิน</span></span></div>

<!-- fx.sparkle: up to 3 .spk stars in the clip, placed by hand beside the line (not over its words) -->
<span class="spk" style="left:20px;top:-30px"><svg viewBox="0 0 24 24"><path fill="currentColor"
  d="M12 0C13 8 16 11 24 12C16 13 13 16 12 24C11 16 8 13 0 12C8 11 11 8 12 0Z"/></svg></span>

<!-- fx.burst: three strokes off the top-right corner of a price; each <b> sets one stroke's angle -->
<span class="burst" style="left:900px;top:30px"><b style="rotate:-15deg"><i></i></b><b style="rotate:30deg"><i></i></b><b style="rotate:75deg"><i></i></b></span>

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
| `fx.type(tl, "#t4", t)` | types on by Thai cells at its final layout, 0.045 s a cell (`dur` 4th argument; at most 1.0 s) | ≤ 1.0 s |
| `fx.pop(tl, "#t5", t)` | words grow from 40% with an overshoot, 0.12 s apart (its `.w`, else dictionary words) | 0.3 s + stagger |
| `fx.blurIn(tl, "#t1", t)` | title comes into focus from a 14 px blur, 104% → 100% | 0.8 s |
| `fx.sparkle(tl, "#t5", t)` | the clip's `.spk` stars pop in turning 90°, 0.1 s apart, then rest | 0.45 s + stagger |
| `fx.burst(tl, "#n4", t)` | the `.burst` strokes shoot out from their inner end | 0.35 s |
| `fx.out(tl, "#t2", end)` | slips down 16 px and fades in the last 0.2 s | 0.2 s |

`fx.pop` on a two-line fact (size, then floor) reads best with up to ~8 words; past that the last word lands
after 1.2 s, so split it into two clips or use `fx.rise`. Start `fx.sparkle` about 0.3 s after `fx.pop`, and
`fx.burst` about 0.25 s after `fx.num`. One accent per scene: sparkles or a burst, not both, and not with a
highlight. `fx.blurIn` is for a title over a calm shot (a view, the exterior), never the hook: the hook is on
screen sharp from the first frame.

Start a highlight after the line has landed (about `t + 0.45` after `fx.rise`). Keep every text on screen at
least 1.2 s counting from when it has landed, as `STYLES.md` says. With `fx.out` on a line, don't also fade
its `.clip` out at the same time.

Expected `HF check` notes: `negative_z_index` for `.hl-bar` (it sits behind its word on purpose).
