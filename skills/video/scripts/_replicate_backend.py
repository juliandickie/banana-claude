#!/usr/bin/env python3
"""Nano Banana Studio -- Replicate backend helper for Kling video generation.

Pure data-translation layer for the Replicate predictions API. Called by
video_generate.py when --backend replicate is active (v3.8.0+). Has no global
state. Stdlib only.

Why Replicate? Google's VEO 3.1 on Vertex AI won on bake-off spike 5 Phase 1
only against some candidates; in Phase 2 head-to-head playback Kling v3 Std
beat VEO 3.1 on 8 of 15 shot types (VEO won 0), at 7.5x lower cost. This
module wires Kling v3 Std as the default video model and keeps VEO as an
opt-in backup via --provider veo. See:
- spikes/v3.8.0-provider-bakeoff/writeup/v3.8.0-bakeoff-findings.md
- dev-docs/kwaivgi-kling-v3-video-llms.md (canonical Kling input schema)
- dev-docs/replicate-openapi.json (canonical Replicate API contract)

Auth: Replicate uses HTTP Bearer tokens. The same `replicate_api_token`
already stored in ~/.banana/config.json by setup_mcp.py (for the image-gen
side) is reused for video — no new setup flow needed.

Request shape (per POST /v1/models/{owner}/{name}/predictions):

    {
      "input": {
        "prompt":          "...",       # required, max 2500 chars
        "duration":        8,            # int, 3-15 seconds
        "aspect_ratio":    "16:9",      # "16:9" | "9:16" | "1:1"
        "mode":            "pro",       # "standard" (720p) | "pro" (1080p)
        "generate_audio":  true,        # bool
        "negative_prompt": "...",       # optional
        "start_image":     "data:...",  # optional, data URI or URL
        "end_image":       "data:...",  # optional, requires start_image
        "multi_prompt":    "[...]"      # optional, JSON array as STRING
      }
    }

Poll shape (per GET /v1/predictions/{id}):

    {
      "id":         "...",
      "status":     "starting" | "processing" | "succeeded" |
                    "failed"   | "canceled"   | "aborted",
      "output":     "https://replicate.delivery/.../tmp.mp4",  # string for Kling
      "error":      "...",              # when status=failed
      "urls": {
        "get":    "...",
        "cancel": "..."
      }
    }

Prefer header: The Replicate OpenAPI spec documents `Prefer: wait=N` with
N in [1, 60] for synchronous inline completion. The spike client used
`wait=0` which is non-spec-compliant (happens to work). This module OMITS
the Prefer header entirely for async submit — correct for Kling's 3-6 min
wall times — and polls via GET to the prediction URL.

Run this module directly to diagnose the Replicate setup without burning a
Kling generation: `python3 _replicate_backend.py` will ping the free
/v1/account endpoint and report whether the auth path is working.
"""

import argparse
import base64
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ─── Endpoint templates ─────────────────────────────────────────────

# Base URL per the Replicate OpenAPI schema.
REPLICATE_API_BASE = "https://api.replicate.com/v1"

# Model predictions endpoint template. Owner and name are separated by "/"
# in the slug (e.g., "kwaivgi/kling-v3-video").
REPLICATE_PREDICTIONS_URL_TEMPLATE = (
    REPLICATE_API_BASE + "/models/{owner}/{name}/predictions"
)

# Free endpoint used by --diagnose to verify auth without burning a
# generation. Returns the account name + type for the authenticated token.
REPLICATE_ACCOUNT_URL = REPLICATE_API_BASE + "/account"

# User-Agent identifying our client to Replicate. Sent on every request.
# Cloudflare's edge rules reject the default Python-urllib/3.x user agent
# on some endpoints (observed: HTTP 403 error 1010 on /v1/account with no
# User-Agent). Identifying the client avoids the WAF heuristic and gives
# Replicate a way to contact us if they see odd traffic.
REPLICATE_USER_AGENT = "nano-banana-studio/3.8.0 (+https://github.com/juliandickie/nano-banana-studio)"


# ─── Model registry ─────────────────────────────────────────────────

