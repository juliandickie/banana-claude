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

# Vertex AI backend helper (commit 1 of v3.6.0). This module provides the
# request/response translators for the Vertex AI `instances`/`parameters`
# wrapper shape. It's imported unconditionally because it's stdlib-only
# and has no side effects at import time. The backend path is chosen per
# call by _select_backend() below.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _vertex_backend as vertex  # noqa: E402

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

# Backend selection for --backend auto. v3.6.0 adds a real Vertex AI
# backend (via _vertex_backend.py) that reaches models and features the
# Gemini API surface does not serve.
BACKEND_GEMINI_API = "gemini-api"
BACKEND_VERTEX_AI = "vertex-ai"
BACKEND_AUTO = "auto"
VALID_BACKENDS = {BACKEND_GEMINI_API, BACKEND_VERTEX_AI, BACKEND_AUTO}

# Scene Extension v2 on Vertex has a single fixed durationSeconds. All
# other values are rejected with "supported durations are [7] for
# feature video_extension". Text/image-to-video still use the {4, 6, 8}
# set — this constant applies ONLY when --video-input is set and the
# request is routed to Vertex.
VIDEO_EXTENSION_FIXED_DURATION = 7

# Service-agent cold-start retry tuning. The first Scene Extension v2
# call on a fresh Vertex project returns a transient "Service agents
# are being provisioned" error (code 9) that auto-resolves in ~60-90s.
# We sleep then retry once; a second failure surfaces to the user.
SERVICE_AGENT_RETRY_SECONDS = 90

# VEO 3.1 accepts prompts up to 1,024 tokens (English only). We have no
# tokenizer dependency, so approximate using ~4 chars/token for English prose.
# Warn near the limit, hard-reject clearly over.
PROMPT_WARN_CHARS = 3800   # ~950 tokens
PROMPT_ERROR_CHARS = 4500  # ~1,125 tokens

# Generated video download URIs expire 48 hours after creation on Google's
# servers. We download immediately so runtime is safe, but manifests that
# store URIs become stale after this window.
DOWNLOAD_RETENTION_HOURS = 48

