# Animated logo: blocks for the editor

Two pieces the `editor` agent pastes into every cut's `output/hyperframes/index.html`. Both are made from
the layers in `brand/logo_layers/` (ring, mark, uptown, assets: cut by position from `brand/logo.png` by
`scripts/split_logo.py`, never redrawn) plus `brand/logo.png` itself. Copy them into the cut as
`assets/logo.png` and `assets/logo/{ring,mark,uptown,assets}.png`.

The motion only moves, fades and lights the logo: its shape, colours and size at rest stay exactly as in
`brand/logo.png`.

`brand/logo_anim.mov` (900×900, ProRes 4444 with alpha, 2.4 s, the logo 848 px inside 26 px of padding) is
the same build-up rendered from `brand/logo_anim/index.html`, for use outside HyperFrames (CapCut, other
editors). `brand/logo_anim_preview.mp4` shows it on the brand wine colour. Cuts use the HTML below, not the
.mov.

## A. Corner logo (every shot)

Pops in over the first 0.5 s (the hook photo and text are already on screen), then stays still. A soft
gold sheen crosses the U about every 5.5 s and stops before the end card. Same box as before: x 40–200,
y 170–330, 92% opacity.

```html
<!-- CSS -->
<style>
  #logo { position: absolute; left: 40px; top: 170px; width: 160px; height: 160px; opacity: 0.92; }
  #logo-img { position: absolute; left: 0; top: 0; width: 160px; height: 160px; transform-origin: 50% 50%; }
  #logo-sheen { position: absolute; left: 0; top: 0; width: 160px; height: 160px; overflow: hidden;
    -webkit-mask-image: url(assets/logo/mark.png); -webkit-mask-size: 100% 100%;
    mask-image: url(assets/logo/mark.png); mask-size: 100% 100%; transform-origin: 50% 50%; }
  #logo-band { position: absolute; left: 0; top: 0; width: 60px; height: 160px;
    background: linear-gradient(100deg, rgba(255,248,225,0) 0%, rgba(255,248,225,0.6) 50%, rgba(255,248,225,0) 100%); }
</style>

<!-- markup: the wrapper is the timed clip (start 0, until the end card); children are animated -->
<div id="logo" class="clip" data-start="0" data-duration="END_START" data-track-index="4" style="z-index:60">
  <img id="logo-img" src="assets/logo.png" alt="Uptown Assets">
  <div id="logo-sheen"><div id="logo-band"></div></div>
</div>
```

```js
// in the main timeline, before window.__timelines["main"] = tl
tl.fromTo(["#logo-img", "#logo-sheen"], { scale: 0.8, opacity: 0 },
  { scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.6)" }, 0);
for (let t = 1.5; t + 0.7 <= END_START - 0.3; t += 5.5) {   // deterministic, no repeat:-1
  tl.fromTo("#logo-band", { x: -70 }, { x: 170, duration: 0.7, ease: "power1.inOut", immediateRender: false }, t);
}
tl.set("#logo-band", { x: -70 }, 0);
```

Replace `END_START` with the end card's start time (the corner logo stops there, as before; if the cut
fades it out before the end card, keep that fade on `#logo`).

## B. End card logo (the large logo)

Builds up in about 1.4 s, then holds: the white disc pops in, the ring draws clockwise from the top, the U
rises into place, UPTOWN then ASSETS fade up, and one sheen crosses the U. The end card text fades up from
0.75 s, so it is readable from about 1.1 s; the end card stays 3–4 s as the style says. Same place and size
as before: 360 px wide, centred (x 360–720), top at y 400 unless the layout moves it.

```html
<style>
  #end-logo { position: absolute; left: 360px; top: 400px; width: 360px; height: 360px; }
  #el { position: absolute; left: 0; top: 0; width: 848px; height: 848px;
    transform: scale(0.42453); transform-origin: 0 0; }   /* 360 / 848; #el itself is never animated */
  #el img, #el .lyr { position: absolute; left: 0; top: 0; width: 848px; height: 848px; }
  #el-disc { position: absolute; left: 16px; top: 16px; width: 816px; height: 816px; border-radius: 50%;
    background: #fff; transform-origin: 50% 50%; }
  #el-ring { --a: 0deg;
    -webkit-mask-image: conic-gradient(#000 var(--a), transparent var(--a));
    mask-image: conic-gradient(#000 var(--a), transparent var(--a)); }
  #el-mark { transform-origin: 50% 60%; }
  #el-sheen { overflow: hidden;
    -webkit-mask-image: url(assets/logo/mark.png); -webkit-mask-size: 100% 100%;
    mask-image: url(assets/logo/mark.png); mask-size: 100% 100%; }
  #el-band { position: absolute; left: 0; top: 0; width: 320px; height: 848px;
    background: linear-gradient(100deg, rgba(255,248,225,0) 0%, rgba(255,248,225,0.85) 50%, rgba(255,248,225,0) 100%); }
</style>

<!-- inside the end card shot, in place of <img id="end-logo" ...> -->
<div id="end-logo">
  <div id="el">
    <div id="el-disc"></div>
    <img id="el-ring" src="assets/logo/ring.png" alt="">
    <img id="el-mark" src="assets/logo/mark.png" alt="Uptown Assets">
    <div id="el-sheen" class="lyr"><div id="el-band"></div></div>
    <img id="el-up" src="assets/logo/uptown.png" alt="">
    <img id="el-as" src="assets/logo/assets.png" alt="">
  </div>
</div>
```

```js
const E = END_START;   // the end card's start time
tl.fromTo("#el-disc", { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.35, ease: "back.out(1.4)" }, E);
tl.fromTo("#el-ring", { "--a": "0deg" }, { "--a": "360deg", duration: 0.55, ease: "power2.inOut" }, E + 0.05);
tl.fromTo("#el-mark", { y: 70, scale: 0.9, opacity: 0 }, { y: 0, scale: 1, opacity: 1, duration: 0.45, ease: "power3.out" }, E + 0.25);
tl.fromTo("#el-up", { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: "power2.out" }, E + 0.5);
tl.fromTo("#el-as", { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: "power2.out" }, E + 0.6);
tl.fromTo("#el-band", { x: -360 }, { x: 900, duration: 0.55, ease: "power1.inOut" }, E + 1.1);
tl.fromTo("#end-text", { y: 20, opacity: 0 }, { y: 0, opacity: 1, duration: 0.35, ease: "power2.out" }, E + 0.75);
```

`#end-text` is the end card's text block (any id; animate the block, not the shot clip). If the end card
crossfades in, start `E` at the crossfade's start so the build-up begins as the card appears.
