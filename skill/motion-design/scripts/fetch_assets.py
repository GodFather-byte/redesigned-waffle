#!/usr/bin/env python3
"""fetch_assets — download free assets listed in a manifest (never redistributed in the repo).

    python fetch_assets.py MANIFEST.json DEST_DIR

Manifest: {"items": [{"path": "sfx/pop.wav", "url": "https://...", "licence": "..."}]}
Items with "url": null are skipped with a hint. Files that already exist are kept.
Sources used by the skill (all free): Mixkit (music/SFX/video), Pexels & Unsplash (photos/video),
SVGL (brand logos), Simple Icons (monochrome icons), Geist (OFL font).
Respect each licence; brand logos stay the property of their owners.
"""
import json, os, sys, urllib.request
from pathlib import Path


def main(manifest, dest):
    items = json.load(open(manifest))["items"]
    dest = Path(dest); ok = fail = skip = 0
    for it in items:
        p = dest / it["path"]
        if p.exists():
            print("have   ", it["path"]); ok += 1; continue
        if not it.get("url"):
            print("SKIP   ", it["path"], "- no url;", it.get("hint", "fill it in the manifest")); skip += 1; continue
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            req = urllib.request.Request(it["url"], headers={"User-Agent": "Mozilla/5.0 motion-design"})
            with urllib.request.urlopen(req, timeout=60) as r, open(p, "wb") as f:
                f.write(r.read())
            print("fetched", it["path"], f"({it.get('licence', '?')})"); ok += 1
        except Exception as e:
            print("FAILED ", it["path"], "-", e); fail += 1
    print(f"\n{ok} ok, {skip} skipped, {fail} failed. Missing music/SFX fall back to synthesised placeholders in audio.py.")
    return 1 if fail else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
