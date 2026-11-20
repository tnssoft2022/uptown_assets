// Motion graphics for the editor's HyperFrames cuts (see brand/motion_fx/SNIPPETS.md): the price highlight,
// animated feature icons and graphic-layer parallax. Copy into the cut as assets/motion_fx.js and load it
// after GSAP. Every helper adds deterministic tweens to the paused timeline `tl` at time `t` (seconds) and
// moves only its own inner elements, never a `.clip` (a clip may only have its opacity tweened).
(function () {
  const all = (sel) => Array.from(document.querySelectorAll(sel));
  const one = (sel) => document.querySelector(sel);

  const mfx = {
    // Price highlight. Label rises, the gold plate wipes in from the left, the number pops in at its final
    // value (never counts up), one sheen crosses the plate, then the sub-line rises. About 1.2 s in all.
    // A block without .pr-bg / .pr-sheen (เรียบหรู "pr--quiet") gets the number and its gold rule only.
    price(tl, sel, t) {
      if (one(sel + " .pr-lbl")) {
        tl.fromTo(sel + " .pr-lbl", { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.25, ease: "power2.out" }, t);
      }
      const plate = !!one(sel + " .pr-bg");
      if (plate) {
        tl.fromTo(sel + " .pr-bg", { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power3.out" }, t + 0.1);
      }
      tl.fromTo(sel + " .pr-num", { scale: 1.15, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)" }, t + (plate ? 0.25 : 0.1));
      if (one(sel + " .pr-rule")) {
        tl.fromTo(sel + " .pr-rule", { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power2.inOut" }, t + 0.35);
      }
      if (one(sel + " .pr-band")) {
        tl.fromTo(sel + " .pr-band", { xPercent: -120 }, { xPercent: 320, duration: 0.6, ease: "power1.inOut" }, t + 0.6);
      }
      if (one(sel + " .pr-sub")) {
        tl.fromTo(sel + " .pr-sub", { y: 24, opacity: 0 }, { y: 0, opacity: 1, duration: 0.25, ease: "power2.out" }, t + 0.65);
      }
    },

    // Feature icons (.ic-row or .ic-list of .ic items): each badge ring pops, its line icon draws itself
    // stroke by stroke, then its label rises; items follow 0.12 s apart. About 0.75 s + 0.12 s per item.
    icons(tl, sel, t) {
      all(sel + " .ic").forEach((item, i) => {
        const at = t + i * 0.12;
        const ring = item.querySelector(".ic-ring");
        if (ring) {
          tl.fromTo(ring, { scale: 0.6, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.25, ease: "back.out(2)" }, at);
        }
        const shapes = item.querySelectorAll("svg path, svg circle, svg rect, svg line, svg polyline, svg polygon, svg ellipse");
        shapes.forEach((s) => { s.setAttribute("pathLength", "1"); s.style.strokeDasharray = "1"; });
        if (shapes.length) {
          // round line caps show as dots at zero length: keep the icon hidden until its strokes start
          tl.fromTo(item.querySelector("svg"), { opacity: 0 }, { opacity: 1, duration: 0.05, ease: "none" }, at + 0.1);
          tl.fromTo(shapes, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.45, ease: "power1.inOut", stagger: 0.04 }, at + 0.1);
        }
        const lbl = item.querySelector(".ic-lbl");
        if (lbl) {
          tl.fromTo(lbl, { y: 18, opacity: 0 }, { y: 0, opacity: 1, duration: 0.25, ease: "power2.out" }, at + 0.3);
        }
      });
    },

    // Graphic-layer parallax over a shot whose photo already has its Ken Burns move: the text/icon layer
    // (fg) drifts a little faster than the photo, a middle layer (scrim, card frame) half that, so the frame
    // reads as depth. Linear, the whole shot, at most 24 px. dir: the way the photo's content moves on
    // screen ("left", "right", "up", "down"); fg goes the same way. The photo itself is never moved here.
    parallax(tl, layers, t, dur, dir, px) {
      const d = Math.min(Math.abs(px || 18), 24);
      const axis = dir === "left" || dir === "right" ? "x" : "y";
      const sign = dir === "left" || dir === "up" ? -1 : 1;
      const go = (target, amount) => {
        if (!target || !one(target)) return;
        const from = {}; const to = { duration: dur, ease: "none" };
        from[axis] = -sign * amount / 2; to[axis] = sign * amount / 2;
        tl.fromTo(target, from, to, t);
      };
      go(layers.fg, d);
      go(layers.mid, d / 2);
    },
  };

  window.mfx = mfx;
})();