# v3.8.0 ships with a deliberately lean roster: Kling v3 Std only. PrunaAI
# P-Video was considered in spike 5 Phase 1 but the user declined to wire
# it after reviewing the output. Other Replicate models (Kling Omni, Runway,
# xAI Grok, ByteDance Seedance) are deferred — see ROADMAP priorities
# 10a (Seedance retest) and 10b (Omni retest if wall time improves).
REPLICATE_MODELS = {
    "kwaivgi/kling-v3-video": {
        "family": "kling",
        "display_name": "Kling v3 Std",
        "aspects": ["16:9", "9:16", "1:1"],
        "min_duration_s": 3,
        "max_duration_s": 15,
        "modes": ["standard", "pro"],
        "supports_audio": True,
        "supports_multi_prompt": True,
        "supports_negative_prompt": True,
        "supports_start_image": True,
        "supports_end_image": True,
        "price_usd_per_8s_clip_pro": 0.16,
        "price_usd_per_15s_clip_pro": 0.30,
    },
    # v3.8.1: Fabric 1.0 — audio-driven talking head lip-sync specialist.
    # Closes the gap left by v3.8.0 (VEO chars can't speak external voices).
    # Pair with audio_pipeline.py narrate output for custom ElevenLabs voices.
    "veed/fabric-1.0": {
        "family": "fabric",
        "display_name": "VEED Fabric 1.0",
        "resolutions": ["480p", "720p"],
        "max_duration_s": 60,
        "supports_audio_input": True,
        "supports_image_input": True,
        "image_formats": ["jpg", "jpeg", "png"],
        "audio_formats": ["mp3", "wav", "m4a", "aac"],
        # Pricing: Replicate does not publish Fabric per-call cost publicly
        # in the model card. v3.8.1 verification will measure empirically
        # and update this field before release.
        "price_usd_per_call_estimate": 0.30,
    },
}


# ─── Kling v3 Std parameter constraints ─────────────────────────────
# All values below are sourced from the Kling v3 Std model card at
# dev-docs/kwaivgi-kling-v3-video-llms.md. Any changes here must be
# traceable to that file.

VALID_ASPECT_RATIOS = {"16:9", "9:16", "1:1"}
VALID_MODES = {"standard", "pro"}
MIN_DURATION_S = 3
MAX_DURATION_S = 15
MAX_PROMPT_CHARS = 2500
MAX_NEGATIVE_PROMPT_CHARS = 2500
MAX_MULTI_PROMPT_SHOTS = 6
MIN_SHOT_DURATION_S = 1
MAX_START_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB per the model card

# Replicate OpenAPI Prediction.status enum — all 6 values.
RUNNING_STATUSES = {"starting", "processing"}
TERMINAL_SUCCESS_STATUSES = {"succeeded"}
TERMINAL_FAILURE_STATUSES = {"failed", "canceled", "aborted"}

# File extension to MIME type. Replicate accepts .jpg/.jpeg/.png for image
# inputs per the Kling model card. Intentionally narrow — we don't want to
# accept .webp because Kling's model card doesn't list it as supported.
IMAGE_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


# ─── Fabric 1.0 parameter constraints (v3.8.1+) ────────────────────
# Sourced from dev-docs/veed-fabric-1.0-llms.md. Fabric is the lip-sync
# specialist: image + audio → talking-head MP4. Dramatically simpler
# input surface than Kling (no prompt, no multi_prompt, no negative_prompt).

VALID_FABRIC_RESOLUTIONS = {"480p", "720p"}
FABRIC_MAX_DURATION_S = 60
MAX_FABRIC_IMAGE_BYTES = 10 * 1024 * 1024  # Conservative — Fabric doesn't publish
MAX_FABRIC_AUDIO_BYTES = 50 * 1024 * 1024  # 60s at reasonable bitrates ≈ 1-5 MB

# Audio extension to MIME type. Fabric model card lists: mp3, wav, m4a, aac.
# Intentionally narrow: don't accept .ogg/.flac/.opus because they aren't listed.
AUDIO_MIME_MAP = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}


# ─── Logger ─────────────────────────────────────────────────────────

# Named logger lets callers attach handlers / tests use self.assertLogs.
_logger = logging.getLogger(__name__)


# ─── Error types ────────────────────────────────────────────────────

class ReplicateBackendError(RuntimeError):
    """Base class for Replicate backend errors.

    Raised by this module when it can't proceed. Callers in video_generate.py
    should catch and translate to _error_exit() JSON for user-facing output.
    """


class ReplicateValidationError(ReplicateBackendError):
    """Pre-flight validation failed — caller passed an invalid parameter.

    Raised by validate_kling_params() and build_kling_request_body() when the
    input would be rejected by Replicate. Catching these locally prevents a
    wasted API call.
    """


