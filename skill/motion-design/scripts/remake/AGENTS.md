# Phase 2 agent prompts

## Build agent (×4, one per scene group)
You own scenes {IDS} of `work/spec.json` (frames {RANGE}). Read `work/sheets/scene_XX.jpg` and the full frames in
`work/frames/`. Build your scenes in the shared page using `RM.scene(startFrame, endFrame, fn, selector)` — nothing but
`seek`-driven code (no CSS transitions, timers or Date.now). Rules: closed-form springs, log-space camera, masked word reveals,
palette from the brand folder. Loop: render stills at your keyframes (`mdrender.py probe`), make a side-by-side sheet
(reference frame | your frame), fix the biggest difference, repeat until layout, colour and motion phase match.
Do not touch other agents' scenes or the shared engine. Report: scenes done, residual differences.

## Audio agent (×1)
Pick a royalty-free track (never the reference's). Detect its real drop (`audio_tools.py drop`), time-stretch to the reference BPM,
align the drop to the reference's key frame. Synthesise/pick SFX for each reference hit (list the hit times from the reference
waveform), place them by measured peak with `audio_tools.py mix`, loudnorm to -14 LUFS. Never reuse reference audio.
