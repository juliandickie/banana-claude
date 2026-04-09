#!/usr/bin/env python3
"""Banana Claude -- Video Extension via VEO 3.1

Extend a video clip by chaining: extract last frame, use as reference
for next generation, concatenate. Each hop adds ~7 seconds of video.
Maximum total duration: 148 seconds (20 hops).

Uses only Python stdlib + subprocess (FFmpeg and video_generate.py).

Usage:
    video_extend.py --input clip.mp4 --target-duration 30
                    [--prompt "continue the scene..."]
                    [--api-key KEY] [--output extended.mp4]
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────

HOP_DURATION = 7  # effective seconds per generation (8s with overlap)
GENERATE_DURATION = 8  # duration passed to video_generate.py
MAX_HOPS = 20
MAX_DURATION = 148  # MAX_HOPS * HOP_DURATION + initial clip headroom
COST_PER_HOP = 1.20  # USD estimate per VEO generation
SCRIPT_DIR = Path(__file__).resolve().parent
GENERATE_SCRIPT = SCRIPT_DIR / "video_generate.py"


def _error_exit(message):
    """Print JSON error to stdout and exit."""
    print(json.dumps({"error": True, "message": message}))
    sys.exit(1)


def _progress(data):
    """Print progress JSON to stderr."""
    print(json.dumps(data), file=sys.stderr)


def _check_tool(name):
    """Verify an external tool is on PATH."""
    if shutil.which(name) is None:
        _error_exit(
            f"{name} not found. Install FFmpeg: "
            "brew install ffmpeg (macOS) or apt install ffmpeg (Linux)"
        )


def _get_duration(video_path):
    """Get video duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(video_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _error_exit(f"ffprobe failed on {video_path}: {result.stderr.strip()}")
    try:
        return float(result.stdout.strip())
    except ValueError:
        _error_exit(f"Could not parse duration from ffprobe output: {result.stdout.strip()}")


def _extract_last_frame(video_path, output_path):
    """Extract the last frame of a video as PNG."""
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-sseof", "-0.1",
            "-i", str(video_path),
            "-frames:v", "1", "-update", "1",
            str(output_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _error_exit(f"Failed to extract last frame: {result.stderr.strip()}")


def _generate_clip(first_frame, prompt, api_key, output_dir):
    """Call video_generate.py with first-frame to produce next clip."""
    cmd = [
        sys.executable, str(GENERATE_SCRIPT),
        "--first-frame", str(first_frame),
        "--duration", str(GENERATE_DURATION),
        "--output", str(output_dir),
    ]
    if prompt:
        cmd.extend(["--prompt", prompt])
    if api_key:
        cmd.extend(["--api-key", api_key])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr_msg = result.stderr.strip()
        # Try to parse JSON error from stdout
        try:
            err = json.loads(result.stdout)
            return None, err.get("message", stderr_msg)
        except (json.JSONDecodeError, ValueError):
            return None, stderr_msg or "video_generate.py failed with no output"

    try:
        output = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None, f"Could not parse video_generate.py output: {result.stdout[:200]}"

    if output.get("error"):
        return None, output.get("message", "Unknown generation error")

    clip_path = output.get("path")
    if not clip_path or not Path(clip_path).exists():
        return None, "video_generate.py did not produce a video file"
    return clip_path, None


def _concat_clips(clip_a, clip_b, output_path, tmpdir):
    """Concatenate two clips via FFmpeg concat demuxer."""
    list_file = Path(tmpdir) / "concat_list.txt"
    with open(list_file, "w") as f:
        f.write(f"file '{clip_a}'\n")
        f.write(f"file '{clip_b}'\n")

    result = subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _error_exit(f"FFmpeg concat failed: {result.stderr.strip()}")


def _trim_to_duration(input_path, target_duration, output_path):
    """Trim video to exact target duration."""
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-t", str(target_duration),
            "-c", "copy",
            str(output_path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _error_exit(f"FFmpeg trim failed: {result.stderr.strip()}")


def main():
    parser = argparse.ArgumentParser(
        description="Extend a video clip by chaining VEO generations"
    )
    parser.add_argument("--input", required=True, help="Input video file")
    parser.add_argument(
        "--target-duration", type=float, required=True,
        help="Desired final duration in seconds"
    )
    parser.add_argument("--prompt", default="", help="Continuation prompt for each hop")
    parser.add_argument("--api-key", default=None, help="Google AI API key")
    parser.add_argument("--output", default=None, help="Output file path")
    args = parser.parse_args()

    # ── Preflight checks ─────────────────────────────────────────────
    _check_tool("ffmpeg")
    _check_tool("ffprobe")

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        _error_exit(f"Input file not found: {input_path}")

    if not GENERATE_SCRIPT.exists():
        _error_exit(f"video_generate.py not found at {GENERATE_SCRIPT}")

    original_duration = _get_duration(input_path)
    target = args.target_duration

    if target <= original_duration:
        _error_exit(
            f"Target duration ({target}s) must be greater than "
            f"input duration ({original_duration:.1f}s)"
        )

    remaining = target - original_duration
    hops_needed = math.ceil(remaining / HOP_DURATION)

    if hops_needed > MAX_HOPS:
        _error_exit(
            f"Need {hops_needed} hops but maximum is {MAX_HOPS} "
            f"(148s total). Reduce --target-duration."
        )

    _progress({
        "stage": "plan",
        "original_duration": round(original_duration, 1),
        "target_duration": target,
        "hops_needed": hops_needed,
        "estimated_cost": round(hops_needed * COST_PER_HOP, 2),
    })

    # ── Extension loop ───────────────────────────────────────────────
    with tempfile.TemporaryDirectory(prefix="video_extend_") as tmpdir:
        current_clip = str(input_path)
        hops_done = 0

        for hop in range(1, hops_needed + 1):
            _progress({"stage": "hop", "hop": hop, "of": hops_needed})

            # Extract last frame
            last_frame = os.path.join(tmpdir, f"lastframe_{hop}.png")
            _extract_last_frame(current_clip, last_frame)

            # Generate next segment
            gen_dir = os.path.join(tmpdir, f"gen_{hop}")
            os.makedirs(gen_dir, exist_ok=True)
            new_clip, error = _generate_clip(
                last_frame, args.prompt, args.api_key, gen_dir
            )
            if error:
                _error_exit(f"Generation failed at hop {hop}/{hops_needed}: {error}")

            # Concatenate
            concat_out = os.path.join(tmpdir, f"concat_{hop}.mp4")
            _concat_clips(current_clip, new_clip, concat_out, tmpdir)
            current_clip = concat_out
            hops_done = hop

            current_dur = _get_duration(current_clip)
            _progress({
                "stage": "hop_done",
                "hop": hop,
                "current_duration": round(current_dur, 1),
            })

        # ── Trim and finalize ────────────────────────────────────────
        if args.output:
            output_path = Path(args.output).resolve()
        else:
            stem = input_path.stem
            output_path = input_path.parent / f"{stem}_extended.mp4"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Trim to exact target duration
        final_duration = _get_duration(current_clip)
        if final_duration > target:
            _trim_to_duration(current_clip, target, str(output_path))
        else:
            shutil.copy2(current_clip, str(output_path))

        final_duration = _get_duration(str(output_path))

    # ── Output ───────────────────────────────────────────────────────
    print(json.dumps({
        "path": str(output_path),
        "original_duration": round(original_duration, 1),
        "final_duration": round(final_duration, 1),
        "hops": hops_done,
        "cost": round(hops_done * COST_PER_HOP, 2),
    }))


if __name__ == "__main__":
    main()
