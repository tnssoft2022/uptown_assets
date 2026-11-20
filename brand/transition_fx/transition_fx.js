// Transitions for the editor's HyperFrames cuts (see brand/transition_fx/SNIPPETS.md).
// Copy into the cut as assets/transition_fx.js and load it after GSAP, before the main timeline script.
// Every helper adds deterministic tweens to the paused timeline `tl`. Shots keep their Ken Burns tweens on
// their <img>; transitions move the shot's inner `.mv` wrapper and only tween a `.clip`'s opacity.
// Nothing here bends or warps a photo: it slides, scales evenly, fades, or lays light over it.
(function () {
  const W = 1080;

  const tr = {
    // Plain crossfade: the incoming shot starts at t and fades in over d; the outgoing shot ends at t + d.
    crossfade(tl, outSel, inSel, t, d = 0.3) {
      tl.fromTo(inSel, { opacity: 0 }, { opacity: 1, duration: d, ease: "none" }, t);
    },

    // Whip pan: both shots slide sideways together (a push) with horizontal motion blur at the middle.
    // Overlap d (incoming starts at t, outgoing ends at t + d). dir 1 = new shot enters from the right.
    // Each shot's `.mb` (a horizontally blurred copy, made with ffmpeg) fades up/down around the midpoint.
    whip(tl, outSel, inSel, t, dir = 1, d = 0.3) {
      tl.fromTo(outSel + " .mv", { x: 0 }, { x: -dir * W, duration: d, ease: "power3.inOut" }, t);
      tl.fromTo(inSel + " .mv", { x: dir * W }, { x: 0, duration: d, ease: "power3.inOut" }, t);
      if (document.querySelector(outSel + " .mb")) {
        tl.fromTo(outSel + " .mb", { opacity: 0 }, { opacity: 1, duration: d * 0.45, ease: "power2.in" }, t);
      }
      if (document.querySelector(inSel + " .mb")) {
        tl.fromTo(inSel + " .mb", { opacity: 1 }, { opacity: 0, duration: d * 0.45, ease: "power2.out" }, t + d * 0.55);
      }
    },

    // Zoom through: the outgoing shot pushes in fast while the incoming one settles from 112% and fades in.
    // Overlap d.
    zoom(tl, outSel, inSel, t, d = 0.35) {
      tl.fromTo(outSel + " .mv", { scale: 1 }, { scale: 1.35, duration: d, ease: "power2.in" }, t);
      tl.fromTo(inSel + " .mv", { scale: 1.12 }, { scale: 1, duration: d + 0.25, ease: "power2.out" }, t);
      tl.fromTo(inSel, { opacity: 0 }, { opacity: 1, duration: d, ease: "power1.inOut" }, t);
    },

    // Fade through a colour (เรียบหรู): hard cut at t under a full-frame wash that peaks at the cut.
    // washSel is a full-frame <div class="clip wash"> from t - d/2 to t + d/2. No overlap.
    fadeThrough(tl, washSel, t, d = 0.6) {
      tl.fromTo(washSel, { opacity: 0 }, { opacity: 1, duration: d / 2, ease: "power1.in" }, t - d / 2);
      tl.fromTo(washSel, { opacity: 1 }, { opacity: 0, duration: d / 2, ease: "power1.out", immediateRender: false }, t);
    },

    // Warm camera flash (เดินชมห้อง): hard cut at t under a soft warm flash that peaks at the cut.
    // flashSel is a full-frame <div class="clip flash"> from t - d/2 to t + d/2. No overlap.
    flash(tl, flashSel, t, d = 0.3) {
      tl.fromTo(flashSel, { opacity: 0 }, { opacity: 0.95, duration: d / 2, ease: "power2.in" }, t - d / 2);
      tl.fromTo(flashSel, { opacity: 0.95 }, { opacity: 0, duration: d / 2, ease: "power2.out", immediateRender: false }, t);
    },

    // Light leak (เรียบหรู, at most 2-3 per video): warm light drifts across the frame over a cut.
    // leakSel is a <div class="clip leak"> with three `.lk` layers, from t - d/2 to t + d/2. Lays light
    // over the picture; it never hides a defect for long (under 1 s, peak 70%).
    leak(tl, leakSel, t, d = 0.9) {
      tl.fromTo(leakSel, { opacity: 0 }, { opacity: 0.7, duration: d * 0.4, ease: "sine.out" }, t - d / 2);
      tl.fromTo(leakSel, { opacity: 0.7 }, { opacity: 0, duration: d * 0.6, ease: "sine.in", immediateRender: false }, t - d / 2 + d * 0.4);
      tl.fromTo(leakSel + " .lk", { xPercent: -25 }, { xPercent: 25, duration: d, ease: "sine.inOut", stagger: 0 }, t - d / 2);
    },

    // Push inside a frame (การ์ดข้อมูล photos): the new photo pushes the old one out to the left.
    // Both shots sit in a frame with overflow hidden; dist is the frame width. Overlap d.
    push(tl, outSel, inSel, t, d = 0.35, dist = 960) {
      tl.fromTo(outSel + " .mv", { x: 0 }, { x: -dist, duration: d, ease: "power3.inOut" }, t);
      tl.fromTo(inSel + " .mv", { x: dist }, { x: 0, duration: d, ease: "power3.inOut" }, t);
    },

    // Lift (การ์ดข้อมูล section change): the old frame rises and fades, the new one rises into place.
    // Overlap d.
    lift(tl, outSel, inSel, t, d = 0.4, dist = 90) {
      tl.fromTo(outSel + " .mv", { y: 0, opacity: 1 }, { y: -dist, opacity: 0, duration: d * 0.6, ease: "power2.in" }, t);
      tl.fromTo(inSel + " .mv", { y: dist, opacity: 0 }, { y: 0, opacity: 1, duration: d * 0.7, ease: "power2.out" }, t + d * 0.3);
    },
  };

  window.tr = tr;
})();