class ReplicateAuthError(ReplicateBackendError):
    """Auth failed — missing or invalid Replicate API token.

    Points the user at setup_mcp.py --replicate-key in the error message so
    they can fix it without leaving the terminal.
    """


class ReplicateSubmitError(ReplicateBackendError):
    """Submit POST returned a non-2xx response or unparseable body."""


class ReplicatePollError(ReplicateBackendError):
    """Poll GET returned a non-2xx response or unparseable body."""


# ─── Credentials loader ─────────────────────────────────────────────

def load_replicate_credentials(*, cli_token=None):
    """Load the Replicate API token with the same precedence as setup_mcp.py.

    Precedence:
        1. CLI flag (explicit --replicate-key)
        2. Env var REPLICATE_API_TOKEN
        3. ~/.banana/config.json field replicate_api_token

    Returns a dict with key: api_token.
    Raises ReplicateAuthError with a setup pointer if the token is missing.
    """
    token = cli_token or os.environ.get("REPLICATE_API_TOKEN")

    if not token:
        config_path = Path.home() / ".banana" / "config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
                token = cfg.get("replicate_api_token", "")
            except (json.JSONDecodeError, OSError):
                pass

    if not token:
        raise ReplicateAuthError(
            "No Replicate API token. Set it with:\n"
            "  python3 skills/banana/scripts/setup_mcp.py --replicate-key YOUR_TOKEN\n"
            "Or set the REPLICATE_API_TOKEN environment variable.\n"
            "Get a token at: https://replicate.com/account/api-tokens"
        )
    return {"api_token": token}


# ─── URL builder ────────────────────────────────────────────────────

def build_predictions_url(model_slug):
    """Return the POST URL for a model's predictions endpoint.

    Model slug format: "owner/name" (e.g., "kwaivgi/kling-v3-video").
    """
    if "/" not in model_slug:
        raise ReplicateBackendError(
            f"Invalid model slug '{model_slug}'. Expected 'owner/name' format."
        )
    owner, name = model_slug.split("/", 1)
    return REPLICATE_PREDICTIONS_URL_TEMPLATE.format(owner=owner, name=name)


# ─── Image helpers ──────────────────────────────────────────────────

