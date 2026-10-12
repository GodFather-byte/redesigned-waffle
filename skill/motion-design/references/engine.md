# Engine cheatsheet (`engine/engine.js`)

```html
<link rel="stylesheet" href="…/engine/engine.css"><div id="stage">…</div>
<script src="…/engine/engine.js"></script>
<script>
  MD.duration = 24; MD.cuts = [3, 14]; MD.beats = {bpm: 120, offset: 0};
  MD.scene(0, 3, (lt, dur, p, t) => { /* lt = local seconds, p = 0..1 */ }, '#sA');   // shows #sA only in [0,3)
  MD.ready();                                                                           // fonts+images, seek(0), window.__mdReady
</script>
```

| Need | Call |
|---|---|
| clamp / lerp / progress / remap | `MD.clamp, MD.lerp, MD.prog(t,a,b), MD.map(v,a,b,c,d,ease)` |
| easings | `MD.ease.outCubic / inOutQuint / outExpo / outBack / bezier(x1,y1,x2,y2)` |
| spring 0→1 | `MD.spring(t - t0, {k:170, c:18, m:1})` (under/critical/over-damped, closed form) |
| camera | `const cam = MD.camera([{t,x,y,z},…]); MD.applyCamera(worldEl, cam(t), W, H)` |
| word reveal | `MD.revealWords(el, t, {start, stagger, spring})` |
| typing | `MD.typed(str, t, start, cps)` |
| colour flood | `MD.flood(el, ox, oy, p, W, H)` — clip circle that reaches the farthest corner at p=1 |
| shared element | `MD.fly(el, rectA, rectB, p)` (`MD.rect(el)` measures layout; clear `transform` first) |
| animated beam | `MD.beam(pulsePath, t, {start,dur,len})` |
| border beam | `MD.borderBeam(el, t, period)` + class `md-border-beam`, colour via `--md-beam` |
| count-up | `MD.count(t,a,b,from,to)` |
| beat pulse / snap | `MD.pulse(t)`, `MD.snap(t)` |
| deterministic random | `MD.rand(seed)()` |
| GSAP | build a paused timeline, set `MD.gsapTimeline = tl`; the engine calls `tl.time(t, false)` |

Patterns: make end state of scene A == start state of B (or hide with same-colour flood) to avoid pops; keep per-frame code idempotent (set absolute values from `t`, never accumulate); measure layout with a cleared transform; put animated colours in CSS vars you set from JS.
