# Remake mode — 1:1 frame-accurate remake of a launch video from *your own* brand

Rights first: only remake videos you own or have permission to. **Never reuse the reference's music,
voice-over or photos of people** — the copy gets a royalty-free track and synthesised/free SFX.

## Phases

| Phase | What | How |
|---|---|---|
| 0 | Dissect the reference | `python phase0_extract.py ref.mp4 work/` → every frame, cuts, per-scene contact sheets, `spec.json` |
| 1 | Shared engine | one HTML page using `engine/engine.js` + `remake_engine.js`: scenes are registered in **reference frame numbers**; optional palette filter (`RM.palette`) |
| 2 | Build (parallel) | 4 build agents (one scene group each) + 1 audio agent — prompts in `AGENTS.md`. Each build agent renders stills of its frames and checks a **side-by-side sheet against the reference frame** before reporting |
| 3 | Render + verify | `python mdrender.py full …`, then `python phase3_splitscreen.py ref.mp4 copy.mp4 out/split.mp4` → "original \| copy" split screen + layered sync check (cut times, audio onset lag) |

`BRIEFING_TEMPLATE.md` is the brief to fill in before Phase 0 (brand folder, facts, what must not be copied).

## Audio agent
Royalty-free track time-stretched to the reference BPM (`ffmpeg -af atempo=…`, chain for >2x), beat grid
**verified from band energy** (`audio_tools.py drop`), SFX synthesised/free and placed at the reference's hit
times by measured peak (`audio_tools.py mix`).
