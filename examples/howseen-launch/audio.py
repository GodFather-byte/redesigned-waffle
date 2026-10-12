#!/usr/bin/env python3
"""Build out/audio.wav for the film: music + SFX placed by measured peak, -14 LUFS.

    python fetch_assets.py   # optional: real free music/SFX (Mixkit). Not redistributed here.
    python audio.py          # -> out/audio.wav

If assets/music.* or assets/sfx/*.wav are missing, this script synthesises a 120 BPM placeholder
track (quiet riser, then kick+bass at its own 4.0 s "drop") and placeholder SFX, so the whole
pipeline — drop detection, peak placement, loudnorm — works with zero downloads.
The music's *real* drop is detected from low-band energy and aligned to the film's key frame (8.0 s).
"""
import glob, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "skill" / "motion-design" / "scripts"))
import audio_tools as at  # noqa: E402

SR = 44100
DROP_AT = 8.0          # film's key moment: the colour flood finishes, dashboard appears
DURATION = 24.0
ASSETS = HERE / "assets"
SYN = ASSETS / "synth"
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(d * SR)) / SR


def stereo(m):
    return np.stack([m, m], axis=1).astype(np.float32)


def lp(x, a):  # one-pole low-pass
    y = np.empty_like(x); s = 0.0
    for i, v in enumerate(x):
        s += a * (v - s); y[i] = s
    return y


# ---------------------------------------------------------------- synthesised placeholders
def synth_music(path, length=28.0, drop=4.0, bpm=120):
    t = t_(length); spb = 60 / bpm
    pad = sum(np.sin(2 * np.pi * f * t) * 0.05 for f in (261.6, 329.6, 392.0))          # no low end before the drop
    riser = np.sin(2 * np.pi * (400 + 800 * np.clip(t / drop, 0, 1) ** 2) * t) * 0.03 * np.clip(t / drop, 0, 1)
    m = pad + riser
    kick = np.zeros_like(t); bass = np.zeros_like(t); hat = np.zeros_like(t)
    for b in range(int((length - drop) / spb)):
        s = drop + b * spb; i = int(s * SR)
        n = min(int(0.35 * SR), len(t) - i)
        if n <= 0: break
        tk = np.arange(n) / SR
        kick[i:i + n] += np.sin(2 * np.pi * (45 + 90 * np.exp(-tk * 28)) * tk) * np.exp(-tk * 9) * 0.9
        hat_i = i + int(spb / 2 * SR); hn = min(int(0.05 * SR), len(t) - hat_i)
        if hn > 0: hat[hat_i:hat_i + hn] += rng.normal(0, 1, hn) * np.exp(-np.arange(hn) / SR * 90) * 0.06
    root = [55.0, 55.0, 65.4, 49.0]
    for b in range(int((length - drop) / (spb * 4)) + 1):
        i0 = int((drop + b * spb * 4) * SR); n = min(int(spb * 4 * SR), len(t) - i0)
        if n > 0:
            tb = np.arange(n) / SR
            bass[i0:i0 + n] += np.sin(2 * np.pi * root[b % 4] * tb) * 0.35 * (0.6 + 0.4 * np.exp(-(tb % spb) * 3))
    m = m + kick + bass + hat
    at.write_wav(path, stereo(m / max(1e-6, np.abs(m).max()) * 0.9), SR)


def env(n, a, d):  # attack/decay envelope, peak at `a` seconds
    tt = np.arange(n) / SR
    return np.where(tt < a, tt / a, np.exp(-(tt - a) / d))


def synth_sfx():
    SYN.mkdir(parents=True, exist_ok=True)
    out = {}
    # whoosh: band-passed noise swell, peak ~0.45 s into the file
    n = int(0.9 * SR); tt = np.arange(n) / SR
    w = lp(rng.normal(0, 1, n), 0.25) - lp(rng.normal(0, 1, n), 0.02)
    out["whoosh"] = w * env(n, 0.45, 0.12) * 0.9
    # impact: sub thump + noise burst, peak 0.06 s in
    n = int(1.4 * SR); tt = np.arange(n) / SR
    out["impact"] = (np.sin(2 * np.pi * (38 + 60 * np.exp(-tt * 14)) * tt) * 1.0 + lp(rng.normal(0, 1, n), 0.3) * 0.5) * env(n, 0.06, 0.25)
    # pop: short blip, peak 0.02 s in
    n = int(0.25 * SR); tt = np.arange(n) / SR
    out["pop"] = np.sin(2 * np.pi * (900 - 500 * tt * 4) * tt) * env(n, 0.02, 0.05)
    # tick: tiny click for text
    n = int(0.12 * SR); out["tick"] = lp(rng.normal(0, 1, n), 0.5) * env(n, 0.004, 0.015)
    # shimmer: bell-ish cluster, peak 0.03 s in
    n = int(1.6 * SR); tt = np.arange(n) / SR
    out["shimmer"] = sum(np.sin(2 * np.pi * f * tt) * a for f, a in ((1568, .5), (2093, .35), (2637, .25), (3136, .18))) * env(n, 0.03, 0.5)
    for k, v in out.items():
        v = v / max(1e-6, np.abs(v).max()) * 0.9
        at.write_wav(SYN / f"{k}.wav", stereo(v), SR)
        out[k] = str(SYN / f"{k}.wav")
    return out


def main():
    ASSETS.mkdir(exist_ok=True); (HERE / "out").mkdir(exist_ok=True)
    music = next(iter(sorted(glob.glob(str(ASSETS / "music.*")))), None)
    if not music:
        music = str(SYN / "music.wav"); SYN.mkdir(parents=True, exist_ok=True)
        print("no assets/music.* -> synthesising placeholder music")
        synth_music(music)
    sfx = {k: str(p) for k in ("whoosh", "impact", "pop", "tick", "shimmer")
           if (p := ASSETS / "sfx" / f"{k}.wav").exists()}
    if len(sfx) < 5:
        print("missing assets/sfx/*.wav -> synthesising placeholder SFX")
        sfx = {**synth_sfx(), **sfx}

    ev = []                                                    # (sfx, visual-event time in the film, gain dB)
    for c in (3.0, 14.0, 19.0): ev.append(("whoosh", c, -6))                # hard cuts
    ev.append(("whoosh", 7.55, -9))                                         # flood sweeping in
    ev.append(("impact", 8.0, -2))                                          # flood completes = the drop
    for i in range(3): ev.append(("pop", 5.55 + i * 0.14, -10))             # "not mentioned" badges
    for t in (8.05, 8.19): ev.append(("pop", t, -12))                       # dashboard cards
    for i in range(3):                                                      # beams arriving at each engine, 2 cycles
        for cyc in (0, 2.0): ev.append(("shimmer", 14.8 + 1.3 + i * 0.25 + cyc - 0.0, -14))
    ev.append(("pop", 20.0, -8))                                            # logo dot lands
    ev.append(("shimmer", 20.9, -10))                                       # wordmark settles
    for k in range(7): ev.append(("tick", 3.6 + k * 0.1, -22))              # typing ticks

    plan = {"duration": DURATION, "sr": SR, "lufs": -14.0,
            "music": {"file": music, "drop_at": DROP_AT, "gain_db": -8, "fade_out": 1.5},
            "sfx": [{"file": sfx[n], "at": t, "gain_db": g} for n, t, g in ev]}
    at.mix(plan, str(HERE / "out" / "audio.wav"))


if __name__ == "__main__":
    main()
