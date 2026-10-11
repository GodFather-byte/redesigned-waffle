#!/usr/bin/env python3
"""Phase 0 — dissect a reference video into a frame-accurate spec.

    python phase0_extract.py reference.mp4 work/ [--fps 30] [--cut-threshold 8]

Writes:
  work/frames/f%05d.jpg      every frame (640 px wide) — the ground truth to compare against
  work/spec.json             {fps, frames, duration, cuts:[frame..], scenes:[{id,start,end,keyframes:[..]}]}
  work/sheets/scene_XX.jpg   contact sheet per scene (start, 25/50/75 %, end) for the build agents
  work/ref_audio.wav         reference audio (analysis only — NEVER reuse it in the copy)
A cut = an isolated spike in frame-to-frame difference (> --cut-threshold and > 2.5x both neighbouring
steps), so fast motion inside a scene is not mistaken for a cut.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mdrender import FFMPEG  # noqa: E402


def detect_cuts(d, thr=8.0):
    """d[i] = mean abs diff between frame i and i+1. A cut is an *isolated* spike: above `thr` and
    far above both neighbouring steps (so fast motion / colour floods inside a shot are not cuts)."""
    out = []
    for i, v in enumerate(d):
        nb = max(d[i - 1] if i > 0 else 0, d[i + 1] if i + 1 < len(d) else 0)
        if v > thr and v > 2.5 * nb:
            out.append(i + 1)                         # frame index where the new shot starts
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("work")
    ap.add_argument("--fps", type=float, default=30); ap.add_argument("--cut-threshold", type=float, default=8.0)
    a = ap.parse_args()
    work = Path(a.work); (work / "frames").mkdir(parents=True, exist_ok=True); (work / "sheets").mkdir(exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", a.video, "-vf", f"fps={a.fps},scale=640:-2", "-q:v", "3",
                    str(work / "frames" / "f%05d.jpg")], check=True)
    subprocess.run([FFMPEG, "-y", "-v", "error", "-i", a.video, "-vn", "-ac", "2", "-ar", "44100", str(work / "ref_audio.wav")])
    files = sorted((work / "frames").glob("f*.jpg"))
    g = [np.asarray(Image.open(p).convert("L").resize((96, 54)), dtype=np.float32) for p in files]
    d = np.array([np.abs(g[i] - g[i - 1]).mean() for i in range(1, len(g))])
    cuts = detect_cuts(d, a.cut_threshold)
    bounds = [0] + cuts + [len(files)]
    scenes = []
    for k in range(len(bounds) - 1):
        s, e = bounds[k], bounds[k + 1] - 1
        kf = sorted({s, s + (e - s) // 4, s + (e - s) // 2, s + 3 * (e - s) // 4, e})
        scenes.append({"id": k + 1, "start": s, "end": e, "keyframes": kf})
        ims = [Image.open(files[i]).convert("RGB") for i in kf]
        w, h = ims[0].size; sheet = Image.new("RGB", (w * len(ims), h))
        for j, (im, i) in enumerate(zip(ims, kf)):
            sheet.paste(im, (j * w, 0)); ImageDraw.Draw(sheet).text((j * w + 6, 6), f"F{i}", fill=(255, 255, 0))
        sheet.save(work / "sheets" / f"scene_{k + 1:02d}.jpg", quality=88)
    spec = {"fps": a.fps, "frames": len(files), "duration": len(files) / a.fps, "cuts": cuts, "scenes": scenes}
    (work / "spec.json").write_text(json.dumps(spec, indent=1))
    print(f"{len(files)} frames, {len(scenes)} scenes, cuts at frames {cuts}")


if __name__ == "__main__":
    main()
