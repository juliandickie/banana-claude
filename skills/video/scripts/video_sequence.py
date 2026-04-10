#!/usr/bin/env python3
"""Banana Claude -- Multi-Shot Sequence Production Pipeline

Break scripts into shot lists, generate storyboard frame pairs using the
image generation API, batch-generate video clips via VEO, and stitch them
together with FFmpeg.  Uses only Python stdlib + subprocess.

Subcommands:
    video_sequence.py plan --script "30-second product launch ad" --target 30
                           [--preset NAME] [--output shot-list.json]
    video_sequence.py storyboard --plan shot-list.json [--api-key KEY]
                                  [--output DIR]
    video_sequence.py estimate --plan shot-list.json
    video_sequence.py generate --storyboard DIR [--api-key KEY] [--output DIR]
    video_sequence.py stitch --clips DIR --output final.mp4
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_BASE = Path.home() / "Documents" / "nanobanana_generated"
COST_STORYBOARD_FRAME = 0.078   # per 2K frame
AVG_SHOT_DURATION = 7           # seconds, for shot-count estimation
MIN_SHOTS = 2
DEFAULT_SHOT_DURATION = 8
MAX_SHOT_DURATION = 8

# Default model for sequences. Individual shots (shot["model"]) and
# sequence-level overrides (plan["model"]) take precedence over this.
DEFAULT_SEQUENCE_MODEL = "veo-3.1-generate-preview"
DEFAULT_SEQUENCE_RESOLUTION = "1080p"

# Quality-tier CLI flag maps to concrete model IDs.
#
# Note: Lite (`veo-3.1-lite-generate-001`) and Legacy 3.0 are Vertex-AI
# only as of 2026-04-10. Until the Vertex AI backend ships (v3.6.0),
# `draft` maps to Fast — which is still an 8x discount vs Standard
# ($0.15/sec vs $0.40/sec) and preserves the draft-then-final value
# proposition even without true Lite access. Once the Vertex AI backend
# lands, `draft` should be re-pointed at Lite for the full ~15x cost
# reduction.
QUALITY_TIER_MODELS = {
    "draft": "veo-3.1-fast-generate-preview",      # Vertex-AI-free fallback
    "fast": "veo-3.1-fast-generate-preview",
    "standard": "veo-3.1-generate-preview",
    # Legacy + real Lite are gated in video_generate.py and will fail
    # fast with a clear message; keeping them here lets Vertex-enabled
    # users opt in when the backend ships.
    "lite": "veo-3.1-lite-generate-001",           # Vertex AI only
    "legacy": "veo-3.0-generate-001",              # Vertex AI only
}

# Fallback per-second rates matching cost_tracker.PRICING. Kept in sync by
# convention rather than import to preserve this script's stdlib-only posture.
_VEO_PER_SECOND = {
    "veo-3.1-generate-preview": 0.40,
    "veo-3.1-generate-001": 0.40,
    "veo-3.1-fast-generate-preview": 0.15,
    "veo-3.1-fast-generate-001": 0.15,
    "veo-3.1-lite-generate-001": 0.05,
    "veo-3.0-generate-001": 0.15,
}

SHOT_TYPES = ("establishing", "content", "closeup", "transition", "broll")


def _veo_cost(model, duration_seconds):
    """Local VEO cost lookup. Mirrors cost_tracker._veo_cost but stdlib-only."""
    rate = _VEO_PER_SECOND.get(model)
    if rate is None:
        return None
    return round(rate * duration_seconds, 4)


def _resolve_shot_model(shot, plan, override=None):
    """3-level cascade: CLI override → shot["model"] → plan["model"] → default."""
    return (
        override
        or shot.get("model")
        or plan.get("model")
        or DEFAULT_SEQUENCE_MODEL
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error_exit(message):
    """Print JSON error to stdout and exit."""
    print(json.dumps({"error": True, "message": message}))
    sys.exit(1)


def _progress(data):
    """Print progress JSON to stderr."""
    print(json.dumps(data), file=sys.stderr)


def _load_api_key(cli_key):
    """Load API key: CLI -> env -> config.json."""
    api_key = (
        cli_key
        or os.environ.get("GOOGLE_AI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
    )
    if not api_key:
        config_path = Path.home() / ".banana" / "config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    api_key = json.load(f).get("google_ai_api_key", "")
            except (json.JSONDecodeError, OSError):
                pass
    if not api_key:
        _error_exit(
            "No API key. Run /banana setup, set GOOGLE_AI_API_KEY env, "
            "or pass --api-key"
        )
    return api_key


def _load_plan(path):
    """Load a shot-list JSON plan from *path*."""
    p = Path(path)
    if not p.exists():
        _error_exit(f"Plan file not found: {path}")
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        _error_exit(f"Failed to read plan: {exc}")


def _save_plan(path, plan):
    """Write *plan* dict to *path* as formatted JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(plan, f, indent=2)
    return str(p.resolve())


