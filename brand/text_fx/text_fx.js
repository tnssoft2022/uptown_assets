// Text effects for the editor's HyperFrames cuts (see brand/text_fx/SNIPPETS.md).
// Copy this file into the cut as assets/text_fx.js and load it after GSAP, before the main timeline script.
// Every helper adds deterministic tweens to the paused timeline `tl` at time `t` (seconds). They move the
// inner `.tx` of a text clip (or its `.w` words), never the `.clip` itself, so the clip's own opacity stays
// the clip's. Thai is moved by whole words or lines only, never by character.
(function () {
  const q = (sel) => document.querySelector(sel);

  const fx = {
    // Hook: on screen from its first frame, then settles from 112% to 100% (no fade-in).
    hook(tl, sel, t) {
      tl.fromTo(`${sel} .tx`, { scale: 1.12 }, { scale: 1, duration: 0.25, ease: "power3.out" }, t);
    },

    // มาตรฐาน: words rise 30 px and fade in, 0.08 s apart (words are the line's own space-separated parts).
    rise(tl, sel, t) {
      const parts = q(sel).querySelectorAll(".w").length ? `${sel} .w` : `${sel} .tx`;
      tl.fromTo(parts, { y: 30, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.25, ease: "power2.out", stagger: 0.08 }, t);
    },

    // เรียบหรู: the line slides up from behind its baseline (.rv clips it), then a thin gold line draws under it.
    reveal(tl, sel, t) {
      tl.fromTo(`${sel} .tx`, { yPercent: 110 }, { yPercent: 0, duration: 0.6, ease: "power3.out" }, t);
      if (q(`${sel} .uline`)) {
        tl.fromTo(`${sel} .uline`, { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power2.inOut" }, t + 0.25);
      }
    },

    // เดินชมห้อง: room label pops in like a sticker, tilted, then straightens.
    sticker(tl, sel, t) {
      tl.fromTo(`${sel} .tx`, { scale: 0.6, rotation: -6, opacity: 0 },
        { scale: 1, rotation: 0, opacity: 1, duration: 0.4, ease: "back.out(2.2)" }, t);
    },

    // Numbers (price, size, rooms): pop in at their final value. Never count up: the frames in between
    // would show prices or sizes the listing doesn't state.
    num(tl, sel, t) {
      tl.fromTo(`${sel} .num`, { scale: 1.18, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)" }, t);
    },

    // One highlighted word per line: a gold bar wipes in behind it from the left.
    highlight(tl, sel, t) {
      tl.fromTo(`${sel} .hl-bar`, { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power2.out" }, t);
    },

    // Voice-over caption phrase: a quick pop as the phrase starts.
    cap(tl, sel, t) {
      tl.fromTo(`${sel} .tx`, { scale: 0.94, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.15, ease: "power2.out" }, t);
    },

    // การ์ดข้อมูล red sticker: one wiggle as it lands.
    wiggle(tl, sel, t) {
      const el = `${sel} .tx`;
      tl.fromTo(el, { scale: 0.6, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.25, ease: "back.out(2.5)" }, t);
      tl.fromTo(el, { rotation: 0 }, { rotation: -6, duration: 0.1, ease: "sine.inOut" }, t + 0.25);
      tl.fromTo(el, { rotation: -6 }, { rotation: 5, duration: 0.12, ease: "sine.inOut", immediateRender: false }, t + 0.35);
      tl.fromTo(el, { rotation: 5 }, { rotation: -3, duration: 0.1, ease: "sine.inOut", immediateRender: false }, t + 0.47);
      tl.fromTo(el, { rotation: -3 }, { rotation: 0, duration: 0.1, ease: "sine.inOut", immediateRender: false }, t + 0.57);
    },

    // Exit: slips down 16 px and fades in the last 0.2 s before `end` (the clip's end or the cut).
    out(tl, sel, end) {
      tl.fromTo(`${sel} .tx`, { y: 0, opacity: 1 },
        { y: 16, opacity: 0, duration: 0.2, ease: "power1.in", immediateRender: false }, end - 0.2);
    },
  };

  window.fx = fx;
})();