def image_path_to_data_uri(path):
    """Read an image file and return a single data URI string.

    Format: "data:{mime};base64,{base64_data}"

    Replicate's Kling integration accepts either HTTPS URLs or data URIs
    for start_image / end_image. Data URIs are simpler for the common case
    of local files; the Kling model card specifies a 10 MB cap which this
    function enforces at the boundary.

    Raises ReplicateValidationError if the file is missing, has an
    unsupported extension, or exceeds the 10 MB limit.
    """
    p = Path(path)
    if not p.exists():
        raise ReplicateValidationError(f"Image not found: {path}")
    ext = p.suffix.lower()
    mime = IMAGE_MIME_MAP.get(ext)
    if not mime:
        raise ReplicateValidationError(
            f"Unsupported image format '{ext}'. "
            f"Kling v3 Std accepts: {', '.join(sorted(IMAGE_MIME_MAP))}"
        )
    size = p.stat().st_size
    if size > MAX_START_IMAGE_BYTES:
        mb = size / (1024 * 1024)
        cap_mb = MAX_START_IMAGE_BYTES / (1024 * 1024)
        raise ReplicateValidationError(
            f"Image file too large ({mb:.1f} MB). "
            f"Kling v3 Std start_image/end_image limit is {cap_mb:.0f} MB "
            f"per the model card."
        )
    with open(p, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def audio_path_to_data_uri(path):
    """Read an audio file and return a single data URI string.

    Format: "data:{mime};base64,{base64_data}"

    Fabric 1.0 (v3.8.1+) accepts either HTTPS URLs or data URIs for the
    `audio` field. Mirrors image_path_to_data_uri() but for audio: mp3,
    wav, m4a, aac. Enforces a size cap matching ~60 seconds at typical
    bitrates so users don't accidentally upload huge files.

    Raises ReplicateValidationError if the file is missing, has an
    unsupported extension, or exceeds the size cap.
    """
    p = Path(path)
    if not p.exists():
        raise ReplicateValidationError(f"Audio not found: {path}")
    ext = p.suffix.lower()
    mime = AUDIO_MIME_MAP.get(ext)
    if not mime:
        raise ReplicateValidationError(
            f"Unsupported audio format '{ext}'. "
            f"Fabric 1.0 accepts: {', '.join(sorted(AUDIO_MIME_MAP))}"
        )
    size = p.stat().st_size
    if size > MAX_FABRIC_AUDIO_BYTES:
        mb = size / (1024 * 1024)
        cap_mb = MAX_FABRIC_AUDIO_BYTES / (1024 * 1024)
        raise ReplicateValidationError(
            f"Audio file too large ({mb:.1f} MB). "
            f"Fabric 1.0 cap is {cap_mb:.0f} MB (~60 s at typical bitrates)."
        )
    with open(p, "rb") as f:
        raw = f.read()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


# ─── Parameter validation ───────────────────────────────────────────

def validate_kling_params(
    *,
    aspect_ratio,
    duration,
    mode,
    multi_prompt=None,
    start_image=None,
    end_image=None,
    prompt=None,
    negative_prompt=None,
):
    """Validate Kling v3 Std input against the model card's rules.

    Rules enforced (all sourced from dev-docs/kwaivgi-kling-v3-video-llms.md):

      1. aspect_ratio ∈ {"16:9", "9:16", "1:1"}
      2. duration is an integer in [3, 15]
      3. mode ∈ {"standard", "pro"}
      4. If multi_prompt is provided:
         a. Must be a valid JSON string
         b. Must parse to a list of shot objects
         c. Max 6 shots
         d. Each shot.duration >= 1 second
         e. sum(shot.duration for shot in shots) == duration  ← MOST CRITICAL
      5. If end_image is provided, start_image must also be provided
      6. If prompt is provided, must be <= 2500 chars
      7. If negative_prompt is provided, must be <= 2500 chars

    Non-blocking warning:
      - If both aspect_ratio AND start_image are provided, the model card
        says aspect_ratio is ignored. We log a WARNING so the caller knows.

    Raises ReplicateValidationError on any rule violation. Returns None.
    """
    # 1. aspect_ratio
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        raise ReplicateValidationError(
            f"Invalid aspect_ratio '{aspect_ratio}'. "
            f"Kling v3 Std supports: {sorted(VALID_ASPECT_RATIOS)}."
        )

    # 2. duration
    if not isinstance(duration, int) or not (MIN_DURATION_S <= duration <= MAX_DURATION_S):
        raise ReplicateValidationError(
            f"Invalid duration {duration!r}. "
            f"Kling v3 Std supports integer seconds in "
            f"[{MIN_DURATION_S}, {MAX_DURATION_S}]."
        )

    # 3. mode
    if mode not in VALID_MODES:
        raise ReplicateValidationError(
            f"Invalid mode '{mode}'. "
            f"Kling v3 Std supports: {sorted(VALID_MODES)}."
        )

    # 4. multi_prompt (the hard one)
    if multi_prompt is not None:
        try:
            shots = json.loads(multi_prompt)
        except json.JSONDecodeError as e:
            raise ReplicateValidationError(
                f"multi_prompt is not valid JSON: {e}. "
                f"Expected a JSON array string per the Kling model card."
            ) from None
        if not isinstance(shots, list):
            raise ReplicateValidationError(
                f"multi_prompt must be a JSON array, got "
                f"{type(shots).__name__}."
            )
        if len(shots) > MAX_MULTI_PROMPT_SHOTS:
            raise ReplicateValidationError(
                f"multi_prompt has {len(shots)} shots; max is "
                f"{MAX_MULTI_PROMPT_SHOTS} per the Kling model card."
            )
        if len(shots) == 0:
            raise ReplicateValidationError(
                "multi_prompt must contain at least one shot."
            )
        total_shot_duration = 0
        for i, shot in enumerate(shots):
            if not isinstance(shot, dict):
                raise ReplicateValidationError(
                    f"multi_prompt shot {i} is not an object: {shot!r}"
                )
            shot_dur = shot.get("duration")
            if not isinstance(shot_dur, int) or shot_dur < MIN_SHOT_DURATION_S:
                raise ReplicateValidationError(
                    f"multi_prompt shot {i} has invalid duration "
                    f"{shot_dur!r}; must be integer >= "
                    f"{MIN_SHOT_DURATION_S} second."
                )
            total_shot_duration += shot_dur
        # THIS is the critical rule from the Kling model card:
        # "total must equal duration"
        if total_shot_duration != duration:
            raise ReplicateValidationError(
                f"multi_prompt shot durations sum to {total_shot_duration}, "
                f"but duration is {duration}. The Kling model card requires "
                f"sum(shot.duration) == duration."
            )

    # 5. end_image requires start_image
    if end_image is not None and start_image is None:
        raise ReplicateValidationError(
            "end_image requires start_image. Kling's first-and-last frame "
            "mode uses both images to constrain the generation."
        )

    # 6-7. prompt / negative_prompt length
    if prompt is not None and len(prompt) > MAX_PROMPT_CHARS:
        raise ReplicateValidationError(
            f"prompt is {len(prompt)} chars; max is {MAX_PROMPT_CHARS} "
            f"per the Kling model card."
        )
    if negative_prompt is not None and len(negative_prompt) > MAX_NEGATIVE_PROMPT_CHARS:
        raise ReplicateValidationError(
            f"negative_prompt is {len(negative_prompt)} chars; max is "
            f"{MAX_NEGATIVE_PROMPT_CHARS} per the Kling model card."
        )

    # Non-blocking warning: aspect_ratio is ignored when start_image is set.
    if start_image is not None and aspect_ratio is not None:
        _logger.warning(
            "aspect_ratio='%s' will be IGNORED by Kling because start_image "
            "is provided. The output will use the start image's native "
            "aspect ratio per the Kling v3 Std model card.",
            aspect_ratio,
        )


def validate_fabric_params(*, image, audio, resolution="720p"):
    """Validate Fabric 1.0 input against the model card's rules.

    Rules enforced (all sourced from dev-docs/veed-fabric-1.0-llms.md):

      1. resolution ∈ {"480p", "720p"}
      2. image file exists and has extension in {.jpg, .jpeg, .png}
      3. audio file exists and has extension in {.mp3, .wav, .m4a, .aac}

    Fabric's input surface is dramatically simpler than Kling's — no prompt,
    no multi_prompt, no duration parameter (derived from audio length), no
    negative_prompt. The validator only has three things to check.

    `image` and `audio` must be pathlib.Path objects (or anything Path()
    can accept). Strings are also accepted.

    Raises ReplicateValidationError on any rule violation. Returns None.
    """
    # 1. resolution
    if resolution not in VALID_FABRIC_RESOLUTIONS:
        raise ReplicateValidationError(
            f"Invalid resolution '{resolution}'. "
            f"Fabric 1.0 supports: {sorted(VALID_FABRIC_RESOLUTIONS)}."
        )

    # 2. image
    image_path = Path(image)
    if not image_path.exists():
        raise ReplicateValidationError(f"Image not found: {image}")
    image_ext = image_path.suffix.lower()
    if image_ext not in IMAGE_MIME_MAP:
        raise ReplicateValidationError(
            f"Unsupported image format '{image_ext}'. "
            f"Fabric 1.0 accepts: {', '.join(sorted(IMAGE_MIME_MAP))} "
            f"per the model card."
        )

    # 3. audio
    audio_path = Path(audio)
    if not audio_path.exists():
        raise ReplicateValidationError(f"Audio not found: {audio}")
    audio_ext = audio_path.suffix.lower()
    if audio_ext not in AUDIO_MIME_MAP:
        raise ReplicateValidationError(
            f"Unsupported audio format '{audio_ext}'. "
            f"Fabric 1.0 accepts: {', '.join(sorted(AUDIO_MIME_MAP))} "
            f"per the model card."
        )


# ─── Request body builder ───────────────────────────────────────────

def build_kling_request_body(
    prompt,
    *,
    duration,
    aspect_ratio,
    mode="pro",
    negative_prompt=None,
    start_image=None,
    end_image=None,
    multi_prompt=None,
    generate_audio=True,
):
    """Build the JSON dict to serialize for POST /v1/models/.../predictions.

    Wraps the input parameters in the Replicate-required `{"input": {...}}`
    envelope. Returns a dict ready to be JSON-serialized and POSTed.

    Only fields with non-None values are included in the "input" dict, to
    keep the request body minimal and match the examples from the Kling
    model card. `generate_audio` is always included because Kling treats
    omission as True (the model card default).

    Does NOT call validate_kling_params() internally — callers should
    validate separately so the error surface is predictable.
    """
    input_dict = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "mode": mode,
        "generate_audio": generate_audio,
    }
    if negative_prompt is not None:
        input_dict["negative_prompt"] = negative_prompt
    if start_image is not None:
        input_dict["start_image"] = start_image
    if end_image is not None:
        input_dict["end_image"] = end_image
    if multi_prompt is not None:
        # Per the Kling model card: multi_prompt is a STRING containing a
        # JSON array. We preserve it verbatim — do NOT re-parse and re-
        # serialize because that could reorder fields or drop whitespace
        # in ways that confuse downstream consumers.
        input_dict["multi_prompt"] = multi_prompt
    return {"input": input_dict}


