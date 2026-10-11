#!/usr/bin/env python3
"""mdrender — render a seek(t) page to video, frame by frame, with sub-frame motion blur.

    python mdrender.py probe  --url URL 1 8 15 20          # stills + contact sheet
    python mdrender.py draft  --url URL                     # fast 540p preview
    python mdrender.py full   --url URL --out out/video.mp4 # master

Pipeline per output frame n (time t = n/fps):
  1. for each of N sub-frames at t + (i/N) * shutter/fps:  seek(sub_t) -> 2 rAF -> screenshot
  2. average the N sub-frames (a 180-degree shutter => shutter = 0.5). Sub-frames that would
     straddle a hard cut (MD.cuts) are dropped, so a cut is never smeared into a cross-fade.
  3. pipe raw RGB into ffmpeg: BT.709 matrix, TV range, yuv420p, x264.

The page must expose window.seek(t), window.__mdReady, and (optionally) MD.duration / MD.cuts
(see engine/engine.js).
"""
import argparse, bisect, contextlib, glob, http.server, os, socket, socketserver, subprocess, sys, threading
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import imageio_ffmpeg
    FFMPEG = os.environ.get("FFMPEG") or imageio_ffmpeg.get_ffmpeg_exe()
except Exception:  # fall back to PATH
    FFMPEG = os.environ.get("FFMPEG", "ffmpeg")

SWIFTSHADER = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]


# ---------------------------------------------------------------- helpers
def _port_open(host, port):
    with contextlib.closing(socket.socket()) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0


@contextlib.contextmanager
def ensure_server(url, root):
    """If `url` points at localhost and nothing listens there, serve `root` for the duration."""
    from urllib.parse import urlparse
    u = urlparse(url)
    if u.scheme != "http" or u.hostname not in ("localhost", "127.0.0.1") or _port_open(u.hostname, u.port or 80):
        yield
        return

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(root), **k)

        def log_message(self, *a):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", u.port or 80), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"[mdrender] serving {root} on {u.hostname}:{u.port}")
    try:
        yield
    finally:
        srv.shutdown()


def _chromium_path():
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome", "/opt/pw-browsers/chromium/chrome-linux/chrome"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


class Page:
    """Playwright page wrapper: fonts ready, animations paused by the engine, 2 rAF after each seek."""

    def __init__(self, pw, url, width, height, scale, webgl):
        args = list(SWIFTSHADER) if webgl else []
        try:
            self.browser = pw.chromium.launch(args=args)
        except Exception:
            exe = _chromium_path()
            if not exe:
                raise
            self.browser = pw.chromium.launch(executable_path=exe, args=args)
        self.ctx = self.browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale)
        self.page = self.ctx.new_page()
        self.page.on("pageerror", lambda e: print("[page error]", e, file=sys.stderr))
        self.page.goto(url, wait_until="load")
        self.page.wait_for_function("window.__mdReady === true", timeout=60000)
        self.page.evaluate("document.fonts.ready")
        self.duration = self.page.evaluate("(window.MD && MD.duration) || 0")
        self.cuts = sorted(self.page.evaluate("(window.MD && MD.cuts) || []"))
        self.clip = {"x": 0, "y": 0, "width": width, "height": height}

    def shot(self, t, fmt="png"):
        self.page.evaluate(
            "t => new Promise(r => { window.seek(t); requestAnimationFrame(() => requestAnimationFrame(r)); })", t
        )
        kw = {"type": "jpeg", "quality": 88} if fmt == "jpeg" else {"type": "png"}
        return Image.open(__import__("io").BytesIO(self.page.screenshot(clip=self.clip, **kw))).convert("RGB")

    def close(self):
        self.browser.close()


def subframe_times(n, fps, sub, shutter, cuts):
    """Sub-frame times for output frame n; those at/after the next hard cut are dropped."""
    t0 = n / fps
    ts = [t0 + (i / sub) * (shutter / fps) for i in range(sub)]
    i = bisect.bisect_right(cuts, t0 + 1e-9)  # first cut strictly after t0
    if i < len(cuts):
        ts = [t for t in ts if t < cuts[i] - 1e-9] or [t0]
    return ts


def ffmpeg_cmd(w, h, fps, out, crf, preset):
    return [
        FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
        "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=accurate_rnd+full_chroma_int,format=yuv420p",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart", str(out),
    ]


