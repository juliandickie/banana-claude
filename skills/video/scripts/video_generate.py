#!/usr/bin/env python3
"""Banana Claude -- Video Generation via Google VEO 3.1

Generate videos via VEO REST API using async long-running operations.
Uses only Python stdlib (no pip dependencies).

Usage:
    video_generate.py --prompt "a cat jumping in slow motion" [--duration 8]
                      [--aspect-ratio 16:9] [--resolution 1080p]
                      [--model veo-3.1-generate-preview]
                      [--first-frame PATH] [--last-frame PATH]
                      [--reference-image PATH [PATH ...]]
                      [--api-key KEY] [--poll-interval 10] [--max-wait 300]
                      [--output DIR]
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
OPERATIONS_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "veo-3.1-generate-preview"
DEFAULT_DURATION = 8
DEFAULT_RATIO = "16:9"
DEFAULT_RESOLUTION = "1080p"
DEFAULT_POLL_INTERVAL = 10
DEFAULT_MAX_WAIT = 300
OUTPUT_DIR = Path.home() / "Documents" / "nanobanana_generated"

# All VEO 3.x model IDs the plugin knows about. Not every ID is callable
# through every backend — see MODELS_VERTEX_ONLY below.
VALID_MODELS = {
    # Preview IDs — callable on both Gemini API and Vertex AI
    "veo-3.1-generate-preview",       # Standard (flagship, highest quality)
    "veo-3.1-fast-generate-preview",  # Fast (mid tier)
    # GA IDs — callable on Vertex AI only (as of 2026-04-10)
    "veo-3.1-generate-001",           # Standard GA
    "veo-3.1-fast-generate-001",      # Fast GA
    "veo-3.1-lite-generate-001",      # Lite (draft tier, 5-60s range)
    "veo-3.0-generate-001",           # Legacy (predecessor)
}

# These model IDs return HTTP 404 from `generativelanguage.googleapis.com`
# (the Gemini API surface this script uses). They are reachable only via
# Vertex AI's `*-aiplatform.googleapis.com` endpoint with OAuth/service-
# account auth, which the stdlib-only posture of this script cannot
# currently do without pulling in `google-auth` as a dependency.
#
# Verified empirically on 2026-04-10 — see PROGRESS.md session 7.
# Vertex AI backend support is tracked as a v3.6.0 roadmap item.
MODELS_VERTEX_ONLY = {
    "veo-3.1-generate-001",
    "veo-3.1-fast-generate-001",
    "veo-3.1-lite-generate-001",
    "veo-3.0-generate-001",
}

# Scene Extension v2 (`--video-input`) is also Vertex-only as of
# 2026-04-10. The Gemini API rejects the inlineData video part with
# "inlineData isn't supported by this model".
VIDEO_INPUT_VERTEX_ONLY = True

# VEO 3.1 accepts prompts up to 1,024 tokens (English only). We have no
# tokenizer dependency, so approximate using ~4 chars/token for English prose.
# Warn near the limit, hard-reject clearly over.
PROMPT_WARN_CHARS = 3800   # ~950 tokens
PROMPT_ERROR_CHARS = 4500  # ~1,125 tokens

# Generated video download URIs expire 48 hours after creation on Google's
# servers. We download immediately so runtime is safe, but manifests that
# store URIs become stale after this window.
DOWNLOAD_RETENTION_HOURS = 48

# Model-aware parameter constraints. Lite supports a wider range of
# durations (5-60s) and a square aspect ratio (1:1) that the other
# variants reject. See reference doc lines 493-498.
STANDARD_DURATIONS = {4, 6, 8}
LITE_DURATIONS = set(range(5, 61))  # 5..60 inclusive
VALID_DURATIONS_BY_MODEL = {
    "veo-3.1-lite-generate-001": LITE_DURATIONS,
    # All other models fall through to STANDARD_DURATIONS via _valid_durations()
}

STANDARD_RATIOS = {"16:9", "9:16"}
LITE_RATIOS = {"16:9", "9:16", "1:1"}
VALID_RATIOS_BY_MODEL = {
    "veo-3.1-lite-generate-001": LITE_RATIOS,
    # All other models fall through to STANDARD_RATIOS via _valid_ratios()
}

# Lite does NOT support 4K per reference doc line 55, 274.
MODELS_WITHOUT_4K = {"veo-3.1-lite-generate-001", "veo-3.0-generate-001"}

VALID_RESOLUTIONS = {"720p", "1080p", "4K"}


def _valid_durations(model):
    """Return the set of valid durations for a given model."""
    return VALID_DURATIONS_BY_MODEL.get(model, STANDARD_DURATIONS)


def _valid_ratios(model):
    """Return the set of valid aspect ratios for a given model."""
    return VALID_RATIOS_BY_MODEL.get(model, STANDARD_RATIOS)

MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _error_exit(message):
    """Print JSON error to stdout and exit."""
    print(json.dumps({"error": True, "message": message}))
    sys.exit(1)


def _progress(data):
    """Print progress JSON to stderr."""
    print(json.dumps(data), file=sys.stderr)


def _load_api_key(cli_key):
    """Load API key: CLI -> env -> config.json."""
    api_key = cli_key or os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        config_path = Path.home() / ".banana" / "config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    api_key = json.load(f).get("google_ai_api_key", "")
            except (json.JSONDecodeError, OSError):
                pass
    if not api_key:
        _error_exit("No API key. Run /banana setup, set GOOGLE_AI_API_KEY env, or pass --api-key")
    return api_key


def _read_image_base64(path):
    """Read image file, return (base64_string, mime_type)."""
    p = Path(path)
    if not p.exists():
        _error_exit(f"Image not found: {path}")
    ext = p.suffix.lower()
    mime = MIME_MAP.get(ext)
    if not mime:
        _error_exit(f"Unsupported image format '{ext}'. Use: {', '.join(sorted(MIME_MAP))}")
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return data, mime


# Max MP4 size for inline Scene Extension v2 payload. Gemini API's inlineData
# limit is 20 MB; we leave a 5 MB margin for the base64 overhead (33% inflation)
# and other request JSON. A 720p 8s clip is typically 2-5 MB so this is comfortable.
MAX_VIDEO_INPUT_BYTES = 15 * 1024 * 1024  # 15 MB


def _read_video_base64(path):
    """Read MP4 file for Scene Extension v2, return (base64_string, mime_type).

    Enforces a 15 MB cap to stay under the Gemini API inline payload limit.
    For larger videos, the user should extract a last frame and use --first-frame
    instead (see video_extend.py --method keyframe).
    """
    p = Path(path)
    if not p.exists():
        _error_exit(f"Video not found: {path}")
    ext = p.suffix.lower()
    if ext not in (".mp4", ".mov", ".m4v"):
        _error_exit(f"Unsupported video format '{ext}'. Use: .mp4, .mov, .m4v")
    size = p.stat().st_size
    if size > MAX_VIDEO_INPUT_BYTES:
        size_mb = size / (1024 * 1024)
        _error_exit(
            f"Video file too large ({size_mb:.1f} MB). "
            f"Scene Extension v2 limit is 15 MB (Gemini API inline payload). "
            f"For larger videos, use video_extend.py --method keyframe."
        )
    mime_map = {".mp4": "video/mp4", ".mov": "video/quicktime", ".m4v": "video/mp4"}
    mime = mime_map[ext]
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return data, mime


def _http_request(url, data=None, method="GET", max_retries=3):
    """Make HTTP request with retry on 429. Returns parsed JSON."""
    headers = {"Content-Type": "application/json"} if data else {}
    encoded = json.dumps(data).encode("utf-8") if data else None

    for attempt in range(max_retries):
        req = urllib.request.Request(url, data=encoded, headers=headers, method=method)
        try:
            timeout = 120 if method == "POST" else 30
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            if e.code == 429 and attempt < max_retries - 1:
                wait = 10
                _progress({"retry": True, "attempt": attempt + 1, "wait_seconds": wait, "reason": "rate_limited"})
                time.sleep(wait)
                continue
            if e.code == 400:
                try:
                    err_json = json.loads(error_body)
                    msg = err_json.get("error", {}).get("message", error_body)
                except (json.JSONDecodeError, KeyError):
                    msg = error_body
                _error_exit(f"Bad request: {msg}")
            if e.code == 403:
                _error_exit("API key invalid or billing not enabled. Check key at https://aistudio.google.com/apikey")
            _error_exit(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            _error_exit(f"Network error: {e.reason}")

    _error_exit("Max retries exceeded (rate limited)")


def _submit_operation(prompt, model, duration, ratio, resolution, api_key,
                      first_frame=None, last_frame=None, ref_images=None,
                      negative_prompt=None, seed=None, video_input=None):
    """POST generation request, return operation name.

    Generation modes (set by the input parameters):
    - Text-to-Video: prompt only (no image or video input)
    - Image-to-Video: first_frame set
    - First+Last Frame: first_frame + last_frame set
    - Ingredients to Video: ref_images set (up to 3)
    - Scene Extension v2: video_input set (passes previous clip bytes)

    NOTE: video_input is mutually exclusive with first_frame/last_frame/ref_images.
    TODO(v3.6.0): Extract instance-building into a mode-dispatched helper — this
    function is growing to handle 5 distinct modes and would benefit from refactoring.
    """
    url = f"{API_BASE}/{model}:predictLongRunning?key={api_key}"

    instance = {"prompt": prompt}

    if video_input:
        # Scene Extension v2: pass the previous video as inline data.
        # The API will generate a continuation that preserves audio and motion.
        b64, mime = _read_video_base64(video_input)
        instance["video"] = {"inlineData": {"data": b64, "mimeType": mime}}
    else:
        if first_frame:
            b64, mime = _read_image_base64(first_frame)
            instance["image"] = {"inlineData": {"data": b64, "mimeType": mime}}

        if last_frame:
            b64, mime = _read_image_base64(last_frame)
            instance["lastFrame"] = {"inlineData": {"data": b64, "mimeType": mime}}

        if ref_images:
            ref_list = []
            for img_path in ref_images[:3]:
                b64, mime = _read_image_base64(img_path)
                ref_list.append({
                    "image": {"inlineData": {"data": b64, "mimeType": mime}},
                    "referenceType": "asset"
                })
            instance["referenceImages"] = ref_list

    body = {
        "instances": [instance],
        "parameters": {
            "aspectRatio": ratio,
            "sampleCount": 1,
            "durationSeconds": duration,
        },
    }

    if resolution != DEFAULT_RESOLUTION:
        body["parameters"]["resolution"] = resolution

    # Optional generation controls added in v3.5.0.
    # REST API uses camelCase keys: negativePrompt and seed (not snake_case).
    if negative_prompt:
        body["parameters"]["negativePrompt"] = negative_prompt
    if seed is not None:
        body["parameters"]["seed"] = seed

    _progress({"status": "submitting", "model": model, "duration": duration})
    result = _http_request(url, data=body, method="POST")

    op_name = result.get("name")
    if not op_name:
        _error_exit(f"No operation name in response: {json.dumps(result)[:200]}")

    _progress({"status": "submitted", "operation": op_name})
    return op_name


def _poll_operation(operation_name, api_key, interval, max_wait):
    """Poll operation until done. Return response dict."""
    url = f"{OPERATIONS_BASE}/{operation_name}?key={api_key}"
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            _error_exit(f"Timeout: operation not done after {max_wait}s. Operation: {operation_name}")

        result = _http_request(url, method="GET")

        if result.get("done"):
            error = result.get("error")
            if error:
                msg = error.get("message", str(error))
                if "safety" in msg.lower() or "blocked" in msg.lower():
                    _error_exit(f"VIDEO_SAFETY: {msg}")
                _error_exit(f"Operation failed: {msg}")
            return result

        _progress({"polling": True, "elapsed": int(elapsed), "status": "processing"})
        time.sleep(interval)


def _save_video(response, output_dir, api_key=None):
    """Extract video from response, save as MP4, return path."""
    resp_body = response.get("response", {})
    # Try the documented path: response.generateVideoResponse.generatedSamples
    gen_resp = resp_body.get("generateVideoResponse", {})
    samples = gen_resp.get("generatedSamples", [])
    # Fallback to direct path for older API versions
    if not samples:
        samples = resp_body.get("generatedSamples", [])
    if not samples:
        _error_exit(f"No video in response. Response keys: {list(resp_body.keys())}, body: {json.dumps(resp_body)[:300]}")

    video_data = samples[0].get("video", {})
    b64 = video_data.get("bytesBase64Encoded")
    uri = video_data.get("uri")

    if not b64 and not uri:
        _error_exit(f"No video data or URI in response: {json.dumps(video_data)[:200]}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"video_{timestamp}.mp4"
    output_path = (out / filename).resolve()

    if b64:
        _progress({"status": "saving", "source": "base64"})
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64))
    else:
        _progress({"status": "downloading", "uri": uri})
        # Google video URIs require API key authentication
        download_url = uri
        if api_key and "key=" not in uri:
            sep = "&" if "?" in uri else "?"
            download_url = f"{uri}{sep}key={api_key}"
        try:
            req = urllib.request.Request(download_url)
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(output_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            _error_exit(f"Failed to download video: {e}")

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate video via Google VEO 3.1 REST API")
    parser.add_argument("--prompt", required=True, help="Video generation prompt")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION,
                        help=f"Duration in seconds. Standard/Fast/3.0: {{4,6,8}}. "
                             f"Lite: 5-60. (default: {DEFAULT_DURATION})")
    parser.add_argument("--aspect-ratio", default=DEFAULT_RATIO,
                        help=f"Aspect ratio. Standard/Fast/3.0: 16:9 or 9:16. "
                             f"Lite also supports 1:1. (default: {DEFAULT_RATIO})")
    parser.add_argument("--resolution", default=DEFAULT_RESOLUTION,
                        help=f"Resolution: 720p, 1080p, 4K. "
                             f"Lite and 3.0 do not support 4K. (default: {DEFAULT_RESOLUTION})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Model ID. Options: veo-3.1-generate-preview (Standard), "
                             f"veo-3.1-fast-generate-preview (Fast), "
                             f"veo-3.1-lite-generate-001 (Lite/draft), "
                             f"veo-3.0-generate-001 (Legacy). "
                             f"(default: {DEFAULT_MODEL})")
    parser.add_argument("--first-frame", default=None, help="Path to first frame image")
    parser.add_argument("--last-frame", default=None, help="Path to last frame image")
    parser.add_argument("--reference-image", nargs="+", default=None,
                        help="Reference image paths (up to 3)")
    parser.add_argument("--video-input", default=None,
                        help="Path to source MP4 for Scene Extension v2 (mutually exclusive "
                             "with --first-frame/--last-frame/--reference-image; forces 720p). "
                             "Max 15 MB.")
    parser.add_argument("--negative-prompt", default=None,
                        help="What to avoid in the generation (e.g. 'blurry, low quality, distorted')")
    parser.add_argument("--seed", type=int, default=None,
                        help="Integer seed for reproducible results")
    parser.add_argument("--api-key", default=None, help="Google AI API key")
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL,
                        help=f"Seconds between polls (default: {DEFAULT_POLL_INTERVAL})")
    parser.add_argument("--max-wait", type=int, default=DEFAULT_MAX_WAIT,
                        help=f"Max wait seconds (default: {DEFAULT_MAX_WAIT})")
    parser.add_argument("--output", default=str(OUTPUT_DIR),
                        help=f"Output directory (default: {OUTPUT_DIR})")

    args = parser.parse_args()

    # Prompt length sanity check (VEO 3.1 = 1,024 token limit, English only).
    # Approximate: ~4 chars/token for English prose.
    prompt_len = len(args.prompt)
    if prompt_len > PROMPT_ERROR_CHARS:
        _error_exit(
            f"Prompt is {prompt_len} characters (~{prompt_len // 4} tokens). "
            f"VEO 3.1 limit is 1,024 tokens (~4,096 characters). "
            f"Shorten the prompt or split into multiple shots."
        )
    elif prompt_len > PROMPT_WARN_CHARS:
        _progress({
            "warning": "prompt_approaching_limit",
            "chars": prompt_len,
            "estimated_tokens": prompt_len // 4,
            "limit_tokens": 1024,
        })

    # Validate model first so later validations can be model-aware
    if args.model not in VALID_MODELS:
        _error_exit(
            f"Invalid model '{args.model}'. Valid: {sorted(VALID_MODELS)}. "
            f"Tip: use 'veo-3.1-fast-generate-preview' for draft/preview work."
        )

    # Gate Vertex-only model IDs. This script uses the Gemini API surface
    # (`generativelanguage.googleapis.com`) which does not serve Lite, GA
    # `-001` IDs, or Legacy 3.0 as of 2026-04-10. Fail fast with a clear
    # pointer to the v3.6.0 roadmap item so users don't waste time.
    if args.model in MODELS_VERTEX_ONLY:
        fast_fallback = "veo-3.1-fast-generate-preview"
        _error_exit(
            f"'{args.model}' is not available on the Gemini API surface "
            f"(generativelanguage.googleapis.com). It is currently reachable "
            f"only via Vertex AI, which this plugin does not yet support. "
            f"For a cheap draft-quality alternative, use "
            f"--model {fast_fallback} (~$0.15/sec). Vertex AI backend is "
            f"tracked as a v3.6.0 roadmap item — see ROADMAP.md."
        )

    # Model-aware duration validation (Lite supports 5-60s, others only {4,6,8})
    valid_durations = _valid_durations(args.model)
    if args.duration not in valid_durations:
        if args.model == "veo-3.1-lite-generate-001":
            _error_exit(f"Invalid duration {args.duration}. Lite supports 5-60 seconds.")
        _error_exit(
            f"Invalid duration {args.duration} for {args.model}. "
            f"Valid: {sorted(valid_durations)}. "
            f"Tip: for durations outside 4/6/8, use --model veo-3.1-lite-generate-001."
        )

    # Model-aware aspect ratio validation (Lite supports 1:1 in addition to 16:9/9:16)
    valid_ratios = _valid_ratios(args.model)
    if args.aspect_ratio not in valid_ratios:
        _error_exit(
            f"Invalid aspect ratio '{args.aspect_ratio}' for {args.model}. "
            f"Valid: {sorted(valid_ratios)}. "
            f"Tip: for square 1:1, use --model veo-3.1-lite-generate-001."
        )

    # Resolution validation (4K not available on Lite or Legacy)
    if args.resolution not in VALID_RESOLUTIONS:
        _error_exit(f"Invalid resolution '{args.resolution}'. Valid: {sorted(VALID_RESOLUTIONS)}")
    if args.resolution == "4K" and args.model in MODELS_WITHOUT_4K:
        _error_exit(
            f"{args.model} does not support 4K resolution. "
            f"Use 'veo-3.1-generate-preview' or 'veo-3.1-fast-generate-preview' for 4K."
        )

    if args.reference_image and len(args.reference_image) > 3:
        _error_exit("Maximum 3 reference images allowed")

    # Scene Extension v2 validation: --video-input is mutually exclusive with
    # all image-based inputs. Also force 720p since Scene Extension is limited
    # to 720p per the reference doc.
    if args.video_input and VIDEO_INPUT_VERTEX_ONLY:
        _error_exit(
            "--video-input (Scene Extension v2) is not available on the "
            "Gemini API surface this plugin uses. The API rejects the video "
            "inlineData part with 'inlineData isn't supported by this "
            "model'. It is currently reachable only via Vertex AI. For clip "
            "extension, use `video_extend.py --method keyframe` which "
            "extracts the last frame and uses it as the first-frame seed "
            "for the next hop (no audio continuity, but works today). "
            "Vertex AI backend is tracked as a v3.6.0 roadmap item."
        )
    if args.video_input:
        conflicting = []
        if args.first_frame:
            conflicting.append("--first-frame")
        if args.last_frame:
            conflicting.append("--last-frame")
        if args.reference_image:
            conflicting.append("--reference-image")
        if conflicting:
            _error_exit(
                f"--video-input is mutually exclusive with: {', '.join(conflicting)}. "
                f"Scene Extension v2 takes the source video alone as input."
            )
        if args.resolution != "720p":
            # Downgrade silently with a progress message rather than erroring —
            # the user probably just kept the default resolution.
            _progress({
                "status": "resolution_downgraded",
                "reason": "Scene Extension v2 is limited to 720p",
                "from": args.resolution,
                "to": "720p"
            })
            args.resolution = "720p"

    api_key = _load_api_key(args.api_key)
    gen_start = time.time()

    # Step 1: Submit
    operation_name = _submit_operation(
        prompt=args.prompt,
        model=args.model,
        duration=args.duration,
        ratio=args.aspect_ratio,
        resolution=args.resolution,
        api_key=api_key,
        first_frame=args.first_frame,
        last_frame=args.last_frame,
        ref_images=args.reference_image,
        negative_prompt=args.negative_prompt,
        seed=args.seed,
        video_input=args.video_input,
    )

    # Step 2: Poll
    response = _poll_operation(operation_name, api_key, args.poll_interval, args.max_wait)

    # Step 3: Save
    video_path = _save_video(response, args.output, api_key)
    gen_time = round(time.time() - gen_start, 1)

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=DOWNLOAD_RETENTION_HOURS)).isoformat()
    result = {
        "path": video_path,
        "model": args.model,
        "duration": args.duration,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
        "prompt": args.prompt,
        "generation_time_seconds": gen_time,
        "download_expires_at": expires_at,
    }
    if args.first_frame:
        result["first_frame"] = args.first_frame
    if args.last_frame:
        result["last_frame"] = args.last_frame
    if args.video_input:
        result["video_input"] = args.video_input

    print(json.dumps(result, indent=2))
    print(
        f"Note: The source download URI expires in {DOWNLOAD_RETENTION_HOURS} hours. "
        f"The MP4 has been saved to disk at {video_path}.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
