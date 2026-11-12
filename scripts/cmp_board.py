#!/usr/bin/env python3
"""
cmp_board.py — Visual comparison (`cmp`) and 12–20 frame contact-sheet generator.

Supports five workflows central to claude-behavior:
  1. cmp        : Stitch 2–8 candidate images or HTML files side-by-side with clear labels.
  2. keyframes  : Extract 12–20 keyframes from a video/animation into a single labeled contact sheet.
  3. html-sheet : Capture 12–20 scroll slices, timeline frames, or slides from an HTML file into a sheet.
  4. grid       : Stitch 12–20 existing screenshots into a numbered inspection contact sheet.
  5. stress     : Render an HTML file across desktop/mobile viewports, light/dark mode, and content states.
"""

import argparse
import glob
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Neutral dark canvas keeps bright and dark UI screenshots equally legible without color cast
CANVAS_BG = (24, 24, 27)       # #18181b
TILE_BG = (39, 39, 42)         # #27272a
TILE_BORDER = (63, 63, 70)     # #3f3f46
TEXT_PRIMARY = (244, 244, 245) # #f4f4f5
TEXT_MUTED = (161, 161, 170)   # #a1a1aa
HEADER_HEIGHT = 38
PADDING = 16


def load_ui_font(size: int = 15) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a system font capable of rendering both Latin and CJK labels cleanly."""
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def expand_inputs(raw_inputs: list[str]) -> list[Path]:
    """Expand shell globs on platforms (like Windows PowerShell) that pass literal wildcards."""
    resolved: list[Path] = []
    for item in raw_inputs:
        if any(ch in item for ch in ("*", "?", "[")):
            matches = sorted(Path(p) for p in glob.glob(item))
            resolved.extend(matches)
        else:
            resolved.append(Path(item))
    return [p for p in resolved if p.exists()]


def render_html_to_image(
    html_path: Path,
    out_path: Path,
    width: int = 1440,
    height: int = 900,
    color_scheme: str = "light",
    wait_ms: int = 1200,
) -> Path:
    """Render a single HTML file to a PNG screenshot using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as err:
        raise RuntimeError(
            "Playwright is required to render .html inputs directly. "
            "Install via: pip install playwright && playwright install chromium"
        ) from err

    file_url = html_path.resolve().as_uri()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": width, "height": height},
            device_scale_factor=2,
            color_scheme=color_scheme,
        )
        page = context.new_page()
        page.goto(file_url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            # Long-polling or external font timeouts should not block visual capture
            pass
        page.wait_for_timeout(wait_ms)
        page.screenshot(path=str(out_path), full_page=False)
        context.close()
        browser.close()
    return out_path


def stitch_tiles(
    tiles: list[tuple[str, Image.Image]],
    out_path: Path,
    cols: int,
    tile_width: int = 640,
    title: str | None = None,
) -> Path:
    """Stitch (label, Image) pairs into a uniform grid contact sheet or cmp board."""
    if not tiles:
        raise ValueError("No tiles provided to stitch.")

    cols = max(1, min(cols, len(tiles)))
    rows = math.ceil(len(tiles) / cols)
    font = load_ui_font(15)
    title_font = load_ui_font(18)

    resized: list[tuple[str, Image.Image]] = []
    for label, img in tiles:
        rgb = img.convert("RGB")
        aspect = rgb.height / max(1, rgb.width)
        target_h = max(1, int(round(tile_width * aspect)))
        # Cap extreme tall full-page screenshots so one tile doesn't dwarf the whole board
        max_tile_h = int(tile_width * 1.6)
        if target_h > max_tile_h:
            rgb = rgb.crop((0, 0, rgb.width, int(rgb.width * 1.6)))
            target_h = max_tile_h
        thumb = rgb.resize((tile_width, target_h), Image.Resampling.LANCZOS)
        resized.append((label, thumb))

    # Compute row heights so each row fits its tallest tile cleanly
    row_heights: list[int] = []
    for r in range(rows):
        row_slice = resized[r * cols : (r + 1) * cols]
        max_h = max(im.height for _, im in row_slice)
        row_heights.append(max_h + HEADER_HEIGHT)

    top_banner = 46 if title else 0
    canvas_w = PADDING + cols * (tile_width + PADDING)
    canvas_h = top_banner + PADDING + sum(h + PADDING for h in row_heights)

    canvas = Image.new("RGB", (canvas_w, canvas_h), CANVAS_BG)
    draw = ImageDraw.Draw(canvas)

    if title:
        draw.text((PADDING, 14), title, fill=TEXT_PRIMARY, font=title_font)

    y_cursor = top_banner + PADDING
    for r in range(rows):
        row_h = row_heights[r]
        for c in range(cols):
            idx = r * cols + c
            if idx >= len(resized):
                break
            label, thumb = resized[idx]
            x = PADDING + c * (tile_width + PADDING)
            y = y_cursor

            # Draw card container and header bar
            card_box = [x - 1, y - 1, x + tile_width + 1, y + HEADER_HEIGHT + thumb.height + 1]
            draw.rectangle(card_box, fill=TILE_BG, outline=TILE_BORDER, width=1)
            draw.text((x + 10, y + 9), label, fill=TEXT_PRIMARY, font=font)
            canvas.paste(thumb, (x, y + HEADER_HEIGHT))

        y_cursor += row_h + PADDING

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=92)
    return out_path


