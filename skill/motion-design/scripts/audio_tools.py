#!/usr/bin/env python3
"""audio_tools — beat-accurate music/SFX placement for generated motion-design films.

    python audio_tools.py drop  music.mp3                  # where is the real drop? (low-band energy)
    python audio_tools.py peak  sfx.wav                    # where is the SFX's measured peak?
    python audio_tools.py mix   plan.json out.wav          # place music + SFX by drop/peak, then loudnorm
    python audio_tools.py loudnorm in.wav out.wav [-14]    # two-pass loudnorm only

Rules baked in:
  * never trust an automatic beat grid — find the actual break from band energy;
  * start the music so its drop lands on the film's key visual moment;
  * place every SFX so its *measured peak* (not its file start) lands on the visual event;
  * finish with two-pass loudnorm to -14 LUFS (true peak -1.5 dB).

plan.json:
{ "duration": 24, "sr": 44100,
  "music": {"file": "m.mp3", "drop_at": 8.0, "gain_db": -6, "fade_out": 1.5, "drop_time": null},
  "sfx":   [{"file": "hit.wav", "at": 8.0, "gain_db": -3}, ...] }
`drop_time` overrides auto-detection if you verified it by ear / spectrogram.
"""
import json, os, re, subprocess, sys, tempfile, wave
import numpy as np

try:
    import imageio_ffmpeg
    FFMPEG = os.environ.get("FFMPEG") or imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = os.environ.get("FFMPEG", "ffmpeg")


def decode(path, sr=44100):
    """-> float32 array (n, 2)"""
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()


def write_wav(path, x, sr=44100):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def band_energy(x, sr, lo=20, hi=150, win=2048, hop=441):
    """RMS energy of one frequency band per hop (default 10 ms). Returns (times, energy)."""
    m = x.mean(axis=1)
    w = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    sel = (freqs >= lo) & (freqs <= hi)
    n = max(0, (len(m) - win) // hop)
    e = np.empty(n, dtype=np.float32)
    for i in range(n):
        s = np.abs(np.fft.rfft(m[i * hop:i * hop + win] * w))
        e[i] = np.sqrt(np.mean(s[sel] ** 2))
    return (np.arange(n) * hop + win / 2) / sr, e


def find_drop(x, sr, lo=20, hi=150, span=0.75):
    """Time (s) of the biggest sustained jump in low-band energy: mean(next span) - mean(prev span)."""
    t, e = band_energy(x, sr, lo, hi)
    if len(e) < 10:
        return 0.0
    k = int(span / 0.01)
    c = np.cumsum(np.concatenate([[0], e]))
    score = np.full(len(e), -np.inf)
    for i in range(k, len(e) - k):
        score[i] = (c[i + k] - c[i]) / k - (c[i] - c[i - k]) / k
    i = int(np.argmax(score))
    # refine: walk back to the onset (first hop where energy exceeds 30% of the post-drop level)
    level = 0.3 * float(np.mean(e[i:i + k]))
    while i > 0 and e[i - 1] > level:
        i -= 1
    return float(t[i])


def sfx_peak(x, sr, win=0.005):
    """Time (s) of the loudest instant (short-window RMS) — the moment to sync to the visual hit."""
    m = np.abs(x).max(axis=1)
    n = max(1, int(win * sr))
    env = np.sqrt(np.convolve(m ** 2, np.ones(n) / n, mode="same"))
    return float(np.argmax(env) / sr)


def db(g):
    return 10 ** (g / 20)


def loudnorm(inp, out, target=-14.0, tp=-1.5, lra=11):
    """Two-pass EBU R128 loudnorm. Returns measured input stats."""
    f = f"loudnorm=I={target}:TP={tp}:LRA={lra}"
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(inp), "-af", f + ":print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    f2 = (f"{f}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(inp), "-af", f2, "-ar", "44100", str(out)], check=True)
    return m


def mix(plan, out, base=None):
    sr = plan.get("sr", 44100)
    n = int(plan["duration"] * sr)
    bus = np.zeros((n, 2), dtype=np.float32)

    def place(sig, start_s, gain):
        s0 = int(round(start_s * sr))
        a, b = max(0, -s0), min(len(sig), n - s0)
        if b > a:
            bus[s0 + a:s0 + b] += sig[a:b] * gain

    mu = plan.get("music")
    if mu:
        x = decode(mu["file"], sr)
        d = mu.get("drop_time") or find_drop(x, sr)
        start = mu["drop_at"] - d
        print(f"music: drop at {d:.3f}s in file -> start offset {start:+.3f}s so it lands at {mu['drop_at']}s")
        fo = mu.get("fade_out", 0)
        if fo:
            end = int((plan["duration"] - start) * sr)
            x = x[:max(0, end)]
            k = min(len(x), int(fo * sr))
            x[len(x) - k:] *= np.linspace(1, 0, k)[:, None]
        place(x, start, db(mu.get("gain_db", -6)))

    for s in plan.get("sfx", []):
        x = decode(s["file"], sr)
        pk = s.get("peak_time") or sfx_peak(x, sr)
        place(x, s["at"] - pk, db(s.get("gain_db", -3)))
        print(f"sfx {os.path.basename(s['file'])}: peak {pk:.3f}s -> placed at {s['at'] - pk:+.3f}s (peak on {s['at']}s)")

    with tempfile.TemporaryDirectory() as td:
        raw = os.path.join(td, "raw.wav")
        write_wav(raw, bus, sr)
        m = loudnorm(raw, out, plan.get("lufs", -14.0))
    print(f"loudnorm: in {m['input_i']} LUFS / TP {m['input_tp']} dB -> {plan.get('lufs', -14.0)} LUFS; wrote {out}")


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 1
    c = argv[0]
    if c == "drop":
        x = decode(argv[1]); print(f"{find_drop(x, 44100):.3f}")
    elif c == "peak":
        x = decode(argv[1]); print(f"{sfx_peak(x, 44100):.4f}")
    elif c == "mix":
        mix(json.load(open(argv[1])), argv[2])
    elif c == "loudnorm":
        loudnorm(argv[1], argv[2], float(argv[3]) if len(argv) > 3 else -14.0)
    else:
        print(__doc__); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
