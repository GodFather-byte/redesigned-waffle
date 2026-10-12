---
name: motion-design
description: Make motion-design / launch / explainer videos with code only — HTML + Playwright + ffmpeg. Use when the user asks for a product launch video, animated explainer, social loop, kinetic typography, UI-transformation reveal, or a 1:1 remake of their own brand video. Every frame is a pure function of time (seek(t)), rendered frame by frame with sub-frame motion blur, cut on the beat, SFX placed by measured peak.
---

# motion-design

Deterministic motion design as code. No After Effects, no Remotion licence, no editor.
The whole film is one `seek(t)` function: same input → same frames, always.

## Flow (do not skip steps)

1. **Inputs** — brand folder (logos, colours, fonts), `facts.md` (the only source of on-screen claims), size/fps/duration, music preference. Missing → ask once, otherwise pick sensible defaults and say so.
2. **Director's brief before any code** (`references/briefing.md`): named reference style, timed states per scene, layer list, sound plan. Anti "AI motion" rules below apply.
3. **Beat map** — BPM, key frame (the visual climax), cut times on beats. Put them in `MD.beats`, `MD.cuts`.
4. **Build** the page on `engine/engine.js` + `engine.css` (copy next to the film or reference by relative path). Scenes via `MD.scene(start, end, fn, selector)`.
5. **4 approved stills** — `python scripts/mdrender.py probe t1 t2 t3 t4` → `probe/sheet.png`. Look at it. Fix. Only then continue.
6. **Draft** — `mdrender.py draft` (540p, 30 fps, no blur). Check pacing; run `scripts/qc.py`.
7. **Full render** — `mdrender.py full` (60 fps, 8 sub-frames, 180° shutter, BT.709 TV range). It is slow: ~0.3 s per capture at 1080p, so 24 s × 60 fps × 8 ≈ 1 h on a laptop. Use `--fps 30 --subframes 4` for review masters, `--from/--to` to re-render only the scene you fixed.
8. **Sound analysis → audio** — `audio_tools.py drop music.mp3` finds the real break (low-band energy; never trust an automatic beat grid); start the music so the break hits the key frame; place each SFX so its **measured peak** lands on the visual event (`audio_tools.py mix plan.json out.wav`); two-pass loudnorm to −14 LUFS.
9. **Mux & final QC** — `ffmpeg -i video.mp4 -i audio.wav -map 0:v -map 1:a -c:v copy -c:a aac -shortest final.mp4`; `qc.py final.mp4 --cuts … [--loop]`.

## Engine rules (`references/engine.md` has the API)

- **Only `seek(t)`**: no CSS transitions/animations, no timers, no rAF-driven state, no `Date.now()`. The engine pauses WAAPI/SMIL/GSAP and scrubs them to `t`; CSS animations are disabled by `engine.css`.
- **Closed-form springs** (`MD.spring`), not simulation steps — evaluable at any `t`, so sub-frames are exact.
- **One camera**, keyed in **log-space** zoom (`MD.camera`) so zooms feel constant-speed.
- **Shared-element handoffs** (`MD.fly`): an element in scene A becomes the element in scene B instead of cutting.
- **Colour floods** (`MD.flood`) grow until the *farthest* corner is covered — land exactly on the beat.
- **Masked word-by-word text** (`MD.revealWords`), never fade-ins of whole paragraphs.
- 21st.dev adaptations driven by `seek(t)`: Animated Beam (`MD.beam`), Border Beam (`MD.borderBeam` + `.md-border-beam`).
- Hard cuts go in `MD.cuts`: motion blur is never mixed across them. A flood/transition that is *animated* is not a cut.

## Anti-"AI motion" rules

No default ease-in-out on everything; vary durations (0.25–0.9 s), stagger by 40–90 ms; overshoot only on springs that earn it; one hero motion per beat; hold still frames (0.4 s of nothing reads as confidence); no gratuitous gradients/glow/particles; text ≥ 44 px at 1080p; every move has a reason tied to the message.

## Render details

Playwright screenshots (fonts ready, animations paused, 2 rAF after each `seek`), sub-frames averaged in numpy (equivalent to ffmpeg `tmix`, but lets cut frames drop post-cut sub-frames), encoded `libx264`, `-colorspace/-color_primaries/-color_trc bt709`, `-color_range tv`, `yuv420p`. WebGL pages: `WEBGL=1` adds SwiftShader flags. Do not run `playwright install` if Chromium already exists (`PLAYWRIGHT_BROWSERS_PATH`).

## Honesty rules

Illustrative data is labelled **"Example data"** on screen. Captions stay true. No fabricated customers, logos-as-endorsement, metrics or testimonials. Brand logos are used to *identify* engines/tools, not to imply partnership.

## Assets (free only)

Music/SFX/video: Mixkit. Photos/video: Pexels, Unsplash. Logos: SVGL. Icons: Simple Icons. Font: Geist (OFL). `scripts/fetch_assets.py MANIFEST DEST` downloads from a manifest; never commit downloaded media.

## Also in this skill

- `references/engine.md` — API cheatsheet and patterns
- `references/briefing.md` — director's brief template + borrowed techniques
- `references/prompts.md` — prompt library (single scene, brand film, UI transformation, launch reveal, LinkedIn loop)
- `references/troubleshooting.md` — symptom → fix table
- `scripts/remake/` — **Remake mode**: 1:1 frame-accurate remake of the user's own reference video, split-screen "original | copy" (see its README). Never reuse the reference's music, voice or photos of people.
- `examples/howseen-launch` (repo root) — complete 24 s film using all of the above.
