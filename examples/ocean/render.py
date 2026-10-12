#!/usr/bin/env python3
"""python render.py probe 0 3 6 9 | draft | full  (WebGL via SwiftShader is forced on; extra flags pass through)"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "skill" / "motion-design" / "scripts"))
import mdrender  # noqa: E402
if __name__ == "__main__":
    a = sys.argv[1:]
    d = ["--url", "http://localhost:8000/examples/ocean/index.html", "--root", str(HERE.parent.parent), "--webgl",
         "--width", "1280", "--height", "720", "--out", str(HERE / "out" / "ocean.mp4"), "--probe-dir", str(HERE / "probe")]
    sys.argv = [sys.argv[0]] + a[:1] + d + a[1:]
    mdrender.main()