# ---------------------------------------------------------------- commands
def cmd_probe(a):
    from playwright.sync_api import sync_playwright
    outdir = Path(a.probe_dir); outdir.mkdir(parents=True, exist_ok=True)
    with ensure_server(a.url, a.root), sync_playwright() as pw:
        pg = Page(pw, a.url, a.width, a.height, 1, a.webgl)
        imgs = []
        for t in a.times:
            im = pg.shot(t); p = outdir / f"t{t:07.3f}.png"; im.save(p); imgs.append((t, im)); print("wrote", p)
        pg.close()
    # contact sheet, 2 columns
    from PIL import ImageDraw
    tw = 640; th = int(tw * a.height / a.width); cols = 2; rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (20, 20, 20))
    for k, (t, im) in enumerate(imgs):
        s = im.resize((tw, th), Image.LANCZOS); ImageDraw.Draw(s).text((8, 6), f"t={t:g}s", fill=(255, 255, 0))
        sheet.paste(s, ((k % cols) * tw, (k // cols) * th))
    sheet.save(outdir / "sheet.png"); print("wrote", outdir / "sheet.png")


def render(a, draft):
    from playwright.sync_api import sync_playwright
    scale = 0.5 if draft else 1
    w, h = int(a.width * scale), int(a.height * scale)
    fps = a.draft_fps if draft else a.fps
    sub = 1 if draft else a.subframes
    out = Path(a.out if not draft else a.out.replace(".mp4", "_draft.mp4")); out.parent.mkdir(parents=True, exist_ok=True)
    with ensure_server(a.url, a.root), sync_playwright() as pw:
        pg = Page(pw, a.url, a.width, a.height, scale, a.webgl)
        dur = a.duration or pg.duration
        if not dur:
            sys.exit("no duration: pass --duration or set MD.duration in the page")
        t_from, t_to = a.t_from or 0, a.t_to or dur
        n0, n1 = int(round(t_from * fps)), int(round(t_to * fps))
        proc = subprocess.Popen(ffmpeg_cmd(w, h, fps, out, a.crf if not draft else 23, "veryfast" if draft else a.preset),
                                stdin=subprocess.PIPE)
        fmt = "jpeg" if draft else "png"
        print(f"[mdrender] {'draft' if draft else 'full'} {w}x{h} @{fps}fps, {sub} subframes, cuts={pg.cuts}, frames {n0}..{n1-1}")
        for n in range(n0, n1):
            ts = subframe_times(n, fps, sub, a.shutter, pg.cuts)
            acc = None
            for t in ts:
                arr = np.asarray(pg.shot(t, fmt), dtype=np.float32)
                acc = arr if acc is None else acc + arr
            frame = np.clip(acc / len(ts) + 0.5, 0, 255).astype(np.uint8)
            proc.stdin.write(frame.tobytes())
            if n % 30 == 0:
                print(f"\r[mdrender] frame {n - n0 + 1}/{n1 - n0}", end="", flush=True)
        proc.stdin.close(); proc.wait(); pg.close()
    print(f"\n[mdrender] wrote {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["probe", "draft", "full"])
    p.add_argument("times", nargs="*", type=float, help="probe: seconds to capture")
    p.add_argument("--url", default="http://localhost:8000/index.html")
    p.add_argument("--root", default=".", help="directory to serve if --url is localhost and not running")
    p.add_argument("--width", type=int, default=1920)
    p.add_argument("--height", type=int, default=1080)
    p.add_argument("--fps", type=int, default=60)
    p.add_argument("--draft-fps", type=int, default=30)
    p.add_argument("--duration", type=float, default=0)
    p.add_argument("--from", dest="t_from", type=float, default=0)
    p.add_argument("--to", dest="t_to", type=float, default=0)
    p.add_argument("--subframes", type=int, default=8, help="sub-frames per frame (motion blur quality)")
    p.add_argument("--shutter", type=float, default=0.5, help="0.5 = 180-degree shutter")
    p.add_argument("--crf", type=int, default=16)
    p.add_argument("--preset", default="slow")
    p.add_argument("--out", default="out/video.mp4")
    p.add_argument("--probe-dir", default="probe")
    p.add_argument("--webgl", action="store_true", default=os.environ.get("WEBGL") == "1", help="SwiftShader flags (or WEBGL=1)")
    a = p.parse_intermixed_args()
    if a.mode == "probe":
        if not a.times: p.error("probe needs at least one time")
        cmd_probe(a)
    else:
        render(a, draft=a.mode == "draft")


if __name__ == "__main__":
    main()
