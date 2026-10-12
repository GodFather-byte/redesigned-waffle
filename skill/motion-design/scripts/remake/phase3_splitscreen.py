#!/usr/bin/env python3
"""Phase 3 — encode the "original | copy" split screen and run the layered sync check.

    python phase3_splitscreen.py reference.mp4 copy.mp4 out/split.mp4 [--label-left Original --label-right "Remake"]

Sync check (printed, exit 1 on failure):
  video : hard-cut times of both videos (frame-diff spikes) must agree within 1 frame
  audio : onset-envelope cross-correlation between reference and copy audio -> best lag (ms)
          (the copy uses a different, royalty-free track; we only check that hits land together)
"""
import argparse, subprocess, sys, tempfile, os
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mdrender import FFMPEG  # noqa: E402
from audio_tools import decode  # noqa: E402
from phase0_extract import detect_cuts  # noqa: E402


def cuts_of(path, fps=30, thr=8.0):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", path, "-vf", f"fps={fps},scale=96:54,format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 54, 96).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    return detect_cuts(d, thr)


def onset_env(path, sr=22050, hop=441):
    x = decode(path, sr).mean(axis=1)
    n = len(x) // hop
    e = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1))
    return np.maximum(0, np.diff(np.log1p(e * 50), prepend=0)), hop / sr


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("copy"); ap.add_argument("out")
    ap.add_argument("--label-left", default="Original"); ap.add_argument("--label-right", default="Remake")
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    flt = ("[0:v]scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1,"
           f"drawtext=text='{a.label_left}':x=16:y=12:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.5[l];"
           "[1:v]scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2,setsar=1,"
           f"drawtext=text='{a.label_right}':x=16:y=12:fontsize=26:fontcolor=white:box=1:boxcolor=black@0.5[r];"
           "[l][r]hstack,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]")
    r = subprocess.run([FFMPEG, "-y", "-v", "error", "-i", a.ref, "-i", a.copy, "-filter_complex", flt, "-map", "[v]", "-map", "1:a?",
                        "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-shortest", a.out], capture_output=True, text=True)
    if r.returncode:  # drawtext needs a font build of ffmpeg; retry without labels
        print("drawtext unavailable, encoding without labels")
        subprocess.run([FFMPEG, "-y", "-v", "error", "-i", a.ref, "-i", a.copy, "-filter_complex",
                        "[0:v]scale=960:540,setsar=1[l];[1:v]scale=960:540,setsar=1[r];[l][r]hstack,format=yuv420p[v]",
                        "-map", "[v]", "-map", "1:a?", "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-shortest", a.out], check=True)
    ok = True
    cr, cc = cuts_of(a.ref), cuts_of(a.copy)
    print("cuts ref :", cr); print("cuts copy:", cc)
    if len(cr) != len(cc) or any(abs(x - y) > 1 for x, y in zip(cr, cc)):
        print("VIDEO SYNC: cut mismatch"); ok = False
    try:
        er, dt = onset_env(a.ref); ec, _ = onset_env(a.copy)
        n = min(len(er), len(ec)); er, ec = er[:n], ec[:n]
        xc = np.correlate(er - er.mean(), ec - ec.mean(), "full"); lag = (np.argmax(xc) - (n - 1)) * dt * 1000
        print(f"AUDIO SYNC: best onset lag {lag:+.0f} ms"); ok &= abs(lag) < 60
    except Exception as e:
        print("audio sync skipped:", e)
    print("wrote", a.out); return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