def build_fabric_request_body(image, audio, resolution="720p"):
    """Build the JSON dict to serialize for Fabric 1.0 predictions.

    Wraps the input parameters in the Replicate-required `{"input": {...}}`
    envelope. Returns a dict ready to be JSON-serialized and POSTed.

    Unlike build_kling_request_body(), there are no optional fields — Fabric
    only takes image + audio + resolution. Simpler surface = simpler builder.

    `image` and `audio` can be HTTPS URLs or data URIs (the caller handles
    the file-path-to-data-URI conversion via image_path_to_data_uri() /
    audio_path_to_data_uri() before calling this function).

    Does NOT call validate_fabric_params() internally — callers should
    validate separately so the error surface is predictable.
    """
    return {
        "input": {
            "image": image,
            "audio": audio,
            "resolution": resolution,
        }
    }


# ─── Response parsers ───────────────────────────────────────────────

def parse_replicate_submit_response(response_dict):
    """Extract (prediction_id, poll_url) from a predictions-create response.

    Replicate submit response shape (per OpenAPI):
        {
          "id": "...",
          "status": "starting",
          "urls": {"get": "https://...", "cancel": "https://..."},
          "created_at": "...",
          ...
        }

    Raises ReplicateBackendError if the shape doesn't match.
    """
    if not isinstance(response_dict, dict):
        raise ReplicateBackendError(
            f"Unexpected submit response type: {type(response_dict).__name__}"
        )
    pid = response_dict.get("id")
    if not pid:
        raise ReplicateBackendError(
            f"No prediction id in submit response. "
            f"Keys present: {list(response_dict.keys())}"
        )
    urls = response_dict.get("urls") or {}
    poll_url = urls.get("get")
    if not poll_url:
        raise ReplicateBackendError(
            f"No urls.get in submit response. "
            f"urls keys: {list(urls.keys())}"
        )
    return (pid, poll_url)


