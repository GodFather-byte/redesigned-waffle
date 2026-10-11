#!/usr/bin/env python3
"""Thin wrapper around skill/motion-design/scripts/mdrender.py for this film.

    python render.py probe 1 8 15 20     # stills -> probe/*.png + probe/sheet.png
    python render.py draft               # fast 540p preview  -> out/video_draft.mp4
    python render.py full                # 24 s, 60 fps, 8 sub-frames -> out/video.mp4

Extra flags pass straight through (e.g. --fps 30 --subframes 4 --from 7 --to 9).
If nothing listens on localhost:8000 the script serves this folder itself.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "skill" / "motion-design" / "scripts"))
import mdrender  # noqa: E402

# serve the repo root so index.html can load ../../skill/motion-design/engine/*
ROOT = HERE.parent.parent
URL = "http://localhost:8000/examples/howseen-launch/index.html"

if __name__ == "__main__":
    argv = sys.argv[1:]
    defaults = ["--url", URL, "--root", str(ROOT), "--out", str(HERE / "out" / "video.mp4"),
                "--probe-dir", str(HERE / "probe")]
    sys.argv = [sys.argv[0]] + argv[:1] + defaults + argv[1:]
    mdrender.main()
