#!/usr/bin/env python3
"""Banana Claude -- Video Stitching Toolkit

Concatenate, trim, and convert video clips using FFmpeg.
Uses only Python stdlib + subprocess (FFmpeg only).

Usage:
    video_stitch.py concat --clips clip1.mp4 clip2.mp4 --output final.mp4
    video_stitch.py concat --dir ~/clips/ --output final.mp4
    video_stitch.py trim --input video.mp4 --start 0 --end 30 --output trimmed.mp4
    video_stitch.py convert --input video.mp4 --format webm [--quality 80] --output out.webm
    video_stitch.py info --input video.mp4
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
FORMAT_CODECS = {
    "mp4": {"vcodec": "libx264", "ext": ".mp4"},
    "webm": {"vcodec": "libvpx-vp9", "ext": ".webm"},
    "mov": {"vcodec": "libx264", "ext": ".mov"},
    "avi": {"vcodec": "libx264", "ext": ".avi"},
}


def _error_exit(message):
    """Print JSON error to stdout and exit."""
    print(json.dumps({"error": True, "message": message}))
    sys.exit(1)


def _check_ffmpeg():
    """Verify ffmpeg and ffprobe are available."""
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            _error_exit(
                f"{tool} not found. Install FFmpeg: "
                "brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
            )


def _probe_json(video_path):
    """Run ffprobe and return parsed JSON with format + stream info."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration,size:stream=width,height,codec_name,r_frame_rate,codec_type",
            "-of", "json",
            str(video_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _error_exit(f"ffprobe failed on {video_path}: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        _error_exit(f"Could not parse ffprobe output for {video_path}")


# ── Subcommands ──────────────────────────────────────────────────────

def cmd_concat(args):
    """Concatenate multiple video clips."""
    _check_ffmpeg()

    # Collect clip list
    clips = []
    if args.clips:
        clips = [Path(c).resolve() for c in args.clips]
    elif args.dir:
        clip_dir = Path(args.dir).resolve()
        if not clip_dir.is_dir():
            _error_exit(f"Directory not found: {clip_dir}")
        clips = sorted(
            p for p in clip_dir.iterdir()
            if p.suffix.lower() in VIDEO_EXTENSIONS
        )
    else:
        _error_exit("Provide --clips or --dir")

    if len(clips) < 2:
        _error_exit(f"Need at least 2 clips to concatenate, found {len(clips)}")

    for c in clips:
        if not c.exists():
            _error_exit(f"Clip not found: {c}")

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for c in clips:
            f.write(f"file '{c}'\n")
        list_file = f.name

    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file,
                "-c", "copy",
                str(output),
            ],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            _error_exit(f"FFmpeg concat failed: {result.stderr.strip()}")
    finally:
        os.unlink(list_file)

    probe = _probe_json(str(output))
    duration = float(probe.get("format", {}).get("duration", 0))

    print(json.dumps({
        "path": str(output),
        "clips": len(clips),
        "duration": round(duration, 1),
    }))


def cmd_trim(args):
    """Trim a video to a time range."""
    _check_ffmpeg()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        _error_exit(f"Input not found: {input_path}")

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    duration = args.end - args.start
    if duration <= 0:
        _error_exit(f"End ({args.end}) must be greater than start ({args.start})")

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-ss", str(args.start),
            "-t", str(duration),
            "-c", "copy",
            str(output),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _error_exit(f"FFmpeg trim failed: {result.stderr.strip()}")

    probe = _probe_json(str(output))
    final_dur = float(probe.get("format", {}).get("duration", 0))

    print(json.dumps({
        "path": str(output),
        "start": args.start,
        "end": args.end,
        "duration": round(final_dur, 1),
    }))


def cmd_convert(args):
    """Convert a video to a different format."""
    _check_ffmpeg()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        _error_exit(f"Input not found: {input_path}")

    fmt = args.format.lower()
    if fmt not in FORMAT_CODECS:
        _error_exit(f"Unsupported format: {fmt}. Supported: {', '.join(FORMAT_CODECS)}")

    codec_info = FORMAT_CODECS[fmt]
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Map quality 0-100 to CRF (lower CRF = higher quality, range 0-51)
    quality = max(0, min(100, args.quality))
    crf = str(round(51 - (quality / 100 * 51)))

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-c:v", codec_info["vcodec"],
        "-crf", crf,
    ]
    if fmt == "webm":
        cmd.extend(["-b:v", "0"])  # required for CRF mode with VP9
    cmd.append(str(output))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        _error_exit(f"FFmpeg convert failed: {result.stderr.strip()}")

    file_size_kb = round(output.stat().st_size / 1024)

    print(json.dumps({
        "path": str(output),
        "format": fmt,
        "quality": quality,
        "file_size_kb": file_size_kb,
    }))


def cmd_info(args):
    """Get video file information."""
    _check_ffmpeg()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        _error_exit(f"Input not found: {input_path}")

    probe = _probe_json(str(input_path))
    fmt = probe.get("format", {})
    duration = float(fmt.get("duration", 0))
    file_size_kb = round(int(fmt.get("size", 0)) / 1024)

    # Find video stream
    width, height, codec, fps = 0, 0, "unknown", 0
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            width = stream.get("width", 0)
            height = stream.get("height", 0)
            codec = stream.get("codec_name", "unknown")
            # Parse frame rate fraction like "24/1" or "30000/1001"
            fps_str = stream.get("r_frame_rate", "0/1")
            try:
                num, den = fps_str.split("/")
                fps = round(int(num) / int(den), 2) if int(den) else 0
            except (ValueError, ZeroDivisionError):
                fps = 0
            break

    resolution = f"{width}x{height}" if width and height else "unknown"

    print(json.dumps({
        "path": str(input_path),
        "duration": round(duration, 1),
        "resolution": resolution,
        "codec": codec,
        "fps": fps,
        "file_size_kb": file_size_kb,
    }))


# ── CLI ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Video stitching toolkit: concat, trim, convert, info"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # concat
    p_concat = sub.add_parser("concat", help="Concatenate video clips")
    p_concat.add_argument("--clips", nargs="+", help="Video files to concatenate")
    p_concat.add_argument("--dir", help="Directory of clips to concatenate (sorted)")
    p_concat.add_argument("--output", required=True, help="Output file path")

    # trim
    p_trim = sub.add_parser("trim", help="Trim a video to a time range")
    p_trim.add_argument("--input", required=True, help="Input video file")
    p_trim.add_argument("--start", type=float, required=True, help="Start time (seconds)")
    p_trim.add_argument("--end", type=float, required=True, help="End time (seconds)")
    p_trim.add_argument("--output", required=True, help="Output file path")

    # convert
    p_conv = sub.add_parser("convert", help="Convert video format")
    p_conv.add_argument("--input", required=True, help="Input video file")
    p_conv.add_argument("--format", required=True, help="Target format (mp4, webm, mov, avi)")
    p_conv.add_argument("--quality", type=int, default=80, help="Quality 0-100 (default: 80)")
    p_conv.add_argument("--output", required=True, help="Output file path")

    # info
    p_info = sub.add_parser("info", help="Get video file information")
    p_info.add_argument("--input", required=True, help="Input video file")

    args = parser.parse_args()
    commands = {
        "concat": cmd_concat,
        "trim": cmd_trim,
        "convert": cmd_convert,
        "info": cmd_info,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
