// Text effects for the editor's HyperFrames cuts (see brand/text_fx/SNIPPETS.md).
// Copy this file into the cut as assets/text_fx.js and load it after GSAP, before the main timeline script.
// Every helper adds deterministic tweens to the paused timeline `tl` at time `t` (seconds). They move the
// inner `.tx` of a text clip (or its `.w` words), never the `.clip` itself, so the clip's own opacity stays
// the clip's. Thai is moved by whole words or lines; only fx.type goes finer, by whole Thai cells (a consonant
// with all its marks), never by bare character.
(function () {
  const q = (sel) => document.querySelector(sel);

  const fx = {
    // Hook: on screen from its first frame, then settles from 112% to 100% (no fade-in).
    hook(tl, sel, t) {
      tl.fromTo(sel + " .tx", { scale: 1.12 }, { scale: 1, duration: 0.25, ease: "power3.out" }, t);
    },

    // มาตรฐาน: words rise 30 px and fade in, 0.08 s apart (words are the line's own space-separated parts).
    rise(tl, sel, t) {
      const parts = q(sel).querySelectorAll(".w").length ? sel + " .w" : sel + " .tx";
      tl.fromTo(parts, { y: 30, opacity: 0 },
        { y: 0, opacity: 1, duration: 0.25, ease: "power2.out", stagger: 0.08 }, t);
    },

    // เรียบหรู: the line slides up from behind its baseline (.rv clips it), then a thin gold line draws under it.
    reveal(tl, sel, t) {
      tl.fromTo(sel + " .tx", { yPercent: 110 }, { yPercent: 0, duration: 0.6, ease: "power3.out" }, t);
      if (q(sel + " .uline")) {
        tl.fromTo(sel + " .uline", { scaleX: 0 }, { scaleX: 1, duration: 0.5, ease: "power2.inOut" }, t + 0.25);
      }
    },

    // เดินชมห้อง: room label pops in like a sticker, tilted, then straightens.
    sticker(tl, sel, t) {
      tl.fromTo(sel + " .tx", { scale: 0.6, rotation: -6, opacity: 0 },
        { scale: 1, rotation: 0, opacity: 1, duration: 0.4, ease: "back.out(2.2)" }, t);
    },

    // Numbers (price, size, rooms): pop in at their final value. Never count up: the frames in between
    // would show prices or sizes the listing doesn't state.
    num(tl, sel, t) {
      tl.fromTo(sel + " .num", { scale: 1.18, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2)" }, t);
    },

    // One highlighted word per line: a gold bar wipes in behind it from the left.
    highlight(tl, sel, t) {
      tl.fromTo(sel + " .hl-bar", { scaleX: 0 }, { scaleX: 1, duration: 0.3, ease: "power2.out" }, t);
    },

    // Voice-over caption phrase: a quick pop as the phrase starts.
    cap(tl, sel, t) {
      tl.fromTo(sel + " .tx", { scale: 0.94, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.15, ease: "power2.out" }, t);
    },

    // การ์ดข้อมูล red sticker: one wiggle as it lands.
    wiggle(tl, sel, t) {
      const el = sel + " .tx";
      tl.fromTo(el, { scale: 0.6, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.25, ease: "back.out(2.5)" }, t);
      tl.fromTo(el, { rotation: 0 }, { rotation: -6, duration: 0.1, ease: "sine.inOut" }, t + 0.25);
      tl.fromTo(el, { rotation: -6 }, { rotation: 5, duration: 0.12, ease: "sine.inOut", immediateRender: false }, t + 0.35);
      tl.fromTo(el, { rotation: 5 }, { rotation: -3, duration: 0.1, ease: "sine.inOut", immediateRender: false }, t + 0.47);
      tl.fromTo(el, { rotation: -3 }, { rotation: 0, duration: 0.1, ease: "sine.inOut", immediateRender: false }, t + 0.57);
    },

    // ---- Walk-through look (from the user's reference clip): typewriter, word pop, blur-in, sparkles, burst.
    // fx.type and fx.pop split the line themselves when the timeline is built (no hand-made spans needed).

    // Typewriter: the line types on, one Thai cell at a time, at its final layout (nothing reflows).
    // A cell is a grapheme cluster (a consonant keeps its vowels above/below, tone mark and ์), with a
    // leading vowel (เ แ โ ใ ไ) joined to the consonant after it, so no mark is ever shown alone.
    // `dur` (default: 0.045 s a cell, at most 1.0 s) is the time from the first cell to the last.
    type(tl, sel, t, dur) {
      const cells = splitCells(q(sel + " .tx"));
      const step = Math.min(dur != null ? dur : cells.length * 0.045, 1.0) / Math.max(cells.length - 1, 1);
      cells.forEach((c, i) => {
        tl.fromTo(c, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.06, ease: "none" }, t + i * step);
      });
    },

    // Word pop: each word scales up from 40% with a small overshoot, 0.12 s apart. Uses the line's `.w` spans
    // if it has them, else splits it into Thai words with the browser's dictionary (Intl.Segmenter).
    pop(tl, sel, t) {
      const words = splitWords(q(sel + " .tx"));
      tl.fromTo(words, { scale: 0.4, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.3, ease: "back.out(2.4)", stagger: 0.12 }, t);
    },

    // Blur-in (title over a view): comes into focus from a 14 px blur while settling from 104%.
    blurIn(tl, sel, t) {
      tl.fromTo(sel + " .tx", { opacity: 0, scale: 1.04, filter: "blur(14px)" },
        { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.8, ease: "power2.out" }, t);
    },

    // Sparkles: the `.spk` stars in the clip pop in turning 90°, 0.1 s apart, then rest (no looping).
    sparkle(tl, sel, t) {
      tl.fromTo(sel + " .spk", { scale: 0, rotation: -90, opacity: 0 },
        { scale: 1, rotation: 0, opacity: 1, duration: 0.45, ease: "back.out(3)", stagger: 0.1 }, t);
    },

    // Burst: the `.burst` strokes beside a price shoot out from their inner end.
    burst(tl, sel, t) {
      tl.fromTo(sel + " .burst i", { scaleY: 0, opacity: 0 },
        { scaleY: 1, opacity: 1, duration: 0.25, ease: "power3.out", stagger: 0.05 }, t);
    },

    // Exit: slips down 16 px and fades in the last 0.2 s before `end` (the clip's end or the cut).
    out(tl, sel, end) {
      tl.fromTo(sel + " .tx", { y: 0, opacity: 1 },
        { y: 16, opacity: 0, duration: 0.2, ease: "power1.in", immediateRender: false }, end - 0.2);
    },
  };

  // Wraps every text run under `root` into spans, keeping the other elements (.num, .hl, <br>) where they are.
  function wrapText(root, pieces, cls) {
    if (root.dataset.split) return Array.from(root.querySelectorAll("." + cls));
    root.dataset.split = cls;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    const out = [];
    nodes.forEach((n) => {
      const frag = document.createDocumentFragment();
      pieces(n.textContent).forEach((p) => {
        if (/^\s+$/.test(p)) { frag.appendChild(document.createTextNode(p)); return; }
        const s = document.createElement("span");
        s.className = cls;
        s.textContent = p;
        frag.appendChild(s);
        out.push(s);
      });
      n.parentNode.replaceChild(frag, n);
    });
    return out;
  }

  const LEAD = /^[เ-ไ]$/; // เ แ โ ใ ไ
  function cellsOf(text) {
    const g = Array.from(new Intl.Segmenter("th", { granularity: "grapheme" }).segment(text), (s) => s.segment);
    const out = [];
    for (let i = 0; i < g.length; i++) {
      let c = g[i];
      while (LEAD.test(c) && i + 1 < g.length) c += g[++i];
      if (/^\s$/.test(c) && out.length) { out[out.length - 1] += c; continue; } // a space rides with its cell
      out.push(c);
    }
    return out;
  }
  function splitCells(root) { return wrapText(root, cellsOf, "ch"); }

  function wordsOf(text) {
    const out = [];
    for (const s of new Intl.Segmenter("th", { granularity: "word" }).segment(text)) {
      if (/^\s+$/.test(s.segment)) out.push(s.segment);
      else if (!s.isWordLike && out.length && !/^\s+$/.test(out[out.length - 1])) out[out.length - 1] += s.segment;
      else out.push(s.segment);
    }
    return out;
  }
  function splitWords(root) {
    const own = root.querySelectorAll(".w");
    return own.length ? Array.from(own) : wrapText(root, wordsOf, "w");
  }

  window.fx = fx;
})();
