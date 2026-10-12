#!/usr/bin/env python3
"""qc — automatic checks on a rendered video.

    python qc.py video.mp4 [--cuts 3 14 19] [--loop]

  pops / flashes : a frame that differs a lot from BOTH neighbours while the neighbours match each
                   other (A B A pattern) = a one-frame flash; a lone huge jump that is not a declared
                   cut = a pop (an element snapping into place).
  loop seam      : with --loop, compares the wrap-around step (last -> first) with a typical step.
                   Position seam = the wrap step should look like any other step (ratio ~ 1);
                   velocity seam = the step *into* the end and *out of* the start should match.

Works on 160x90 grayscale copies, so it takes a few seconds. Exit code 1 if anything is flagged.
"""
import argparse, subprocess, sys
import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__file__))
from mdrender import FFMPEG  # noqa: E402


def load_gray(path, w=160, h=90):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def fps_of(path):
    out = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True).stderr
    import re
    m = re.search(r"(\d+(?:\.\d+)?) fps", out)
    return float(m.group(1)) if m else 30.0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video")
    ap.add_argument("--cuts", type=float, nargs="*", default=[]); ap.add_argument("--loop", action="store_true")
    ap.add_argument("--pop-factor", type=float, default=6.0)
    a = ap.parse_args()
    f = load_gray(a.video); fps = fps_of(a.video); n = len(f)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))           # d[i] = |f[i+1]-f[i]|
    cut_frames = {int(round(c * fps)) - 1 for c in a.cuts}      # d index of the step across each cut
    med = np.median(d) + 1e-3
    bad = []
    for i in range(1, len(d) - 1):
        ref = max(np.median(d[max(0, i - 8):i + 9]), 0.05)
        # flash: f[i] vs f[i-1] and f[i+1] large, but f[i+1] ~ f[i-1]
        skip = any(abs(i - c) <= 1 for c in cut_frames)
        if not skip and d[i - 1] > a.pop_factor * ref and d[i] > a.pop_factor * ref:
            if np.abs(f[i + 1] - f[i - 1]).mean() < 0.25 * min(d[i - 1], d[i]):
                bad.append((i, "flash", d[i]))
        elif i not in cut_frames and d[i] > a.pop_factor * 2 * ref and d[i] > 6.0:
            bad.append((i + 1, "pop", d[i]))
    for i, kind, v in bad:
        print(f"{kind.upper():5s} at frame {i} (t={i / fps:.3f}s): step {v:.2f} vs median {med:.2f}")
    if not bad:
        print(f"no pops/flashes in {n} frames (median step {med:.2f})")
    code = 1 if bad else 0
    if a.loop:
        seam = np.abs(f[0] - f[-1]).mean()
        v_end, v_start = d[-1], d[0]
        print(f"loop: wrap step {seam:.2f} vs median step {med:.2f} (ratio {seam / med:.2f}); "
              f"velocity end {v_end:.2f} / start {v_start:.2f}")
        if seam > 3 * med + 1 or abs(v_end - v_start) > 2 * med + 1:
            print("LOOP SEAM visible — make end state == start state in position AND velocity"); code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
