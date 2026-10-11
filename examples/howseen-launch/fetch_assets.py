#!/usr/bin/env python3
"""Download the free music, SFX, logos and font for this film into ./assets (not redistributed here).
See assets.json for sources/licences. The film and audio.py also work WITHOUT this step
(system font fallback, text-only chips, synthesised music/SFX)."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "skill" / "motion-design" / "scripts"))
import fetch_assets  # noqa: E402
sys.exit(fetch_assets.main(str(HERE / "assets.json"), str(HERE / "assets")))
