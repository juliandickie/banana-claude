#!/usr/bin/env python3
"""Banana Claude -- Multi-Format Image Converter

Convert a generated image to multiple formats and sizes using ImageMagick.
Detects source aspect ratio and scales to standard pixel dimensions per tier.

Uses only Python stdlib + subprocess (ImageMagick required).

Usage:
    multiformat.py convert --input hero.png --formats png,webp,jpeg --sizes 4k,2k,1k
    multiformat.py convert --input hero.png --formats webp --sizes 2k --quality 90 --output ./out
    multiformat.py info --input hero.png
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path.home() / "Documents" / "nanobanana_generated"

STANDARD_RATIOS = [
    (16, 9), (9, 16), (1, 1), (4, 3), (3, 4),
    (4, 5), (5, 4), (3, 2), (2, 3), (21, 9),
]

SIZE_MAP = {
    "4K": {"16:9": (3840, 2160), "9:16": (2160, 3840), "1:1": (3840, 3840), "4:3": (3840, 2880), "3:4": (2880, 3840), "4:5": (3072, 3840), "5:4": (3840, 3072), "3:2": (3840, 2560), "2:3": (2560, 3840), "21:9": (3840, 1646)},
    "2K": {"16:9": (2560, 1440), "9:16": (1440, 2560), "1:1": (2560, 2560), "4:3": (2560, 1920), "3:4": (1920, 2560), "4:5": (2048, 2560), "5:4": (2560, 2048), "3:2": (2560, 1707), "2:3": (1707, 2560), "21:9": (2560, 1097)},
    "1K": {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:3": (1440, 1080), "3:4": (1080, 1440), "4:5": (864, 1080), "5:4": (1080, 864), "3:2": (1620, 1080), "2:3": (1080, 1620), "21:9": (1920, 823)},
    "512": {"16:9": (910, 512), "9:16": (512, 910), "1:1": (512, 512), "4:3": (683, 512), "3:4": (512, 683), "4:5": (410, 512), "5:4": (512, 410), "3:2": (768, 512), "2:3": (512, 768), "21:9": (910, 390)},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_exit(msg):
    """Print error JSON to stdout and exit."""
    print(json.dumps({"error": True, "message": msg}, indent=2))
    sys.exit(1)


def _find_magick():
    """Return (path, backend) for image conversion.
    Checks: magick (v7) -> convert (v6) -> sips (macOS built-in).
    Returns: (path_string, "magick"|"convert"|"sips") or (None, None).
    """
    magick = shutil.which("magick")
    if magick:
        return magick, "magick"
    convert = shutil.which("convert")
    if convert:
        return convert, "convert"
    sips = shutil.which("sips")
    if sips:
        return sips, "sips"
    return None, None


def _get_image_info(path, magick_cmd, backend):
    """Get width, height, format from an image file."""
    if backend == "sips":
        try:
            result = subprocess.run(
                ["sips", "--getProperty", "pixelWidth", "--getProperty", "pixelHeight",
                 "--getProperty", "format", str(path)],
                capture_output=True, text=True, check=True)
            w = h = 0
            fmt = "unknown"
            for line in result.stdout.splitlines():
                if "pixelWidth" in line:
                    w = int(line.split(":")[-1].strip())
                elif "pixelHeight" in line:
                    h = int(line.split(":")[-1].strip())
                elif "format" in line:
                    fmt = line.split(":")[-1].strip().lower()
            return w, h, fmt
        except (subprocess.CalledProcessError, ValueError) as exc:
            _error_exit(f"Failed to read image info via sips: {exc}")
    else:
        cmd = [magick_cmd, "identify", "-format", "%w %h %m", str(path)]
        if backend == "convert":
            cmd = ["identify", "-format", "%w %h %m", str(path)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            parts = result.stdout.strip().split()
            return int(parts[0]), int(parts[1]), parts[2].lower()
        except (subprocess.CalledProcessError, ValueError, IndexError) as exc:
            _error_exit(f"Failed to read image info: {exc}")


def _detect_ratio(width, height):
    """Map pixel dimensions to the nearest standard ratio string."""
    actual = width / height
    best_ratio = "1:1"
    best_diff = float("inf")
    for rw, rh in STANDARD_RATIOS:
        diff = abs(actual - rw / rh)
        if diff < best_diff:
            best_diff = diff
            best_ratio = f"{rw}:{rh}"
    return best_ratio


def _convert_one(magick_cmd, backend, input_path, output_path, width, height, fmt, quality):
    """Run a single image conversion."""
    if backend == "sips":
        # sips can resize and convert format. Two-step: resize, then convert if needed.
        sips_fmt_map = {"png": "png", "jpeg": "jpeg", "webp": "png"}  # sips can't write webp
        sips_fmt = sips_fmt_map.get(fmt, "png")
        tmp_out = str(output_path) if fmt != "webp" else str(output_path) + ".tmp.png"
        subprocess.run(
            ["sips", "--resampleHeightWidth", str(height), str(width),
             "-s", "format", sips_fmt, str(input_path), "--out", tmp_out],
            capture_output=True, text=True, check=True)
        if fmt == "webp":
            cwebp = shutil.which("cwebp")
            if cwebp:
                subprocess.run([cwebp, "-q", str(quality), tmp_out, "-o", str(output_path)],
                               capture_output=True, text=True, check=True)
                os.remove(tmp_out)
            else:
                os.rename(tmp_out, str(output_path).replace(".webp", ".png"))
                print(f"Warning: cwebp not found, saved as PNG instead of WebP", file=sys.stderr)
    else:
        if fmt == "jpeg":
            cmd = [magick_cmd, str(input_path), "-resize", f"{width}x{height}!",
                   "-background", "white", "-flatten", "-quality", str(quality), str(output_path)]
        elif fmt == "webp":
            cmd = [magick_cmd, str(input_path), "-resize", f"{width}x{height}!",
                   "-quality", str(quality), str(output_path)]
        else:  # png -- lossless
            cmd = [magick_cmd, str(input_path), "-resize", f"{width}x{height}!", str(output_path)]
        subprocess.run(cmd, capture_output=True, text=True, check=True)


def convert_image(input_path, output_dir, formats, sizes, quality, magick_cmd, backend):
    """Main conversion: produce each format x size combination."""
    width, height, src_fmt = _get_image_info(input_path, magick_cmd, backend)
    ratio = _detect_ratio(width, height)
    stem = Path(input_path).stem

    output_dir.mkdir(parents=True, exist_ok=True)
    ext_map = {"png": ".png", "webp": ".webp", "jpeg": ".jpg"}
    outputs = []

    for size in sizes:
        size_key = size.upper()
        if size_key not in SIZE_MAP:
            _error_exit(f"Unknown size tier: {size}. Valid: {', '.join(SIZE_MAP.keys())}")
        tier = SIZE_MAP[size_key]
        if ratio not in tier:
            _error_exit(f"Ratio {ratio} not defined for size {size_key}.")
        tw, th = tier[ratio]

        for fmt in formats:
            fmt = fmt.lower()
            if fmt not in ext_map:
                _error_exit(f"Unknown format: {fmt}. Valid: png, webp, jpeg")
            ext = ext_map[fmt]
            filename = f"{stem}-{size_key.lower()}{ext}"
            out_path = output_dir / filename
            _convert_one(magick_cmd, backend, input_path, out_path, tw, th, fmt, quality)
            file_kb = round(out_path.stat().st_size / 1024)
            outputs.append({
                "path": filename,
                "format": fmt,
                "size": size_key,
                "pixels": [tw, th],
                "file_size_kb": file_kb,
            })

    return {
        "source": str(input_path),
        "source_dimensions": [width, height],
        "source_ratio": ratio,
        "output_dir": str(output_dir) + "/",
        "outputs": outputs,
        "total_files": len(outputs),
    }


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_convert(args):
    """Handle the convert subcommand."""
    magick_cmd, backend = _find_magick()
    if not magick_cmd:
        _error_exit("No image converter found. Install ImageMagick: brew install imagemagick")

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        _error_exit(f"Input file not found: {input_path}")

    formats = [f.strip().lower() for f in args.formats.split(",")]
    sizes = [s.strip() for s in args.sizes.split(",")]
    quality = args.quality

    if args.output:
        output_dir = Path(args.output).expanduser().resolve()
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_DIR / f"multiformat_{ts}"

    result = convert_image(input_path, output_dir, formats, sizes, quality, magick_cmd, backend)
    print(json.dumps(result, indent=2))


def cmd_info(args):
    """Handle the info subcommand."""
    magick_cmd, backend = _find_magick()
    if not magick_cmd:
        _error_exit("No image converter found. Install ImageMagick: brew install imagemagick")

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        _error_exit(f"Input file not found: {input_path}")

    width, height, fmt = _get_image_info(input_path, magick_cmd, backend)
    ratio = _detect_ratio(width, height)
    file_kb = round(input_path.stat().st_size / 1024)
    print(json.dumps({
        "path": str(input_path),
        "width": width,
        "height": height,
        "format": fmt,
        "ratio": ratio,
        "file_size_kb": file_kb,
    }, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Multi-format image converter for nano-banana-studio")
    sub = parser.add_subparsers(dest="command", required=True)

    p_convert = sub.add_parser("convert", help="Convert image to multiple formats and sizes")
    p_convert.add_argument("--input", required=True, help="Path to source image")
    p_convert.add_argument("--formats", required=True, help="Comma-separated formats: png,webp,jpeg")
    p_convert.add_argument("--sizes", required=True, help="Comma-separated size tiers: 4k,2k,1k,512")
    p_convert.add_argument("--quality", type=int, default=85, help="JPEG/WebP quality (default: 85)")
    p_convert.add_argument("--output", help="Output directory (default: auto-timestamped)")

    p_info = sub.add_parser("info", help="Show image dimensions, ratio, and format")
    p_info.add_argument("--input", required=True, help="Path to source image")

    args = parser.parse_args()
    if args.command == "convert":
        cmd_convert(args)
    elif args.command == "info":
        cmd_info(args)


if __name__ == "__main__":
    main()