def probe_video_duration(video_path: Path) -> float:
    """Return video duration in seconds via ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    return float(data["format"]["duration"])


def format_timestamp(seconds: float) -> str:
    mins = int(seconds) // 60
    secs = seconds - mins * 60
    return f"{mins:02d}:{secs:04.1f}"


def cmd_cmp(args: argparse.Namespace) -> int:
    """Build a side-by-side comparison board (`cmp`) from 2–8 images or HTML files."""
    paths = expand_inputs(args.inputs)
    if len(paths) < 2:
        print("Error: `cmp` requires at least 2 existing input files.", file=sys.stderr)
        return 1

    custom_labels = [s.strip() for s in args.labels.split(",")] if args.labels else []
    vp_w, vp_h = [int(x) for x in args.viewport.split("x")]

    tiles: list[tuple[str, Image.Image]] = []
    with tempfile.TemporaryDirectory(prefix="claude-cmp-") as tmp_dir:
        for idx, path in enumerate(paths):
            letter = chr(ord("A") + idx)
            label = custom_labels[idx] if idx < len(custom_labels) else f"Option {letter} · {path.name}"
            if path.suffix.lower() in (".html", ".htm"):
                shot_path = Path(tmp_dir) / f"opt_{idx}.png"
                render_html_to_image(path, shot_path, width=vp_w, height=vp_h)
                img = Image.open(shot_path).copy()
            else:
                img = Image.open(path).copy()
            tiles.append((label, img))

    cols = args.cols or min(len(tiles), 3 if len(tiles) == 3 else 2 if len(tiles) in (2, 4) else 3)
    out_path = Path(args.out)
    stitch_tiles(
        tiles=tiles,
        out_path=out_path,
        cols=cols,
        tile_width=args.tile_width,
        title=args.title or f"CMP Board ({len(tiles)} options) — Evaluate against explicit criteria",
    )
    print(f"✓ Saved cmp board ({len(tiles)} options) → {out_path}")
    return 0


def cmd_keyframes(args: argparse.Namespace) -> int:
    """Extract 12–20 keyframes from a video/animation and stitch into a contact sheet."""
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: Video file not found: {video_path}", file=sys.stderr)
        return 1

    count = max(4, args.count)
    duration = probe_video_duration(video_path)
    out_path = Path(args.out)
    frames_dir = out_path.parent / f"{out_path.stem}_frames" if args.keep_frames else None
    if frames_dir:
        frames_dir.mkdir(parents=True, exist_ok=True)

    # Sample from 2% to 98% of duration so we catch both intro and outro states cleanly
    start_t = duration * 0.02
    end_t = duration * 0.98
    step = (end_t - start_t) / max(1, count - 1) if count > 1 else 0.0

    tiles: list[tuple[str, Image.Image]] = []
    with tempfile.TemporaryDirectory(prefix="claude-kf-") as tmp_dir:
        target_dir = frames_dir if frames_dir else Path(tmp_dir)
        for idx in range(count):
            t = start_t + idx * step
            frame_file = target_dir / f"frame_{idx + 1:02d}_{t:.2f}s.png"
            cmd = [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{t:.3f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(frame_file),
            ]
            subprocess.run(cmd, check=False)
            if frame_file.exists():
                img = Image.open(frame_file).copy()
                label = f"#{idx + 1:02d}  t={format_timestamp(t)} ({t:.1f}s)"
                tiles.append((label, img))

    if not tiles:
        print("Error: Failed to extract keyframes via ffmpeg.", file=sys.stderr)
        return 1

    stitch_tiles(
        tiles=tiles,
        out_path=out_path,
        cols=args.cols,
        tile_width=args.tile_width,
        title=f"Keyframe Inspection Sheet · {video_path.name} ({len(tiles)} frames, total {duration:.1f}s)",
    )
    print(f"✓ Saved {len(tiles)}-keyframe contact sheet → {out_path}")
    if frames_dir:
        print(f"✓ Individual full-res frames saved in → {frames_dir}")
    return 0


def cmd_html_sheet(args: argparse.Namespace) -> int:
    """Capture 12–20 scroll slices, timeline beats, or slides from an HTML file into one contact sheet."""
    html_path = Path(args.html)
    if not html_path.exists():
        print(f"Error: HTML file not found: {html_path}", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: Playwright is required for html-sheet.", file=sys.stderr)
        return 1

    count = max(2, args.count)
    vp_w, vp_h = [int(x) for x in args.viewport.split("x")]
    out_path = Path(args.out)
    file_url = html_path.resolve().as_uri()
    tiles: list[tuple[str, Image.Image]] = []

    with tempfile.TemporaryDirectory(prefix="claude-html-sheet-") as tmp_dir:
        tmp = Path(tmp_dir)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": vp_w, "height": vp_h}, device_scale_factor=2)
            page = context.new_page()
            page.goto(file_url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            page.wait_for_timeout(800)

            if args.mode == "scroll":
                total_h = page.evaluate("Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
                max_scroll = max(0, total_h - vp_h)
                for idx in range(count):
                    ratio = idx / max(1, count - 1)
                    y_pos = int(round(max_scroll * ratio))
                    page.evaluate(f"window.scrollTo(0, {y_pos})")
                    page.wait_for_timeout(250)
                    shot = tmp / f"scroll_{idx + 1:02d}.png"
                    page.screenshot(path=str(shot), full_page=False)
                    tiles.append((f"#{idx + 1:02d}  y={y_pos}px ({int(ratio * 100)}%)", Image.open(shot).copy()))

            elif args.mode == "slides":
                for idx in range(count):
                    shot = tmp / f"slide_{idx + 1:02d}.png"
                    page.screenshot(path=str(shot), full_page=False)
                    tiles.append((f"Slide #{idx + 1:02d}", Image.open(shot).copy()))
                    if idx < count - 1:
                        page.keyboard.press("ArrowRight")
                        page.wait_for_timeout(450)

            elif args.mode == "timeline":
                duration = args.duration
                step_ms = int((duration * 1000) / max(1, count - 1))
                for idx in range(count):
                    t_sec = (idx * step_ms) / 1000.0
                    # Support custom window.seekTo(t) if defined; otherwise fast-forward Web Animations API
                    page.evaluate(
                        f"""(tSec) => {{
                            if (typeof window.seekTo === 'function') {{
                                window.seekTo(tSec);
                            }} else if (document.getAnimations) {{
                                document.getAnimations().forEach(a => {{ a.currentTime = tSec * 1000; a.pause(); }});
                            }}
                        }}""",
                        t_sec,
                    )
                    page.wait_for_timeout(150)
                    shot = tmp / f"time_{idx + 1:02d}.png"
                    page.screenshot(path=str(shot), full_page=False)
                    tiles.append((f"#{idx + 1:02d}  t={t_sec:.2f}s", Image.open(shot).copy()))

            context.close()
            browser.close()

    stitch_tiles(
        tiles=tiles,
        out_path=out_path,
        cols=args.cols,
        tile_width=args.tile_width,
        title=f"HTML Inspection Sheet ({args.mode}) · {html_path.name} ({len(tiles)} frames)",
    )
    print(f"✓ Saved HTML inspection contact sheet ({len(tiles)} frames) → {out_path}")
    return 0


def cmd_grid(args: argparse.Namespace) -> int:
    """Stitch 12–20 existing images into a numbered inspection contact sheet."""
    paths = expand_inputs(args.inputs)
    if not paths:
        print("Error: No matching image files found for `grid`.", file=sys.stderr)
        return 1

    tiles: list[tuple[str, Image.Image]] = []
    for idx, path in enumerate(paths):
        img = Image.open(path).copy()
        tiles.append((f"#{idx + 1:02d}  {path.name}", img))

    out_path = Path(args.out)
    stitch_tiles(
        tiles=tiles,
        out_path=out_path,
        cols=args.cols,
        tile_width=args.tile_width,
        title=args.title or f"Inspection Contact Sheet ({len(tiles)} screens)",
    )
    print(f"✓ Saved grid contact sheet ({len(tiles)} images) → {out_path}")
    return 0


def cmd_stress(args: argparse.Namespace) -> int:
    """Render an HTML file across viewport sizes and light/dark themes into one stress-test cmp board."""
    html_path = Path(args.html)
    if not html_path.exists():
        print(f"Error: HTML file not found: {html_path}", file=sys.stderr)
        return 1

    matrix = [
        ("Desktop 1440×900 · Light", 1440, 900, "light"),
        ("Desktop 1440×900 · Dark", 1440, 900, "dark"),
        ("Tablet 768×1024 · Light", 768, 1024, "light"),
        ("Mobile 375×667 · Light", 375, 667, "light"),
        ("Mobile 375×667 · Dark", 375, 667, "dark"),
        ("Wide 1920×1080 · Light", 1920, 1080, "light"),
    ]

    tiles: list[tuple[str, Image.Image]] = []
    with tempfile.TemporaryDirectory(prefix="claude-stress-") as tmp_dir:
        for idx, (label, w, h, scheme) in enumerate(matrix):
            shot = Path(tmp_dir) / f"stress_{idx}.png"
            render_html_to_image(html_path, shot, width=w, height=h, color_scheme=scheme)
            tiles.append((f"#{idx + 1:02d}  {label}", Image.open(shot).copy()))

    out_path = Path(args.out)
    stitch_tiles(
        tiles=tiles,
        out_path=out_path,
        cols=3,
        tile_width=args.tile_width,
        title=f"Stress-Test Board · {html_path.name} (Viewports + Light/Dark)",
    )
    print(f"✓ Saved stress-test board → {out_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate side-by-side cmp boards and 12–20 frame inspection contact sheets."
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. cmp
    p_cmp = sub.add_parser("cmp", help="Stitch 2–8 candidate images or HTML files side-by-side")
    p_cmp.add_argument("inputs", nargs="+", help="Image (.png/.jpg) or .html files to compare")
    p_cmp.add_argument("--labels", default="", help="Comma-separated labels for each option")
    p_cmp.add_argument("--cols", type=int, default=0, help="Columns (auto-chosen if omitted)")
    p_cmp.add_argument("--tile-width", type=int, default=720, help="Width per tile in pixels (default 720)")
    p_cmp.add_argument("--viewport", default="1440x900", help="Viewport WxH when rendering .html inputs")
    p_cmp.add_argument("--title", default="", help="Optional banner title")
    p_cmp.add_argument("--out", default="cmp.png", help="Output image path (default cmp.png)")
    p_cmp.set_defaults(func=cmd_cmp)

    # 2. keyframes
    p_kf = sub.add_parser("keyframes", help="Extract 12–20 keyframes from a video into one contact sheet")
    p_kf.add_argument("video", help="Input video file (.mp4, .webm, .mov, .gif)")
    p_kf.add_argument("--count", type=int, default=16, help="Number of keyframes to extract (default 16, rec 12–20)")
    p_kf.add_argument("--cols", type=int, default=4, help="Grid columns (default 4)")
    p_kf.add_argument("--tile-width", type=int, default=560, help="Width per frame tile (default 560)")
    p_kf.add_argument("--keep-frames", action="store_true", help="Also save individual full-res frames to a folder")
    p_kf.add_argument("--out", default="inspect-keyframes.png", help="Output contact sheet path")
    p_kf.set_defaults(func=cmd_keyframes)

    # 3. html-sheet
    p_hs = sub.add_parser("html-sheet", help="Sample 12–20 scroll/timeline/slide frames from an HTML file")
    p_hs.add_argument("html", help="Input HTML file")
    p_hs.add_argument("--mode", choices=["scroll", "slides", "timeline"], default="scroll")
    p_hs.add_argument("--count", type=int, default=16, help="Number of frames/slices to capture (default 16)")
    p_hs.add_argument("--duration", type=float, default=10.0, help="Timeline duration in seconds (for --mode timeline)")
    p_hs.add_argument("--cols", type=int, default=4, help="Grid columns (default 4)")
    p_hs.add_argument("--tile-width", type=int, default=560, help="Width per tile (default 560)")
    p_hs.add_argument("--viewport", default="1440x900", help="Viewport WxH (default 1440x900)")
    p_hs.add_argument("--out", default="inspect-html-sheet.png", help="Output contact sheet path")
    p_hs.set_defaults(func=cmd_html_sheet)

    # 4. grid
    p_grid = sub.add_parser("grid", help="Stitch 12–20 existing screenshots into a numbered contact sheet")
    p_grid.add_argument("inputs", nargs="+", help="Image paths or glob pattern")
    p_grid.add_argument("--cols", type=int, default=4, help="Grid columns (default 4)")
    p_grid.add_argument("--tile-width", type=int, default=560, help="Width per tile (default 560)")
    p_grid.add_argument("--title", default="", help="Optional banner title")
    p_grid.add_argument("--out", default="inspect-grid.png", help="Output contact sheet path")
    p_grid.set_defaults(func=cmd_grid)

    # 5. stress
    p_stress = sub.add_parser("stress", help="Render an HTML file across viewports and light/dark themes")
    p_stress.add_argument("html", help="Input HTML file")
    p_stress.add_argument("--tile-width", type=int, default=560, help="Width per tile (default 560)")
    p_stress.add_argument("--out", default="cmp-stress.png", help="Output board path")
    p_stress.set_defaults(func=cmd_stress)

    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