def parse_replicate_poll_response(response_dict):
    """Parse a Replicate prediction GET response into a state tuple.

    Returns one of:
        ("running", None)            — still in progress, keep polling
        ("done", output)             — succeeded; output is the URI string
                                       (or list for multi-output models)
        ("failed", error_info)       — failed, canceled, or aborted

    The Replicate Prediction.status enum has 6 values per the OpenAPI schema:
      - starting, processing          → running
      - succeeded                     → done
      - failed, canceled, aborted     → failed

    Note: `aborted` is easy to miss (spike client doesn't know it) and
    represents predictions terminated before predict() was called (queue
    eviction, deadline reached). It must be treated as terminal failure,
    NOT as running — otherwise the poll loop spins forever.
    """
    if not isinstance(response_dict, dict):
        raise ReplicateBackendError(
            f"Unexpected poll response type: {type(response_dict).__name__}"
        )
    status = response_dict.get("status")
    if status in RUNNING_STATUSES:
        return ("running", None)
    if status in TERMINAL_SUCCESS_STATUSES:
        output = response_dict.get("output")
        return ("done", output)
    if status in TERMINAL_FAILURE_STATUSES:
        error_info = response_dict.get("error")
        return ("failed", error_info)
    # Unknown status — defensive fallthrough. Treat as failure so we don't
    # spin-poll forever on an enum value Replicate adds in the future.
    raise ReplicateBackendError(
        f"Unknown prediction status '{status}'. "
        f"Expected one of: {sorted(RUNNING_STATUSES | TERMINAL_SUCCESS_STATUSES | TERMINAL_FAILURE_STATUSES)}"
    )


# ─── HTTP helpers ───────────────────────────────────────────────────

