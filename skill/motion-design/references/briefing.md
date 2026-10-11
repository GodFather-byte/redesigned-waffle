# Director's brief (write this BEFORE code)

1. **Reference style** — name one concrete look (e.g. "Linear changelog film", "Apple keynote kinetic type"), not "modern".
2. **Message** — one sentence the viewer should repeat.
3. **Beat map** — BPM, bars, the key frame (climax), every cut on a beat. `spb = 60/bpm`.
4. **Timed states** — per scene: start/end, what is on screen at start, at the hit, at the end, and the motion between.
5. **Layer list** — background, world (camera), UI cards, overlays (flood, grain), text.
6. **Sound plan** — music drop → key frame; one SFX per visual event, with its time.
7. **Truth check** — every claim/number traced to `facts.md` or labelled "Example data".

## Techniques borrowed from other public skills
GSAP/WAAPI scrubbing (engine does it); adaptive sub-frames (more sub-frames only where speed is high); cuts on the seam (hide a cut inside a flood or whip); burned-in captions as DOM text driven by `t`; frame 0 designed as the poster; B-roll laid over a narration track (place by transcript timestamps).
