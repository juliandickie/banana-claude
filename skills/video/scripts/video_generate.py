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
from datetime import datetime
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

VALID_DURATIONS = {4, 6, 8}
VALID_RATIOS = {"16:9", "9:16"}
VALID_RESOLUTIONS = {"720p", "1080p", "4K"}
VALID_MODELS = {"veo-3.1-generate-preview", "veo-3.1-generate-lite-preview"}

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
                      first_frame=None, last_frame=None, ref_images=None):
    """POST generation request, return operation name."""
    url = f"{API_BASE}/{model}:predictLongRunning?key={api_key}"

    instance = {"prompt": prompt}

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
                        help=f"Duration in seconds: {sorted(VALID_DURATIONS)} (default: {DEFAULT_DURATION})")
    parser.add_argument("--aspect-ratio", default=DEFAULT_RATIO,
                        help=f"Aspect ratio (default: {DEFAULT_RATIO})")
    parser.add_argument("--resolution", default=DEFAULT_RESOLUTION,
                        help=f"Resolution (default: {DEFAULT_RESOLUTION})")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--first-frame", default=None, help="Path to first frame image")
    parser.add_argument("--last-frame", default=None, help="Path to last frame image")
    parser.add_argument("--reference-image", nargs="+", default=None,
                        help="Reference image paths (up to 3)")
    parser.add_argument("--api-key", default=None, help="Google AI API key")
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL,
                        help=f"Seconds between polls (default: {DEFAULT_POLL_INTERVAL})")
    parser.add_argument("--max-wait", type=int, default=DEFAULT_MAX_WAIT,
                        help=f"Max wait seconds (default: {DEFAULT_MAX_WAIT})")
    parser.add_argument("--output", default=str(OUTPUT_DIR),
                        help=f"Output directory (default: {OUTPUT_DIR})")

    args = parser.parse_args()

    # Validate inputs
    if args.duration not in VALID_DURATIONS:
        _error_exit(f"Invalid duration {args.duration}. Valid: {sorted(VALID_DURATIONS)}")
    if args.aspect_ratio not in VALID_RATIOS:
        _error_exit(f"Invalid aspect ratio '{args.aspect_ratio}'. Valid: {sorted(VALID_RATIOS)}")
    if args.resolution not in VALID_RESOLUTIONS:
        _error_exit(f"Invalid resolution '{args.resolution}'. Valid: {sorted(VALID_RESOLUTIONS)}")
    if args.model not in VALID_MODELS:
        _error_exit(f"Invalid model '{args.model}'. Valid: {sorted(VALID_MODELS)}")
    if args.reference_image and len(args.reference_image) > 3:
        _error_exit("Maximum 3 reference images allowed")

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
    )

    # Step 2: Poll
    response = _poll_operation(operation_name, api_key, args.poll_interval, args.max_wait)

    # Step 3: Save
    video_path = _save_video(response, args.output, api_key)
    gen_time = round(time.time() - gen_start, 1)

    result = {
        "path": video_path,
        "model": args.model,
        "duration": args.duration,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
        "prompt": args.prompt,
        "generation_time_seconds": gen_time,
    }
    if args.first_frame:
        result["first_frame"] = args.first_frame
    if args.last_frame:
        result["last_frame"] = args.last_frame

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