def replicate_post(url, body, *, token, timeout=60):
    """POST a JSON body to a Replicate endpoint and return the parsed JSON.

    Sends `Authorization: Bearer {token}` per the OpenAPI schema. Does NOT
    send a `Prefer: wait` header — the spike's `wait=0` is out-of-spec per
    the regex `^wait(=([1-9]|[1-9][0-9]|60))?$`, and omitting the header
    gives us the correct async-first semantic for Kling's 3-6 min wall times.

    Raises ReplicateSubmitError on non-2xx or unparseable body.
    """
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": REPLICATE_USER_AGENT,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body_text)
            msg = err.get("detail") or err.get("title") or body_text[:500]
            raise ReplicateSubmitError(
                f"Replicate HTTP {e.code}: {msg}"
            ) from None
        except (json.JSONDecodeError, ValueError):
            raise ReplicateSubmitError(
                f"Replicate HTTP {e.code}: {body_text[:500]}"
            ) from None
    except urllib.error.URLError as e:
        raise ReplicateSubmitError(f"Replicate network error: {e.reason}") from None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ReplicateSubmitError(
            f"Replicate returned non-JSON response: {raw[:300]!r}"
        ) from None


def replicate_get(url, *, token, timeout=60):
    """GET from a Replicate endpoint (used for polling prediction status).

    Same auth as replicate_post but without a body. Raises ReplicatePollError
    on non-2xx or unparseable body.
    """
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": REPLICATE_USER_AGENT,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body_text)
            msg = err.get("detail") or err.get("title") or body_text[:500]
            raise ReplicatePollError(
                f"Replicate HTTP {e.code}: {msg}"
            ) from None
        except (json.JSONDecodeError, ValueError):
            raise ReplicatePollError(
                f"Replicate HTTP {e.code}: {body_text[:500]}"
            ) from None
    except urllib.error.URLError as e:
        raise ReplicatePollError(f"Replicate network error: {e.reason}") from None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ReplicatePollError(
            f"Replicate returned non-JSON response: {raw[:300]!r}"
        ) from None


# ─── Diagnose CLI ───────────────────────────────────────────────────

def _cmd_diagnose(args):
    """Diagnose the Replicate setup without burning a Kling generation.

    Pings the free /v1/account endpoint through the same auth path to verify
    credentials are live. Reports token prefix and account info. Exit 0 on
    success, 1 on any failure.
    """
    print("=== Replicate backend diagnose ===")

    try:
        creds = load_replicate_credentials(cli_token=args.replicate_key)
    except ReplicateAuthError as e:
        print(f"FAIL (auth): {e}")
        sys.exit(1)

    token = creds["api_token"]
    token_preview = token[:8] + "..." + token[-4:] if len(token) > 12 else "<short>"
    print(f"  api_token: {token_preview} ({len(token)} chars)")

    print("\n  sanity check: GET /v1/account ...")
    try:
        result = replicate_get(REPLICATE_ACCOUNT_URL, token=token, timeout=30)
    except ReplicatePollError as e:
        print(f"FAIL (sanity check): {e}")
        sys.exit(1)

    username = result.get("username", "<unknown>")
    account_type = result.get("type", "<unknown>")
    print(f"  OK: account = {username} (type: {account_type})")

    print("\n  registered models:")
    for slug, info in REPLICATE_MODELS.items():
        # Each family exposes different capability metadata. Format each
        # family's row appropriately so the diagnose output doesn't KeyError
        # on families with different capability shapes.
        display = info.get("display_name", slug)
        family = info.get("family", "?")
        if family == "kling":
            aspects = ", ".join(info.get("aspects", []))
            min_d = info.get("min_duration_s", "?")
            max_d = info.get("max_duration_s", "?")
            print(
                f"    {slug:30s} — {display} ({min_d}-{max_d}s, {aspects})"
            )
        elif family == "fabric":
            resolutions = ", ".join(info.get("resolutions", []))
            max_d = info.get("max_duration_s", "?")
            print(
                f"    {slug:30s} — {display} (lipsync, ≤{max_d}s, {resolutions})"
            )
        else:
            # Unknown family — show the slug + display name and nothing else.
            print(f"    {slug:30s} — {display}")

    print("\nAll checks passed. Replicate backend is reachable.")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Replicate backend helper for Kling video generation (v3.8.0+)",
    )
    sub = parser.add_subparsers(dest="command")

    p_diag = sub.add_parser(
        "diagnose", help="Verify Replicate auth without burning a generation"
    )
    p_diag.add_argument(
        "--replicate-key",
        default=None,
        help="Override the Replicate API token (else reads env/config)",
    )

    args = parser.parse_args()
    if args.command is None:
        # Default: diagnose
        args = parser.parse_args(["diagnose"])

    if args.command == "diagnose":
        _cmd_diagnose(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
