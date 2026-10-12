/* Phase 1 — shared frame-based engine for remakes.
 * Scenes are registered in REFERENCE FRAME numbers, so build agents can compare frame F of the copy
 * with frame F of the reference 1:1. Requires ../../engine/engine.js (for window.seek and MD).
 *
 *   RM.fps = 30;
 *   RM.scene(0, 44, (lf, n, p, F) => {...}, '#s1')     // frames [0,45)
 *   RM.palette({ ink:'#111', paper:'#f4efe6', accent:'#ff4d2e' })   // optional global palette filter
 *
 * `lf` is the local frame (can be fractional during sub-frame blur). Use lf/RM.fps for seconds.
 */
(function (g) {
  const RM = { fps: 30 };
  RM.scene = (f0, f1, fn, el) => MD.scene(f0 / RM.fps, (f1 + 1) / RM.fps,
    (lt, dur, p, t) => fn(lt * RM.fps, Math.round(dur * RM.fps), p, t * RM.fps), el);
  RM.F = (t) => t * RM.fps;
  RM.sec = (f) => f / RM.fps;
  /** Palette filter: snaps colours toward a small palette so the copy matches the reference's look.
   *  Implemented as an SVG feComponentTransfer posterize applied to #stage (cheap, deterministic). */
  RM.palette = function (levels = 6, el) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', 0); svg.setAttribute('height', 0); svg.style.position = 'absolute';
    const table = Array.from({ length: levels }, (_, i) => (i / (levels - 1)).toFixed(3)).join(' ');
    svg.innerHTML = `<filter id="rm-pal" color-interpolation-filters="sRGB"><feComponentTransfer>` +
      ['R', 'G', 'B'].map((c) => `<feFunc${c} type="discrete" tableValues="${table}"/>`).join('') +
      `</feComponentTransfer></filter>`;
    document.body.appendChild(svg);
    (el || document.getElementById('stage')).style.filter = 'url(#rm-pal)';
  };
  g.RM = RM;
})(window);