def _default_output(suffix):
    """Return a timestamped output directory under OUTPUT_BASE."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(OUTPUT_BASE / f"sequence_{suffix}_{ts}")


def _run_script(script_path, args, api_key):
    """Run a Python helper script, inject --api-key, return parsed JSON stdout."""
    cmd = [sys.executable, str(script_path)] + args
    if api_key:
        cmd += ["--api-key", api_key]

    _progress({"running": str(script_path.name), "args": args})

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        _error_exit(f"Script timed out: {script_path.name}")
    except FileNotFoundError:
        _error_exit(f"Script not found: {script_path}")

    if proc.returncode != 0:
        # Try to parse the child's JSON error
        try:
            err = json.loads(proc.stdout)
            _error_exit(err.get("message", proc.stdout.strip()))
        except (json.JSONDecodeError, ValueError):
            _error_exit(
                f"{script_path.name} failed (exit {proc.returncode}): "
                f"{proc.stderr.strip() or proc.stdout.strip()}"
            )

    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        _error_exit(
            f"Non-JSON output from {script_path.name}: "
            f"{proc.stdout[:300]}"
        )


def _resolve_script(relative_parts):
    """Resolve a script path relative to this file's location.

    *relative_parts* is a list like ["banana", "scripts", "generate.py"]
    which becomes  <this_dir>/../../banana/scripts/generate.py
    """
    base = Path(__file__).resolve().parent.parent.parent
    return base.joinpath(*relative_parts)


def _copy_file(src, dst):
    """Copy *src* to *dst*, creating parent dirs."""
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(dst))
    return str(Path(dst).resolve())


# ---------------------------------------------------------------------------
# Subcommand: plan
# ---------------------------------------------------------------------------

def cmd_plan(args):
    """Create a shot-list structure from a script description and target duration."""
    target = args.target
    if target < 4:
        _error_exit("Target duration must be at least 4 seconds")

    shot_count = max(MIN_SHOTS, target // AVG_SHOT_DURATION)

    # Distribute duration across shots
    shots = []
    remaining = target
    for i in range(shot_count):
        is_last = i == shot_count - 1
        if is_last:
            dur = min(MAX_SHOT_DURATION, remaining)
        else:
            dur = min(DEFAULT_SHOT_DURATION, remaining - (shot_count - i - 1))
            dur = max(4, dur)  # minimum 4s per shot
        remaining -= dur

        shots.append({
            "number": i + 1,
            "duration": dur,
            "type": "content",
            "camera": "",
            "subject": "",
            "action": "",
            "setting": "",
            "audio": "",
            "prompt": "",
            "start_frame_prompt": "",
            "end_frame_prompt": "",
            "consistency_notes": "",
            # Optional per-shot overrides. Empty string = fall back to the
            # sequence-level model/resolution at generate time.
            "model": "",
            "resolution": "",
            "status": "planned",
        })

    storyboard_cost = shot_count * 2 * COST_STORYBOARD_FRAME
    # Sequence-level model used for the estimate. May be overridden later by
    # --quality-tier at generate time.
    sequence_model = DEFAULT_SEQUENCE_MODEL
    video_cost = sum(_veo_cost(sequence_model, s["duration"]) or 0.0 for s in shots)

    plan = {
        "script": args.script,
        "target_duration": target,
        "preset": getattr(args, "preset", None),
        "model": sequence_model,
        "resolution": DEFAULT_SEQUENCE_RESOLUTION,
        "shot_count": shot_count,
        "shots": shots,
        "estimated_cost": {
            "storyboard_frames": round(storyboard_cost, 2),
            "video_clips": round(video_cost, 2),
            "total": round(storyboard_cost + video_cost, 2),
            "model": sequence_model,
        },
    }

    output_path = args.output or _default_output("plan") + "/shot-list.json"
    saved = _save_plan(output_path, plan)

    result = {
        "plan_path": saved,
        "shots": shot_count,
        "target_duration": target,
        "estimated_cost": plan["estimated_cost"],
    }
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Subcommand: storyboard
# ---------------------------------------------------------------------------

def cmd_storyboard(args):
    """Generate start/end frame image pairs for each shot."""
    plan = _load_plan(args.plan)
    api_key = _load_api_key(args.api_key)
    output_dir = Path(args.output or _default_output("storyboard"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save a copy of the plan into the storyboard dir for later reference
    _save_plan(output_dir / "plan.json", plan)

    generate_script = _resolve_script(["banana", "scripts", "generate.py"])
    if not generate_script.exists():
        _error_exit(f"Image generation script not found: {generate_script}")

    results = []
    frames_generated = 0
    total_cost = 0.0

    for shot in plan["shots"]:
        num = shot["number"]

        if not shot.get("start_frame_prompt") or not shot.get("end_frame_prompt"):
            _progress({
                "skipped": num,
                "reason": "missing start_frame_prompt or end_frame_prompt",
            })
            continue

        _progress({"status": "generating_storyboard", "shot": num, "frame": "start"})

        # Generate start frame
        start_result = _run_script(generate_script, [
            "--prompt", shot["start_frame_prompt"],
            "--aspect-ratio", "16:9",
            "--resolution", "2K",
        ], api_key)

        start_src = start_result.get("path", "")
        start_dst = str(output_dir / f"start-{num:02d}.png")
        if start_src and Path(start_src).exists():
            _copy_file(start_src, start_dst)
        else:
            _progress({"warning": f"No output for shot {num} start frame"})
            continue

        _progress({"status": "generating_storyboard", "shot": num, "frame": "end"})

        # Generate end frame
        end_result = _run_script(generate_script, [
            "--prompt", shot["end_frame_prompt"],
            "--aspect-ratio", "16:9",
            "--resolution", "2K",
        ], api_key)

        end_src = end_result.get("path", "")
        end_dst = str(output_dir / f"end-{num:02d}.png")
        if end_src and Path(end_src).exists():
            _copy_file(end_src, end_dst)
        else:
            _progress({"warning": f"No output for shot {num} end frame"})
            continue

        frames_generated += 2
        total_cost += 2 * COST_STORYBOARD_FRAME

        results.append({
            "shot": num,
            "start_frame": start_dst,
            "end_frame": end_dst,
        })

    # Save storyboard manifest
    manifest = {
        "plan": args.plan,
        "storyboard_dir": str(output_dir.resolve()),
        "frames": results,
        "frames_generated": frames_generated,
        "shots": len(results),
        "cost": round(total_cost, 2),
    }
    _save_plan(output_dir / "storyboard.json", manifest)

    print(json.dumps({
        "storyboard_dir": str(output_dir.resolve()),
        "frames_generated": frames_generated,
        "shots": len(results),
        "cost": round(total_cost, 2),
    }, indent=2))


# ---------------------------------------------------------------------------
# Subcommand: estimate
# ---------------------------------------------------------------------------

def cmd_estimate(args):
    """Print cost estimate from an existing plan.

    Honors per-shot, sequence-level, and --quality-tier model overrides.
    Shows a per-tier breakdown so users see why draft-then-final saves money.
    """
    plan = _load_plan(args.plan)
    shots = plan.get("shots", [])
    shot_count = len(shots)

    filled = sum(
        1 for s in shots
        if s.get("start_frame_prompt") and s.get("end_frame_prompt")
    )

    storyboard_cost = shot_count * 2 * COST_STORYBOARD_FRAME
    total_duration = sum(s.get("duration", DEFAULT_SHOT_DURATION) for s in shots)

    override = QUALITY_TIER_MODELS.get(getattr(args, "quality_tier", None))

    # Tier breakdown: { model: {"shots": N, "duration": S, "cost": C} }
    breakdown = {}
    video_cost = 0.0
    for shot in shots:
        duration = shot.get("duration", DEFAULT_SHOT_DURATION)
        model = _resolve_shot_model(shot, plan, override=override)
        per_shot = _veo_cost(model, duration) or 0.0
        video_cost += per_shot
        entry = breakdown.setdefault(model, {"shots": 0, "duration": 0, "cost": 0.0})
        entry["shots"] += 1
        entry["duration"] += duration
        entry["cost"] = round(entry["cost"] + per_shot, 4)

    result = {
        "shots": shot_count,
        "shots_ready": filled,
        "total_duration": total_duration,
        "estimated_cost": {
            "storyboard_frames": round(storyboard_cost, 2),
            "video_clips": round(video_cost, 2),
            "total": round(storyboard_cost + video_cost, 2),
            "per_model": breakdown,
        },
    }
    if override:
        result["quality_tier_override"] = override
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# Subcommand: generate
# ---------------------------------------------------------------------------

def cmd_generate(args):
    """Generate video clips from approved storyboard frames."""
    storyboard_dir = Path(args.storyboard)
    if not storyboard_dir.is_dir():
        _error_exit(f"Storyboard directory not found: {storyboard_dir}")

    # Try to load the plan from the storyboard dir or a separate path
    plan_path = storyboard_dir / "plan.json"
    if not plan_path.exists():
        manifest_path = storyboard_dir / "storyboard.json"
        if manifest_path.exists():
            manifest = _load_plan(manifest_path)
            alt = manifest.get("plan")
            if alt and Path(alt).exists():
                plan_path = Path(alt)

    if not plan_path.exists():
        _error_exit(
            f"No plan.json in storyboard dir. "
            f"Run 'storyboard' first or place plan.json in {storyboard_dir}"
        )

    plan = _load_plan(plan_path)
    api_key = _load_api_key(args.api_key)
    output_dir = Path(args.output or _default_output("clips"))
    output_dir.mkdir(parents=True, exist_ok=True)

    video_script = Path(__file__).resolve().parent / "video_generate.py"
    if not video_script.exists():
        _error_exit(f"Video generation script not found: {video_script}")

    override = QUALITY_TIER_MODELS.get(getattr(args, "quality_tier", None))
    sequence_resolution = plan.get("resolution") or DEFAULT_SEQUENCE_RESOLUTION

    results = []
    total_cost = 0.0
    total_duration = 0

    for shot in plan["shots"]:
        num = shot["number"]
        prompt = shot.get("prompt", "")
        if not prompt:
            _progress({"skipped": num, "reason": "no prompt"})
            continue

        start_frame = storyboard_dir / f"start-{num:02d}.png"
        end_frame = storyboard_dir / f"end-{num:02d}.png"

        if not start_frame.exists() or not end_frame.exists():
            _progress({"skipped": num, "reason": "missing storyboard frames"})
            continue

        duration = shot.get("duration", DEFAULT_SHOT_DURATION)
        model = _resolve_shot_model(shot, plan, override=override)
        resolution = shot.get("resolution") or sequence_resolution

        _progress({
            "status": "generating_clip",
            "shot": num,
            "duration": duration,
            "model": model,
            "resolution": resolution,
        })

        cmd_args = [
            "--prompt", prompt,
            "--model", model,
            "--duration", str(duration),
            "--aspect-ratio", "16:9",
            "--resolution", resolution,
            "--first-frame", str(start_frame),
            "--last-frame", str(end_frame),
        ]

        result = _run_script(video_script, cmd_args, api_key)

        # Rename output to sequential clip file
        src_path = result.get("path", "")
        clip_dst = str(output_dir / f"clip-{num:02d}.mp4")
        if src_path and Path(src_path).exists():
            _copy_file(src_path, clip_dst)
        else:
            _progress({"warning": f"No video output for shot {num}"})
            continue

        per_shot_cost = _veo_cost(model, duration) or 0.0
        total_cost += per_shot_cost
        total_duration += duration

        results.append({
            "shot": num,
            "clip": clip_dst,
            "duration": duration,
            "model": model,
            "resolution": resolution,
            "cost": round(per_shot_cost, 4),
        })

    # Save generation manifest
    manifest = {
        "clips_dir": str(output_dir.resolve()),
        "clips": results,
        "clips_generated": len(results),
        "total_duration": total_duration,
        "cost": round(total_cost, 2),
    }
    _save_plan(output_dir / "generate.json", manifest)

    print(json.dumps({
        "clips_dir": str(output_dir.resolve()),
        "clips_generated": len(results),
        "total_duration": total_duration,
        "cost": round(total_cost, 2),
    }, indent=2))


# ---------------------------------------------------------------------------
# Subcommand: stitch
# ---------------------------------------------------------------------------

def cmd_stitch(args):
    """Concatenate clips in order using FFmpeg."""
    clips_dir = Path(args.clips)
    if not clips_dir.is_dir():
        _error_exit(f"Clips directory not found: {clips_dir}")

    clips = sorted(clips_dir.glob("clip-*.mp4"))
    if not clips:
        _error_exit(f"No clip-*.mp4 files found in {clips_dir}")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        _error_exit("FFmpeg not found. Install: brew install ffmpeg")

    # Build concat file list
    list_file = clips_dir / "concat.txt"
    with open(list_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip.resolve()}'\n")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    _progress({"status": "stitching", "clips": len(clips), "output": str(output)})

    try:
        proc = subprocess.run(
            [
                ffmpeg, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        list_file.unlink(missing_ok=True)
        _error_exit("FFmpeg timed out during stitching")

    # Clean up concat list
    list_file.unlink(missing_ok=True)

    if proc.returncode != 0:
        _error_exit(f"FFmpeg failed: {proc.stderr.strip()}")

    # Probe duration with ffprobe if available
    total_duration = 0
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            probe = subprocess.run(
                [
                    ffprobe, "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "csv=p=0",
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if probe.returncode == 0 and probe.stdout.strip():
                total_duration = round(float(probe.stdout.strip()))
        except (subprocess.TimeoutExpired, ValueError):
            pass

    result = {
        "output": str(output.resolve()),
        "duration": total_duration,
        "clips": len(clips),
    }
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Multi-shot video sequence production pipeline",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- plan --
    p_plan = subparsers.add_parser("plan", help="Create a shot-list structure")
    p_plan.add_argument(
        "--script", required=True,
        help="Script description (e.g. '30-second product launch ad')",
    )
    p_plan.add_argument(
        "--target", type=int, required=True,
        help="Target total duration in seconds",
    )
    p_plan.add_argument("--preset", default=None, help="Brand preset name")
    p_plan.add_argument("--output", default=None, help="Output path for shot-list.json")

    # -- storyboard --
    p_sb = subparsers.add_parser(
        "storyboard", help="Generate start/end frame pairs for each shot",
    )
    p_sb.add_argument("--plan", required=True, help="Path to shot-list.json")
    p_sb.add_argument("--api-key", default=None, help="Google AI API key")
    p_sb.add_argument("--output", default=None, help="Output directory for frames")

    # -- estimate --
    p_est = subparsers.add_parser("estimate", help="Print cost estimate from plan")
    p_est.add_argument("--plan", required=True, help="Path to shot-list.json")
    p_est.add_argument(
        "--quality-tier", choices=["draft", "fast", "standard", "lite", "legacy"],
        default=None,
        help="Override model for all shots (draft|fast|standard|legacy)",
    )

    # -- generate --
    p_gen = subparsers.add_parser(
        "generate", help="Generate video clips from storyboard frames",
    )
    p_gen.add_argument(
        "--storyboard", required=True, help="Storyboard directory with frames",
    )
    p_gen.add_argument("--api-key", default=None, help="Google AI API key")
    p_gen.add_argument("--output", default=None, help="Output directory for clips")
    p_gen.add_argument(
        "--quality-tier", choices=["draft", "fast", "standard", "lite", "legacy"],
        default=None,
        help=(
            "Override model for all shots. 'draft' currently maps to Fast "
            "($0.15/sec, 2.7x cheaper than Standard) as the draft-then-final "
            "pass. 'standard' uses the flagship Standard tier for final "
            "renders. 'lite' and 'legacy' are Vertex-AI-only and will fail "
            "with a clear message until the v3.6.0 backend ships. See "
            "references/video-sequences.md for the draft-then-final workflow."
        ),
    )

    # -- stitch --
    p_stitch = subparsers.add_parser(
        "stitch", help="Concatenate clips into final video with FFmpeg",
    )
    p_stitch.add_argument("--clips", required=True, help="Directory containing clip-*.mp4")
    p_stitch.add_argument("--output", required=True, help="Output file path (e.g. final.mp4)")

    args = parser.parse_args()

    dispatch = {
        "plan": cmd_plan,
        "storyboard": cmd_storyboard,
        "estimate": cmd_estimate,
        "generate": cmd_generate,
        "stitch": cmd_stitch,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