# Model-aware parameter constraints. All VEO 3.1 tiers share the same
# {4, 6, 8} duration set. v3.5.0 documented a 5-60 second range for Lite
# based on unverified docs; real-API testing during v3.6.0 proved this
# wrong — the API explicitly rejects 5-second Lite requests with
# "Unsupported output video duration 5 seconds, supported durations are
# [8,4,6] for feature text_to_video".
STANDARD_DURATIONS = {4, 6, 8}
VALID_DURATIONS_BY_MODEL = {
    # No model-specific overrides — all VEO 3.1 tiers use STANDARD_DURATIONS.
    # Kept as an empty dict so future models with different ranges (e.g. a
    # long-form tier) have a natural place to land.
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


def _select_backend(args):
    """Return which backend to use for this request.

    `--backend auto` routing rules (in precedence order):
    1. `--video-input` set → Vertex (Gemini API rejects inline video)
    2. `--first-frame` / `--last-frame` / `--reference-image` set → Vertex
       (Gemini API rejects the inlineData image parts for VEO as of 2026-04-10)
    3. `--model` is a GA `-001` ID → Vertex (Gemini API returns 404)
    4. `--model` is Lite or Legacy 3.0 → Vertex (Gemini API returns 404)
    5. Otherwise (text-only on a preview ID) → Gemini API (preserves the
       v3.4.x code path for backward compat)

    Explicit `--backend gemini-api` or `--backend vertex-ai` always wins.
    """
    if args.backend != BACKEND_AUTO:
        return args.backend

    # Any form of non-text input forces Vertex.
    if args.video_input or args.first_frame or args.last_frame or args.reference_image:
        return BACKEND_VERTEX_AI

    # Vertex-only model IDs force Vertex.
    if args.model in MODELS_VERTEX_ONLY:
        return BACKEND_VERTEX_AI

    # Text-only on a preview-tier model → Gemini API.
    return BACKEND_GEMINI_API

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


def _submit_gemini_api(prompt, model, duration, ratio, resolution, api_key,
                       first_frame=None, last_frame=None, ref_images=None,
                       negative_prompt=None, seed=None, video_input=None):
    """POST to the Gemini API (generativelanguage.googleapis.com) endpoint.

    Uses the legacy request shape:
      {
        "instances": [{"prompt": "...", "image": {"inlineData": {...}}, ...}],
        "parameters": {...}
      }

    Image parts use `inlineData.data` (Gemini convention) rather than
    `bytesBase64Encoded` (Vertex convention). This is the v3.4.x-compatible
    code path that preserves working text-to-video on Standard/Fast preview
    IDs. As of 2026-04-10 this path does NOT serve image-to-video, Lite, or
    GA -001 IDs — callers should route those through Vertex via _select_backend().
    """
    url = f"{API_BASE}/{model}:predictLongRunning?key={api_key}"

    instance = {"prompt": prompt}

    if video_input:
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

    if negative_prompt:
        body["parameters"]["negativePrompt"] = negative_prompt
    if seed is not None:
        body["parameters"]["seed"] = seed

    _progress({"status": "submitting", "backend": BACKEND_GEMINI_API,
               "model": model, "duration": duration})
    result = _http_request(url, data=body, method="POST")

    op_name = result.get("name")
    if not op_name:
        _error_exit(f"No operation name in response: {json.dumps(result)[:200]}")

    _progress({"status": "submitted", "operation": op_name})
    return op_name


def _submit_vertex_ai(prompt, model, duration, ratio, resolution,
                      vertex_creds,
                      first_frame=None, last_frame=None, ref_images=None,
                      negative_prompt=None, seed=None, video_input=None):
    """POST to the Vertex AI endpoint via _vertex_backend helper.

    Uses the Vertex `instances`/`parameters` wrapper shape with image
    parts encoded as `bytesBase64Encoded` (NOT `inlineData.data`). The
    helper module handles URL composition, request body validation,
    resolution normalization (4K → 4k), and submit response parsing.

    Reference images (`ref_images`) are currently only supported on the
    Gemini API code path. Vertex AI Veo does accept reference images but
    under a different schema name — deferred to v3.6.1.
    """
    if ref_images:
        _error_exit(
            "--reference-image is not yet supported on the Vertex AI backend. "
            "This is a v3.6.1 scope item. For now, use --first-frame or "
            "--last-frame to guide generation, or force "
            "--backend gemini-api (which accepts reference-images but only "
            "for text-to-video on preview model IDs)."
        )
    if last_frame:
        # Vertex AI Veo 3.1 supports first-frame image-to-video and
        # last-frame interpolation, but the latter uses a different
        # request field that we haven't probed empirically. Defer to v3.6.1.
        _error_exit(
            "--last-frame is not yet supported on the Vertex AI backend. "
            "First/last frame interpolation is a v3.6.1 scope item. "
            "Use --first-frame alone for now, or force "
            "--backend gemini-api for the legacy last-frame path."
        )

    try:
        body = vertex.build_vertex_request_body(
            prompt,
            duration=duration,
            aspect_ratio=ratio,
            resolution=resolution,
            image_path=first_frame,
            video_input_path=video_input,
            negative_prompt=negative_prompt,
            seed=seed,
            sample_count=1,
        )
    except vertex.VertexBackendError as e:
        _error_exit(f"Vertex request build failed: {e}")

    url = vertex.build_vertex_url(
        model=model,
        method=vertex.METHOD_SUBMIT,
        project=vertex_creds["project_id"],
        location=vertex_creds["location"],
        api_key=vertex_creds["api_key"],
    )

    _progress({
        "status": "submitting",
        "backend": BACKEND_VERTEX_AI,
        "model": model,
        "duration": duration,
        "project": vertex_creds["project_id"],
        "location": vertex_creds["location"],
    })

    try:
        result = vertex.vertex_post(url, body, timeout=120)
        op_name = vertex.parse_vertex_submit_response(result)
    except vertex.VertexBackendError as e:
        _error_exit(f"Vertex submit failed: {e}")

    _progress({"status": "submitted", "operation": op_name})
    return op_name


def _submit_operation(*, backend, vertex_creds, **kwargs):
    """Dispatch to the right backend.

    kwargs are forwarded to either _submit_gemini_api or _submit_vertex_ai.
    Both take compatible keyword signatures: prompt, model, duration, ratio,
    resolution, first_frame, last_frame, ref_images, negative_prompt, seed,
    video_input. The Gemini path also takes `api_key`; the Vertex path takes
    `vertex_creds` instead. The dispatcher translates.
    """
    if backend == BACKEND_VERTEX_AI:
        return _submit_vertex_ai(vertex_creds=vertex_creds, **kwargs)
    # Gemini API path: the api_key is already in kwargs as api_key=...
    return _submit_gemini_api(**kwargs)


def _poll_gemini_api(operation_name, api_key, interval, max_wait):
    """Poll the Gemini API operation endpoint via GET.

    Gemini API polling shape: GET /v1beta/{operation_name}?key={api_key}
    Returns the raw response dict on done=true.
    """
    url = f"{OPERATIONS_BASE}/{operation_name}?key={api_key}"
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            _error_exit(
                f"Timeout: operation not done after {max_wait}s. "
                f"Operation: {operation_name}"
            )

        result = _http_request(url, method="GET")

        if result.get("done"):
            error = result.get("error")
            if error:
                msg = error.get("message", str(error))
                if "safety" in msg.lower() or "blocked" in msg.lower():
                    _error_exit(f"VIDEO_SAFETY: {msg}")
                _error_exit(f"Operation failed: {msg}")
            return result

        _progress({"polling": True, "backend": BACKEND_GEMINI_API,
                   "elapsed": int(elapsed), "status": "processing"})
        time.sleep(interval)


def _poll_vertex_ai(operation_name, model, vertex_creds, interval, max_wait):
    """Poll the Vertex AI operation via POST :fetchPredictOperation.

    Returns a tuple (status, payload):
      ("done", [bytes, ...])            — video bytes ready to save
      ("service_agent_provisioning",
       error_dict)                      — caller should sleep and retry submit
      error is raised via _error_exit() for any other failure mode.

    Unlike the Gemini API path (which returns the full response dict),
    this path pre-parses and returns the decoded video bytes directly.
    The caller's _save_video path is backend-aware to match.
    """
    url = vertex.build_vertex_url(
        model=model,
        method=vertex.METHOD_POLL,
        project=vertex_creds["project_id"],
        location=vertex_creds["location"],
        api_key=vertex_creds["api_key"],
    )
    body = {"operationName": operation_name}
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            _error_exit(
                f"Timeout: operation not done after {max_wait}s. "
                f"Operation: {operation_name}"
            )

        try:
            result = vertex.vertex_post(url, body, timeout=60)
            status, payload = vertex.parse_vertex_poll_response(result)
        except vertex.VertexBackendError as e:
            _error_exit(f"Vertex poll failed: {e}")

        if status == "running":
            _progress({
                "polling": True,
                "backend": BACKEND_VERTEX_AI,
                "elapsed": int(elapsed),
                "status": "processing",
            })
            time.sleep(interval)
            continue

        if status == "done":
            return ("done", payload)

        if status == "service_agent_provisioning":
            # Surface this up so the caller can decide whether to retry the
            # entire submit+poll cycle. Polling again won't help — the
            # operation is already marked done=true with the error.
            return ("service_agent_provisioning", payload)

        # status == "error": surface the message from the parser
        msg = payload.get("message", str(payload)) if isinstance(payload, dict) else str(payload)
        if "safety" in msg.lower() or "blocked" in msg.lower() or "RAI_FILTERED" in str(payload.get("code", "")):
            _error_exit(f"VIDEO_SAFETY: {msg}")
        _error_exit(f"Vertex operation failed: {msg}")


def _poll_operation(*, backend, operation_name, api_key, vertex_creds, model,
                    interval, max_wait):
    """Dispatch polling to the right backend.

    Returns:
        - For Gemini API: the raw response dict (legacy shape), for _save_video
        - For Vertex: a tuple ("done", [video_bytes, ...]) or
                     ("service_agent_provisioning", error_dict)
    """
    if backend == BACKEND_VERTEX_AI:
        return _poll_vertex_ai(operation_name, model, vertex_creds, interval, max_wait)
    return _poll_gemini_api(operation_name, api_key, interval, max_wait)


def _save_video_gemini_api(response, output_dir, api_key=None):
    """Save video from a Gemini API poll response. Returns the output path.

    The Gemini API returns a response shape that's been through at least
    three variants in this codebase's history:
      - response.generateVideoResponse.generatedSamples[0].video.uri
      - response.generatedSamples[0].video.uri (older path)
      - samples[0].video.bytesBase64Encoded (inline bytes)

    We try each shape in turn. The video URI path requires downloading
    with the API key in the query string; the bytesBase64Encoded path
    writes directly.
    """
    resp_body = response.get("response", {})
    gen_resp = resp_body.get("generateVideoResponse", {})
    samples = gen_resp.get("generatedSamples", [])
    if not samples:
        samples = resp_body.get("generatedSamples", [])
    if not samples:
        _error_exit(
            f"No video in response. Response keys: {list(resp_body.keys())}, "
            f"body: {json.dumps(resp_body)[:300]}"
        )

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


def _save_video_vertex_ai(video_bytes_list, output_dir):
    """Save video bytes already decoded by the Vertex poll path.

    Vertex returns video bytes inline in the poll response, so there's
    no separate download step — just write to disk. The first video in
    the list is saved and its path returned. (sampleCount is pinned to 1
    in v3.6.0; multi-video support is a v3.6.1 scope item.)
    """
    if not video_bytes_list:
        _error_exit("Vertex poll returned an empty video list.")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"video_{timestamp}.mp4"
    output_path = (out / filename).resolve()
    _progress({
        "status": "saving",
        "backend": BACKEND_VERTEX_AI,
        "source": "inline_bytes",
        "bytes": len(video_bytes_list[0]),
    })
    with open(output_path, "wb") as f:
        f.write(video_bytes_list[0])
    return str(output_path)


def _save_video(*, backend, poll_result, output_dir, api_key=None):
    """Dispatch save to the right backend.

    poll_result is whatever _poll_operation returned for this backend:
      - Gemini API: the raw response dict
      - Vertex AI: a tuple (status, payload)
    """
    if backend == BACKEND_VERTEX_AI:
        status, payload = poll_result
        if status != "done":
            _error_exit(
                f"_save_video called for Vertex with status={status!r}; "
                f"expected 'done'. Caller bug."
            )
        return _save_video_vertex_ai(payload, output_dir)
    return _save_video_gemini_api(poll_result, output_dir, api_key=api_key)


def main():
    parser = argparse.ArgumentParser(description="Generate video via Google VEO 3.1 REST API")
    parser.add_argument("--prompt", required=True, help="Video generation prompt")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION,
                        help=f"Duration in seconds. All VEO 3.1 tiers: {{4,6,8}}. "
                             f"Scene Extension v2 (--video-input) uses 7. "
                             f"(default: {DEFAULT_DURATION})")
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
    parser.add_argument("--api-key", default=None, help="Google AI API key (Gemini API backend)")
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL,
                        help=f"Seconds between polls (default: {DEFAULT_POLL_INTERVAL})")
    parser.add_argument("--max-wait", type=int, default=DEFAULT_MAX_WAIT,
                        help=f"Max wait seconds (default: {DEFAULT_MAX_WAIT})")
    parser.add_argument("--output", default=str(OUTPUT_DIR),
                        help=f"Output directory (default: {OUTPUT_DIR})")
    # Backend selection (v3.6.0). `auto` routes to Vertex AI when the
    # request needs features not served by the Gemini API: Lite/GA/Legacy
    # model IDs, image-to-video, or Scene Extension v2.
    parser.add_argument("--backend", default=BACKEND_AUTO, choices=sorted(VALID_BACKENDS),
                        help=f"Which backend to use. 'auto' routes Vertex-only features "
                             f"through Vertex AI and keeps text-to-video on Gemini API. "
                             f"(default: {BACKEND_AUTO})")
    parser.add_argument("--vertex-api-key", default=None,
                        help="Vertex AI API key (bound to service account, format AQ.*). "
                             "Loads from VERTEX_API_KEY env or ~/.banana/config.json if unset.")
    parser.add_argument("--vertex-project", default=None,
                        help="GCP project ID for Vertex AI. Loads from VERTEX_PROJECT_ID env "
                             "or ~/.banana/config.json if unset.")
    parser.add_argument("--vertex-location", default=None,
                        help="Vertex AI region (e.g. us-central1). Loads from VERTEX_LOCATION "
                             "env or ~/.banana/config.json if unset. Defaults to us-central1.")

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

    # Resolve the backend up front so the remaining validations and
    # gates can be backend-aware.
    backend = _select_backend(args)

    # Gate Vertex-only model IDs ONLY on the Gemini API path. When the
    # request is routed to Vertex (either by --backend auto or explicit
    # --backend vertex-ai), these models are fully callable.
    if backend == BACKEND_GEMINI_API and args.model in MODELS_VERTEX_ONLY:
        _error_exit(
            f"'{args.model}' is not available on the Gemini API surface "
            f"(generativelanguage.googleapis.com). It is reachable only via "
            f"Vertex AI. Drop --backend gemini-api (default --backend auto "
            f"will route this model through Vertex automatically) or use "
            f"--model veo-3.1-fast-generate-preview (~$0.15/sec) for the "
            f"Gemini API path."
        )

    # Duration validation. All VEO 3.1 tiers accept {4, 6, 8}.
    # Skipped when the request is Scene Extension v2 on the Vertex backend —
    # that path has its own hard durationSeconds=7 constraint enforced below
    # in the --video-input block and again in build_vertex_request_body.
    skip_duration_check = args.video_input and backend == BACKEND_VERTEX_AI
    if not skip_duration_check:
        valid_durations = _valid_durations(args.model)
        if args.duration not in valid_durations:
            _error_exit(
                f"Invalid duration {args.duration} for {args.model}. "
                f"Valid: {sorted(valid_durations)}."
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
    if args.video_input and backend == BACKEND_GEMINI_API:
        _error_exit(
            "--video-input (Scene Extension v2) is not available on the "
            "Gemini API backend. The API rejects the video inlineData part "
            "with 'inlineData isn't supported by this model'. Use "
            "--backend auto (default) or --backend vertex-ai to route this "
            "through Vertex AI, which v3.6.0 fully supports."
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
        # Vertex AI Scene Extension v2 has a hard durationSeconds=7 constraint.
        # Auto-override from the standard {4,6,8} default so users don't have
        # to think about this. Matches the pattern of the 720p auto-downgrade
        # above: the user probably just kept the default.
        if backend == BACKEND_VERTEX_AI and args.duration != VIDEO_EXTENSION_FIXED_DURATION:
            _progress({
                "status": "duration_overridden",
                "reason": "Scene Extension v2 requires durationSeconds=7",
                "from": args.duration,
                "to": VIDEO_EXTENSION_FIXED_DURATION,
            })
            args.duration = VIDEO_EXTENSION_FIXED_DURATION

    # Load credentials for whichever backend we're going to use.
    # The Gemini API path uses the existing google_ai_api_key; the Vertex
    # path uses vertex_api_key + vertex_project_id + vertex_location.
    api_key = None
    vertex_creds = None
    if backend == BACKEND_GEMINI_API:
        api_key = _load_api_key(args.api_key)
    else:
        try:
            vertex_creds = vertex.load_vertex_credentials(
                cli_api_key=args.vertex_api_key,
                cli_project=args.vertex_project,
                cli_location=args.vertex_location,
            )
        except vertex.VertexAuthError as e:
            _error_exit(str(e))
        _progress({
            "status": "backend_selected",
            "backend": BACKEND_VERTEX_AI,
            "project": vertex_creds["project_id"],
            "location": vertex_creds["location"],
        })

    gen_start = time.time()

    # Submit + Poll loop. The Vertex path may return a transient
    # "service_agent_provisioning" result on the first Scene Extension v2
    # call against a cold project; we catch that and retry once after a
    # 90-second sleep. Gemini API path returns a raw response dict and
    # never hits this case.
    submit_kwargs = dict(
        prompt=args.prompt,
        model=args.model,
        duration=args.duration,
        ratio=args.aspect_ratio,
        resolution=args.resolution,
        first_frame=args.first_frame,
        last_frame=args.last_frame,
        ref_images=args.reference_image,
        negative_prompt=args.negative_prompt,
        seed=args.seed,
        video_input=args.video_input,
    )
    if backend == BACKEND_GEMINI_API:
        submit_kwargs["api_key"] = api_key

    service_agent_retries_left = 1
    while True:
        operation_name = _submit_operation(
            backend=backend,
            vertex_creds=vertex_creds,
            **submit_kwargs,
        )
        poll_result = _poll_operation(
            backend=backend,
            operation_name=operation_name,
            api_key=api_key,
            vertex_creds=vertex_creds,
            model=args.model,
            interval=args.poll_interval,
            max_wait=args.max_wait,
        )

        if (backend == BACKEND_VERTEX_AI
                and isinstance(poll_result, tuple)
                and poll_result[0] == "service_agent_provisioning"):
            if service_agent_retries_left <= 0:
                err = poll_result[1]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                _error_exit(
                    f"Vertex service agents still not provisioned after retry. "
                    f"Original message: {msg}. "
                    f"See https://cloud.google.com/vertex-ai/docs/general/access-control#service-agents"
                )
            service_agent_retries_left -= 1
            _progress({
                "status": "service_agent_provisioning",
                "action": "retrying",
                "sleep_seconds": SERVICE_AGENT_RETRY_SECONDS,
                "note": (
                    "First Scene Extension v2 call on this Vertex project. "
                    "Google is auto-provisioning service agents; retrying once."
                ),
            })
            time.sleep(SERVICE_AGENT_RETRY_SECONDS)
            continue

        break

    video_path = _save_video(
        backend=backend,
        poll_result=poll_result,
        output_dir=args.output,
        api_key=api_key,
    )
    gen_time = round(time.time() - gen_start, 1)

    result = {
        "path": video_path,
        "model": args.model,
        "duration": args.duration,
        "aspect_ratio": args.aspect_ratio,
        "resolution": args.resolution,
        "prompt": args.prompt,
        "generation_time_seconds": gen_time,
        "backend": backend,
    }
    # The 48-hour download expiry only applies to the Gemini API path,
    # which returns a URI the plugin downloads (we already have the bytes
    # locally after _save_video, but users who keep manifests around might
    # try to re-fetch the URI later). Vertex returns video bytes inline
    # in the poll response — no URI, no expiry.
    if backend == BACKEND_GEMINI_API:
        result["download_expires_at"] = (
            datetime.now(timezone.utc) + timedelta(hours=DOWNLOAD_RETENTION_HOURS)
        ).isoformat()

    if args.first_frame:
        result["first_frame"] = args.first_frame
    if args.last_frame:
        result["last_frame"] = args.last_frame
    if args.video_input:
        result["video_input"] = args.video_input

    print(json.dumps(result, indent=2))
    if backend == BACKEND_GEMINI_API:
        print(
            f"Note: The source download URI expires in {DOWNLOAD_RETENTION_HOURS} hours. "
            f"The MP4 has been saved to disk at {video_path}.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
