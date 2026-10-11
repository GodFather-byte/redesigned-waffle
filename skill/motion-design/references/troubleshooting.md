# Symptom → fix

| Symptom | Cause | Fix |
|---|---|---|
| Text in wrong font on frame 0 | fonts not loaded | `MD.ready()` awaits `document.fonts.ready`; add `@font-face`; renderer waits for `__mdReady` |
| Something moves on its own / mismatched frames | CSS transition/animation or timer | remove; engine.css disables them; WAAPI/SMIL are scrubbed in `seek` |
| One-frame white flash | element toggled `display` without bg, or flood ≠ next bg | match colours; run `qc.py` |
| Pop at scene change | state mismatch at the boundary | make end == start state, or hide in a flood/whip |
| Smeared cut | motion blur across a hard cut | list it in `MD.cuts` |
| Banding / washed colours in player | wrong range/matrix | keep the BT.709 TV-range encode flags |
| Loop jumps | position or velocity mismatch | `qc.py --loop`; ease to rest at both ends |
| Everything looks "AI" | default ease on all, same durations | vary durations, stagger, hold still frames |
| SFX feels late | file start placed at event | `audio_tools.py` places by measured peak |
| Music drop misses key frame | trusted a beat grid | `audio_tools.py drop` and re-offset |
| WebGL/3D black | no GPU | `WEBGL=1` (SwiftShader) |
| Render far too slow | 60 fps × many sub-frames | `--fps 30 --subframes 4`, `--from/--to`, draft first |
| `playwright install` re-downloads | env already has Chromium | don't; set `PLAYWRIGHT_BROWSERS_PATH` |
