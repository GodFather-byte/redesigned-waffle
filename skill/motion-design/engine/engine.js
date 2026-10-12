/*
 * motion-design engine — everything is a pure function of time.
 *
 *   window.seek(t)   -> draws the exact frame at second t (synchronous)
 *
 * No CSS transitions, no setTimeout/rAF-driven animation, no Date.now().
 * The renderer calls seek(t) (many times per frame for motion blur), waits two
 * rAFs, and screenshots. Same input -> same pixels, always.
 */
(function (g) {
  "use strict";
  const MD = {};

  /* ---------- math ---------- */
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, p) => a + (b - a) * p;
  /** progress of t inside [a,b], clamped 0..1 */
  const prog = (t, a, b) => (b === a ? (t >= b ? 1 : 0) : clamp((t - a) / (b - a)));
  /** remap v from [a,b] to [c,d], clamped */
  const map = (v, a, b, c, d, e) => lerp(c, d, (e || ((x) => x))(prog(v, a, b)));
  Object.assign(MD, { clamp, lerp, prog, map });

  /* ---------- easings (all take p in 0..1) ---------- */
  MD.ease = {
    linear: (p) => p,
    inQuad: (p) => p * p,
    outQuad: (p) => 1 - (1 - p) * (1 - p),
    outCubic: (p) => 1 - Math.pow(1 - p, 3),
    inOutCubic: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
    outQuart: (p) => 1 - Math.pow(1 - p, 4),
    outExpo: (p) => (p >= 1 ? 1 : 1 - Math.pow(2, -10 * p)),
    inOutQuint: (p) => (p < 0.5 ? 16 * Math.pow(p, 5) : 1 - Math.pow(-2 * p + 2, 5) / 2),
    outBack: (p, s = 1.70158) => 1 + (s + 1) * Math.pow(p - 1, 3) + s * Math.pow(p - 1, 2),
    /** cubic-bezier like CSS, solved by bisection */
    bezier(x1, y1, x2, y2) {
      const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
      const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
      const X = (s) => ((ax * s + bx) * s + cx) * s;
      const Y = (s) => ((ay * s + by) * s + cy) * s;
      return (p) => {
        if (p <= 0) return 0;
        if (p >= 1) return 1;
        let lo = 0, hi = 1, s = p;
        for (let i = 0; i < 24; i++) { s = (lo + hi) / 2; X(s) < p ? (lo = s) : (hi = s); }
        return Y(s);
      };
    },
  };

  /* ---------- closed-form spring: 0 -> 1 from rest, evaluated at time t (s) ---------- */
  MD.spring = function (t, o) {
    if (t <= 0) return 0;
    const { k = 170, c = 18, m = 1 } = o || {};
    const w0 = Math.sqrt(k / m), z = c / (2 * Math.sqrt(k * m));
    if (z < 1) {
      const wd = w0 * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0) / wd) * Math.sin(wd * t));
    }
    if (z === 1) return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
    const s = w0 * Math.sqrt(z * z - 1), r1 = -z * w0 + s, r2 = -z * w0 - s;
    return 1 - (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r2 - r1);
  };
  /** spring that starts at time `t0` */
  MD.springAt = (t, t0, o) => MD.spring(t - t0, o);

  /* ---------- seeded noise (deterministic "randomness") ---------- */
  MD.rand = function (seed) {
    let s = (seed >>> 0) || 1;
    return () => ((s = (Math.imul(s ^ (s >>> 15), 2246822507) + 0x9e3779b9) >>> 0), (s >>> 0) / 4294967296);
  };

  /* ---------- scenes ---------- */
  const scenes = [];
  /**
   * MD.scene(start, end, fn(lt, dur, p, t))
   * `el` (optional string selector / element) is shown only while t in [start,end).
   */
  MD.scene = function (start, end, fn, el) {
    scenes.push({ start, end, fn, el: typeof el === "string" ? el : el || null });
  };

  /* ---------- camera keyed in log-space (zoom feels constant-speed) ---------- */
  /**
   * keys: [{t, x, y, z, ease?}] — (x,y) is the world point at screen centre, z is zoom.
   * Between keys, zoom is interpolated in log space, position linearly under the same ease.
   */
  MD.camera = function (keys, ease) {
    return function at(t) {
      if (t <= keys[0].t) return keys[0];
      for (let i = 0; i < keys.length - 1; i++) {
        const a = keys[i], b = keys[i + 1];
        if (t < b.t) {
          const e = (b.ease || ease || MD.ease.inOutQuint)(prog(t, a.t, b.t));
          return { x: lerp(a.x, b.x, e), y: lerp(a.y, b.y, e), z: Math.exp(lerp(Math.log(a.z), Math.log(b.z), e)) };
        }
      }
      return keys[keys.length - 1];
    };
  };
  /** apply a camera sample to a world element inside a W x H stage */
  MD.applyCamera = function (world, cam, W, H) {
    world.style.transform = `translate(${W / 2}px,${H / 2}px) scale(${cam.z}) translate(${-cam.x}px,${-cam.y}px)`;
  };

  /* ---------- masked word-by-word text ---------- */
  MD.splitWords = function (el) {
    if (el.__split) return el.__split;
    const words = el.textContent.trim().split(/\s+/);
    el.textContent = "";
    el.__split = words.map((w, i) => {
      const outer = document.createElement("span");
      outer.style.cssText = "display:inline-block;overflow:hidden;vertical-align:top;padding:0.08em 0;margin:-0.08em 0";
      const inner = document.createElement("span");
      inner.style.cssText = "display:inline-block;will-change:transform";
      inner.textContent = w;
      outer.appendChild(inner);
      el.appendChild(outer);
      if (i < words.length - 1) el.appendChild(document.createTextNode(" "));
      return inner;
    });
    return el.__split;
  };
  MD.revealWords = function (el, t, o) {
    const { start = 0, stagger = 0.06, spring = { k: 220, c: 24 }, from = 110 } = o || {};
    MD.splitWords(el).forEach((inner, i) => {
      const p = MD.spring(t - start - i * stagger, spring);
      inner.style.transform = `translateY(${(1 - p) * from}%)`;
    });
  };
  /** typed text: returns the first n chars at `cps` chars/second */
  MD.typed = (str, t, start, cps = 40) => str.slice(0, Math.max(0, Math.floor((t - start) * cps)));

  /* ---------- colour flood: circle that grows from (ox,oy) until the FARTHEST corner is covered ---------- */
  MD.flood = function (el, ox, oy, p, W, H) {
    const r = Math.max(Math.hypot(ox, oy), Math.hypot(W - ox, oy), Math.hypot(ox, H - oy), Math.hypot(W - ox, H - oy));
    el.style.clipPath = `circle(${(p * r).toFixed(2)}px at ${ox}px ${oy}px)`;
  };

  /* ---------- shared-element handoff: fly `el` from rect A to rect B ---------- */
  MD.rect = (el) => {
    const r = el.getBoundingClientRect();
    return { x: r.left, y: r.top, w: r.width, h: r.height };
  };
  MD.fly = function (el, a, b, p) {
    el.style.transformOrigin = "0 0";
    el.style.transform = `translate(${lerp(a.x - b.x, 0, p)}px,${lerp(a.y - b.y, 0, p)}px) scale(${lerp(a.w / b.w, 1, p)},${lerp(a.h / b.h, 1, p)})`;
  };

  /* ---------- seek(t)-driven adaptations of 21st.dev components ---------- */
  /**
   * Animated Beam: a gradient pulse travelling along an SVG <path>.
   * `path` is the SVG path; `pulse` is a second <path> (same d) with stroke="url(#grad)"-like dash.
   */
  MD.beam = function (pulse, t, o) {
    const { start = 0, dur = 1.6, len = 0.28, ease = MD.ease.inOutCubic } = o || {};
    const L = pulse.getTotalLength();
    const p = ease(prog(t, start, start + dur));
    const seg = L * len;
    pulse.style.strokeDasharray = `${seg} ${L + seg}`;
    pulse.style.strokeDashoffset = String(seg - p * (L + seg));
    pulse.style.opacity = t < start || t > start + dur ? 0 : 1;
  };
  /** Border Beam: a light that orbits the border. Needs .md-border-beam from engine.css */
  MD.borderBeam = function (el, t, period = 3, phase = 0) {
    el.style.setProperty("--md-angle", ((((t / period + phase) % 1) + 1) % 1) * 360 + "deg");
  };
  /** count-up number with an ease */
  MD.count = (t, a, b, from, to, fmt = Math.round, ease = MD.ease.outExpo) => fmt(lerp(from, to, ease(prog(t, a, b))));

  /* ---------- beat helpers ---------- */
  MD.beats = { bpm: 120, offset: 0 };
  MD.snap = (t) => {
    const spb = 60 / MD.beats.bpm;
    return MD.beats.offset + Math.round((t - MD.beats.offset) / spb) * spb;
  };
  /** 1 on a beat, decaying to 0 — handy for pulses */
  MD.pulse = (t, decay = 6) => {
    const spb = 60 / MD.beats.bpm;
    const ph = (((t - MD.beats.offset) % spb) + spb) % spb;
    return Math.exp(-decay * ph);
  };

  /* ---------- driver ---------- */
  MD.cuts = []; // hard cuts (seconds) — the renderer never motion-blurs across these
  MD.duration = 0;
  MD.t = 0;

  function freezeNativeAnimations(t) {
    // CSS animations / WAAPI / SMIL: pause and scrub to t instead of letting the wall clock run.
    if (document.getAnimations) document.getAnimations().forEach((a) => { try { a.pause(); a.currentTime = t * 1000; } catch (e) {} });
    document.querySelectorAll("svg").forEach((s) => { try { s.pauseAnimations(); s.setCurrentTime(t); } catch (e) {} });
    // GSAP, if present: scrub a registered master timeline
    if (g.gsap && MD.gsapTimeline) MD.gsapTimeline.time(t, false);
  }

  g.seek = MD.seek = function (t) {
    MD.t = t;
    freezeNativeAnimations(t);
    for (const s of scenes) {
      const on = t >= s.start && t < s.end;
      if (s.el) {
        const e = typeof s.el === "string" ? document.querySelector(s.el) : s.el;
        if (e) e.style.display = on ? "" : "none";
      }
      if (on) s.fn(t - s.start, s.end - s.start, prog(t, s.start, s.end), t);
    }
    if (MD.onFrame) MD.onFrame(t);
    return t;
  };

  /** Call once after scenes are registered. Waits for fonts + images so frame 0 is final. */
  MD.ready = async function (o) {
    Object.assign(MD, o || {});
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    await Promise.all([...document.images].map((i) => (i.complete ? 0 : new Promise((r) => { i.onload = i.onerror = r; }))));
    g.seek(0);
    g.__mdReady = true;
  };

  g.MD = MD;
})(window);
