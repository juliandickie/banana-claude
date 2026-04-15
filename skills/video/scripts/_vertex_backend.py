#!/usr/bin/env python3
"""Banana Claude -- Vertex AI backend helper for VEO video generation.

Pure data-translation layer for the Vertex AI Gemini API surface. Called by
video_generate.py when --backend vertex-ai is active. Has no global state.
Stdlib only.

Why Vertex? The Gemini API surface (generativelanguage.googleapis.com) only
serves text-to-video and only for the preview model IDs. Lite, GA -001 IDs,
image-to-video, reference images, and Scene Extension v2 are all Vertex AI
only. This module is the translator between the existing Gemini API request
shape and the Vertex `instances`/`parameters` wrapper shape.

Auth: Vertex AI supports API-key authentication via query string for
bound-to-service-account keys (the `AQ.*` format created through Express
Mode signup). OAuth is NOT required for this path. Verified empirically
and per Google's docs convention that omits the "Authorization scopes"
section on methods that accept API keys.

Request shape (per POST /v1/{endpoint}:predictLongRunning):

    {
      "instances": [{
        "prompt": "...",
        "image":  {"bytesBase64Encoded": "...", "mimeType": "image/png"},  # optional
        "video":  {"bytesBase64Encoded": "...", "mimeType": "video/mp4"}   # optional (Scene Ext v2)
      }],
      "parameters": {
        "sampleCount":      1,
        "durationSeconds":  4,       # 4/6/8 for text/image; 7 for video_extension
        "aspectRatio":      "16:9",  # "16:9" or "9:16"
        "resolution":       "720p",  # "720p", "1080p", "4k" (lowercase)
        "negativePrompt":   "...",   # optional
        "seed":             42        # optional, 0..4294967295
      }
    }

Polling shape (per POST /v1/{endpoint}:fetchPredictOperation):

    Request:  {"operationName": "projects/.../operations/..."}
    Response: {"name": "...", "done": true|false, "error": {...}, "response": {...}}

    When done=true and no error, response.videos[0] contains
    bytesBase64Encoded + mimeType.

Run this module directly to diagnose the Vertex setup without burning VEO
budget: `python3 _vertex_backend.py` will ping a free Gemini text-gen call
and report whether the auth path is working.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


# ─── Endpoint templates ─────────────────────────────────────────────

# Regional endpoint (recommended). Example region: "us-central1".
# Must use /v1/ explicitly — the google-genai SDK has an open bug (#2079)
# where Veo 3.1 GA calls are incorrectly routed to v1beta1, producing
# RESOURCE_PROJECT_INVALID errors. We hard-code /v1/ to avoid that trap.
VERTEX_REGIONAL_TEMPLATE = (
    "https://{region}-aiplatform.googleapis.com/v1"
    "/projects/{project}/locations/{region}"
    "/publishers/google/models/{model}:{method}?key={key}"
)

# Global endpoint (location=global). Used when the project is configured
# for the global multi-region rather than a specific region. Auth and
# request shape are identical to the regional endpoint; only the URL
# host differs.
VERTEX_GLOBAL_TEMPLATE = (
    "https://aiplatform.googleapis.com/v1"
    "/projects/{project}/locations/global"
    "/publishers/google/models/{model}:{method}?key={key}"
)

# Vertex AI default region for VEO. Empirically verified on us-central1.
# Other regions may work but haven't been tested.
VERTEX_DEFAULT_LOCATION = "us-central1"

# Valid method names we call on VEO models.
METHOD_SUBMIT = "predictLongRunning"
METHOD_POLL = "fetchPredictOperation"

# Scene Extension v2 has a hard duration constraint that differs from
# text/image-to-video. The API error on mismatch is:
#   "Unsupported output video duration N seconds,
#    supported durations are [7] for feature video_extension"
VIDEO_EXTENSION_FIXED_DURATION = 7

# Vertex AI uses lowercase "4k" while the existing Gemini API code path
# uses "4K" (uppercase). Normalize at the request boundary.
RESOLUTION_NORMALIZATION = {"4K": "4k"}

# Valid aspect ratios per Vertex docs. v3.5.0 documented "1:1" for Lite
# but that claim was wrong on two counts (Vertex rejects 1:1 for all VEO
# 3.1 tiers and the SDK enum only lists 16:9 and 9:16).
VALID_ASPECT_RATIOS = {"16:9", "9:16"}

# File extension to MIME type. Kept local so this module doesn't depend
# on video_generate.py's MIME_MAP — the two should agree by convention
# but not by import.
IMAGE_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}
VIDEO_MIME_MAP = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".m4v": "video/mp4",
}


# ─── Error types ────────────────────────────────────────────────────

class VertexBackendError(RuntimeError):
    """Base class for Vertex backend errors.

    Raised by this module when it can't proceed. Callers in video_generate.py
    should catch and translate to _error_exit() JSON for user-facing output.
    """


class VertexServiceAgentProvisioning(VertexBackendError):
    """Transient error on first Scene Extension v2 call on a cold project.

    The Vertex API returns code 9 (FAILED_PRECONDITION) with a message
    containing "Service agents are being provisioned". This is a one-time
    auto-setup that takes ~60-90 seconds. Callers should retry once after
    sleeping.

    See:
    https://cloud.google.com/vertex-ai/docs/general/access-control#service-agents
    """


class VertexAuthError(VertexBackendError):
    """Auth failed — missing credentials, wrong project, or expired key."""


# ─── Credentials loader ─────────────────────────────────────────────

def load_vertex_credentials(
    *,
    cli_api_key=None,
    cli_project=None,
    cli_location=None,
):
    """Load Vertex credentials with the same precedence as _load_api_key.

    Precedence:
        1. CLI flag (explicit --vertex-api-key / --vertex-project / --vertex-location)
        2. Env var (VERTEX_API_KEY / VERTEX_PROJECT_ID / VERTEX_LOCATION)
        3. ~/.banana/config.json fields vertex_api_key / vertex_project_id / vertex_location

    Returns a dict with keys: api_key, project_id, location.
    Raises VertexAuthError with a helpful setup pointer if any field is missing.
    """
    api_key = cli_api_key or os.environ.get("VERTEX_API_KEY")
    project = cli_project or os.environ.get("VERTEX_PROJECT_ID")
    location = cli_location or os.environ.get("VERTEX_LOCATION")

    if not (api_key and project and location):
        config_path = Path.home() / ".banana" / "config.json"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    cfg = json.load(f)
                api_key = api_key or cfg.get("vertex_api_key", "")
                project = project or cfg.get("vertex_project_id", "")
                location = location or cfg.get("vertex_location", "")
            except (json.JSONDecodeError, OSError):
                pass

    # Fall back to the default location only if api_key + project are set.
    if api_key and project and not location:
        location = VERTEX_DEFAULT_LOCATION

    if not api_key:
        raise VertexAuthError(
            "No Vertex AI API key. Set vertex_api_key in ~/.banana/config.json, "
            "VERTEX_API_KEY env var, or pass --vertex-api-key. "
            "See docs/plans/v3.6.0-plan.md for setup steps."
        )
    if not project:
        raise VertexAuthError(
            "No Vertex AI project ID. Set vertex_project_id in "
            "~/.banana/config.json, VERTEX_PROJECT_ID env var, or pass "
            "--vertex-project."
        )
    return {"api_key": api_key, "project_id": project, "location": location}


# ─── URL builder ────────────────────────────────────────────────────

def build_vertex_url(*, model, method, project, location, api_key):
    """Return the POST URL for a Vertex AI VEO operation.

    Branches on location: 'global' uses the bare aiplatform.googleapis.com
    host, everything else uses the regional {region}-aiplatform prefix.
    """
    if method not in (METHOD_SUBMIT, METHOD_POLL):
        raise VertexBackendError(
            f"Unknown Vertex method '{method}'. Expected one of: "
            f"{METHOD_SUBMIT}, {METHOD_POLL}"
        )
    template = (
        VERTEX_GLOBAL_TEMPLATE if location == "global" else VERTEX_REGIONAL_TEMPLATE
    )
    return template.format(
        region=location,
        project=project,
        model=model,
        method=method,
        key=api_key,
    )


# ─── Request body builder ───────────────────────────────────────────

def _read_image_base64(path):
    """Read an image file, return (base64_string, mime_type).

    Mirrors video_generate._read_image_base64 but without the shared
    MIME_MAP import — the two maps are maintained by convention.
    """
    p = Path(path)
    if not p.exists():
        raise VertexBackendError(f"Image not found: {path}")
    ext = p.suffix.lower()
    mime = IMAGE_MIME_MAP.get(ext)
    if not mime:
        raise VertexBackendError(
            f"Unsupported image format '{ext}'. "
            f"Use: {', '.join(sorted(IMAGE_MIME_MAP))}"
        )
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return data, mime


def _read_video_base64(path, max_bytes=15 * 1024 * 1024):
    """Read an MP4 for Scene Extension v2, return (base64_string, mime_type).

    Enforces a 15 MB cap by default. Larger inputs should go through GCS
    upload via `gcsUri` — that's a v3.6.1 enhancement.
    """
    p = Path(path)
    if not p.exists():
        raise VertexBackendError(f"Video not found: {path}")
    ext = p.suffix.lower()
    mime = VIDEO_MIME_MAP.get(ext)
    if not mime:
        raise VertexBackendError(
            f"Unsupported video format '{ext}'. "
            f"Use: {', '.join(sorted(VIDEO_MIME_MAP))}"
        )
    size = p.stat().st_size
    if size > max_bytes:
        mb = size / (1024 * 1024)
        cap_mb = max_bytes / (1024 * 1024)
        raise VertexBackendError(
            f"Video file too large ({mb:.1f} MB). "
            f"Scene Extension v2 inline base64 limit is {cap_mb:.0f} MB. "
            f"For larger clips, use video_extend.py --method keyframe, "
            f"or wait for v3.6.1 GCS upload support."
        )
    with open(p, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    return data, mime


def build_vertex_request_body(
    prompt,
    *,
    duration,
    aspect_ratio,
    resolution,
    image_path=None,
    last_frame_path=None,
    reference_image_paths=None,
    video_input_path=None,
    negative_prompt=None,
    seed=None,
    sample_count=1,
):
    """Build the JSON dict to serialize for :predictLongRunning.

    Input modes (set by which of the four path arguments are non-None):

      - Text-to-video: all None
      - Image-to-video: image_path only
      - First-and-last-frame interpolation: image_path + last_frame_path
      - Reference-image-guided: reference_image_paths (up to 3)
      - Scene Extension v2: video_input_path only

    Mutual exclusions:
      - video_input_path cannot combine with ANY image input
      - last_frame_path requires image_path (lastFrame is always paired with image)
      - reference_image_paths cannot combine with image_path or last_frame_path
        (per Vertex docs: reference images and first/last frame are separate modes)

    Validation done at the boundary to prevent known-bad requests:

    - aspect_ratio must be in {"16:9", "9:16"} — v3.5.0 Lite 1:1 claim was wrong
    - resolution is normalized to lowercase (4K → 4k)
    - video_input_path forces Scene Extension v2 mode, which requires
      durationSeconds=7 (enforced by API).
    - reference_image_paths is capped at 3 entries per the Vertex docs.

    Per Vertex docs (https://docs.cloud.google.com/vertex-ai/generative-ai/docs/
    video/generate-videos-from-first-and-last-frames), first+last frame mode
    supports veo-3.1-generate-preview, -fast-generate-preview, -generate-001,
    -fast-generate-001, and -lite-generate-001. All five plugin-registered
    VEO 3.1 model IDs are covered; veo-3.0-generate-001 is NOT supported for
    this feature. The caller is responsible for model-specific routing.
    """
    if aspect_ratio not in VALID_ASPECT_RATIOS:
        raise VertexBackendError(
            f"Invalid aspect ratio '{aspect_ratio}'. "
            f"Vertex AI VEO 3.1 supports: {sorted(VALID_ASPECT_RATIOS)}. "
            f"(v3.5.0 documented '1:1' for Lite but that claim was wrong.)"
        )

    # Normalize resolution at the boundary. Vertex uses lowercase "4k"
    # while the plugin's existing code uses "4K". We convert one-way here
    # so the rest of the plugin can keep its uppercase convention.
    resolution_normalized = RESOLUTION_NORMALIZATION.get(resolution, resolution)

    # Mutual-exclusion checks.
    if video_input_path and (image_path or last_frame_path or reference_image_paths):
        raise VertexBackendError(
            "video_input_path is mutually exclusive with image/last_frame/"
            "reference inputs. Scene Extension v2 takes the source video alone."
        )
    if last_frame_path and not image_path:
        raise VertexBackendError(
            "last_frame_path requires image_path. First/last frame "
            "interpolation uses both frames to constrain the generation."
        )
    if reference_image_paths and (image_path or last_frame_path):
        raise VertexBackendError(
            "reference_image_paths is mutually exclusive with image_path and "
            "last_frame_path. Reference images guide content/style while "
            "first/last frame pins the generation's endpoints — the two "
            "modes use different Vertex code paths."
        )
    if reference_image_paths and len(reference_image_paths) > 3:
        raise VertexBackendError(
            f"Maximum 3 reference images allowed, got {len(reference_image_paths)}."
        )

    if video_input_path and duration != VIDEO_EXTENSION_FIXED_DURATION:
        raise VertexBackendError(
            f"Scene Extension v2 requires durationSeconds="
            f"{VIDEO_EXTENSION_FIXED_DURATION}, got {duration}. "
            f"video_generate.py should auto-override this before calling "
            f"build_vertex_request_body."
        )

    instance = {"prompt": prompt}

    if image_path:
        img_b64, img_mime = _read_image_base64(image_path)
        instance["image"] = {
            "bytesBase64Encoded": img_b64,
            "mimeType": img_mime,
        }
        # `lastFrame` is a sibling of `image` at the instance level. Field
        # name is literal camelCase (confirmed from both the Vertex and
        # Gemini API REST reference pages on 2026-04-11).
        if last_frame_path:
            last_b64, last_mime = _read_image_base64(last_frame_path)
            instance["lastFrame"] = {
                "bytesBase64Encoded": last_b64,
                "mimeType": last_mime,
            }
    elif reference_image_paths:
        # `referenceImages` is an array of {image, referenceType} objects
        # at the instance level. Each image uses the same bytesBase64Encoded
        # wrapper as the primary `image` field. referenceType is "asset"
        # per the official Google Veo 3 notebook and the Gemini API docs
        # (both sources confirmed on 2026-04-11).
        ref_list = []
        for ref_path in reference_image_paths:
            ref_b64, ref_mime = _read_image_base64(ref_path)
            ref_list.append({
                "image": {
                    "bytesBase64Encoded": ref_b64,
                    "mimeType": ref_mime,
                },
                "referenceType": "asset",
            })
        instance["referenceImages"] = ref_list
    elif video_input_path:
        vid_b64, vid_mime = _read_video_base64(video_input_path)
        instance["video"] = {
            "bytesBase64Encoded": vid_b64,
            "mimeType": vid_mime,
        }

    parameters = {
        "sampleCount": sample_count,
        "durationSeconds": duration,
        "aspectRatio": aspect_ratio,
        "resolution": resolution_normalized,
    }
    if negative_prompt:
        parameters["negativePrompt"] = negative_prompt
    if seed is not None:
        parameters["seed"] = int(seed)

    return {"instances": [instance], "parameters": parameters}


# ─── Response parsers ───────────────────────────────────────────────

def parse_vertex_submit_response(response_dict):
    """Extract the operation name from a :predictLongRunning response.

    Vertex submit response shape:
        {"name": "projects/.../operations/<uuid>"}

    Raises VertexBackendError if the response doesn't match the expected
    shape — this catches API changes, wrong URL patterns, or RAI rejections
    at submit time.
    """
    if not isinstance(response_dict, dict):
        raise VertexBackendError(
            f"Unexpected submit response type: {type(response_dict).__name__}"
        )
    op = response_dict.get("name")
    if not op:
        raise VertexBackendError(
            f"No operation name in submit response. "
            f"Keys present: {list(response_dict.keys())}"
        )
    return op


def is_service_agent_provisioning_error(error_dict):
    """True if the error is the transient service-agent cold-start error.

    Vertex returns this on the FIRST Scene Extension v2 call on a project
    whose Vertex AI Service Agent IAM binding hasn't been auto-provisioned
    yet. The error resolves itself in ~60-90 seconds as Google's backend
    creates the service account binding.

    Error shape (from our empirical probe):
        {
          "code": 9,
          "message": "Service agents are being provisioned ... "
                     "please try again in a few minutes."
        }
    """
    if not isinstance(error_dict, dict):
        return False
    code = error_dict.get("code")
    message = error_dict.get("message", "")
    # Match on message text because the numeric code 9 (FAILED_PRECONDITION)
    # is used for other errors too; the message is the discriminator.
    return code == 9 and "Service agents are being provisioned" in message


def parse_vertex_poll_response(response_dict):
    """Parse a :fetchPredictOperation poll response.

    Returns a tuple describing the operation state:

        ("running", None)              — still in progress, keep polling
        ("done", [bytes, ...])         — finished successfully, video bytes returned
        ("error", error_dict)          — finished with error; caller should inspect
        ("service_agent_provisioning", error_dict)
                                       — transient; caller should sleep and retry

    The video bytes list has one entry per requested sample (sampleCount).
    Each entry is raw MP4 bytes decoded from bytesBase64Encoded.

    Response shape when done=true:
        {
          "name": "...",
          "done": true,
          "response": {
            "@type": "type.googleapis.com/cloud.ai.large_models.vision.GenerateVideoResponse",
            "raiMediaFilteredCount": 0,
            "videos": [
              {"bytesBase64Encoded": "...", "mimeType": "video/mp4"},
              ...
            ]
          }
        }

    Or, on failure:
        {"name": "...", "done": true, "error": {"code": ..., "message": ...}}
    """
    if not isinstance(response_dict, dict):
        raise VertexBackendError(
            f"Unexpected poll response type: {type(response_dict).__name__}"
        )

    if not response_dict.get("done"):
        return ("running", None)

    error = response_dict.get("error")
    if error:
        if is_service_agent_provisioning_error(error):
            return ("service_agent_provisioning", error)
        return ("error", error)

    payload = response_dict.get("response", {})
    rai_filtered = payload.get("raiMediaFilteredCount", 0)
    videos = payload.get("videos", [])

    if rai_filtered and not videos:
        return (
            "error",
            {
                "code": "RAI_FILTERED",
                "message": (
                    f"All {rai_filtered} generated videos were filtered by "
                    f"Responsible AI safety checks. Rephrase the prompt "
                    f"using safer language and retry."
                ),
            },
        )

    if not videos:
        return (
            "error",
            {
                "code": "NO_VIDEOS",
                "message": (
                    f"Poll response has done=true but no videos. "
                    f"Payload keys: {list(payload.keys())}"
                ),
            },
        )

    decoded = []
    for i, v in enumerate(videos):
        b64 = v.get("bytesBase64Encoded")
        if not b64:
            raise VertexBackendError(
                f"Video {i} has no bytesBase64Encoded. Keys: {list(v.keys())}"
            )
        decoded.append(base64.b64decode(b64))
    return ("done", decoded)


# ─── HTTP helper ────────────────────────────────────────────────────

def vertex_post(url, body, *, timeout=60):
    """POST a JSON body to a Vertex AI endpoint and return the parsed JSON.

    Raises VertexBackendError on non-2xx or non-JSON responses with the
    full error body included for debugging. Callers in video_generate.py
    catch this and translate to user-facing _error_exit messages.
    """
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        # Try to extract a structured error for cleaner messages.
        try:
            err = json.loads(body_text).get("error", {})
            msg = err.get("message", body_text[:500])
            raise VertexBackendError(f"Vertex HTTP {e.code}: {msg}") from None
        except (json.JSONDecodeError, ValueError):
            raise VertexBackendError(
                f"Vertex HTTP {e.code}: {body_text[:500]}"
            ) from None
    except urllib.error.URLError as e:
        raise VertexBackendError(f"Vertex network error: {e.reason}") from None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise VertexBackendError(
            f"Vertex returned non-JSON response: {raw[:300]!r}"
        ) from None


# ─── Diagnose CLI ───────────────────────────────────────────────────

def _cmd_diagnose(args):
    """Diagnose the Vertex AI setup without burning VEO budget.

    Pings a free Gemini text-gen endpoint through the same auth path to
    verify credentials are live. Reports project, location, key prefix,
    and the resolved URL pattern. Exit 0 on success, 1 on any failure.
    """
    print("=== Vertex AI backend diagnose ===")

    try:
        creds = load_vertex_credentials(
            cli_api_key=args.vertex_api_key,
            cli_project=args.vertex_project,
            cli_location=args.vertex_location,
        )
    except VertexAuthError as e:
        print(f"FAIL (auth): {e}")
        sys.exit(1)

    key_preview = creds["api_key"][:6] + "..." + creds["api_key"][-4:]
    print(f"  api_key:    {key_preview} ({len(creds['api_key'])} chars)")
    print(f"  project_id: {creds['project_id']}")
    print(f"  location:   {creds['location']}")

    # Build a sample URL for a Veo model (not actually called).
    sample_url = build_vertex_url(
        model="veo-3.1-lite-generate-001",
        method=METHOD_SUBMIT,
        project=creds["project_id"],
        location=creds["location"],
        api_key=creds["api_key"],
    )
    # Redact the key from the displayed URL.
    print("  sample URL (key redacted):")
    print("    " + sample_url.replace(creds["api_key"], "<REDACTED>"))

    # Free sanity check: Gemini text-gen via the same auth.
    # This is NOT a VEO call; it confirms the API key + project combo is
    # live without spending VEO budget. Cost: essentially $0 at low volume.
    sanity_url = (
        f"https://{creds['location']}-aiplatform.googleapis.com/v1"
        f"/projects/{creds['project_id']}/locations/{creds['location']}"
        f"/publishers/google/models/gemini-2.5-flash:generateContent"
        f"?key={creds['api_key']}"
    )
    # The regional host doesn't always serve Gemini generateContent; fall
    # back to the global host if the regional one 404s.
    global_sanity_url = (
        f"https://aiplatform.googleapis.com/v1"
        f"/publishers/google/models/gemini-2.5-flash-lite:generateContent"
        f"?key={creds['api_key']}"
    )

    sanity_body = {
        "contents": [
            {"role": "user", "parts": [{"text": "reply with the single word OK"}]}
        ]
    }

    print("\n  sanity check 1: regional Gemini text-gen...")
    try:
        result = vertex_post(sanity_url, sanity_body, timeout=30)
        text = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        print(f"  OK (regional): response text = {text.strip()!r}")
    except VertexBackendError as e:
        print(f"  regional failed: {e}")
        print("  falling back to global endpoint...")
        try:
            result = vertex_post(global_sanity_url, sanity_body, timeout=30)
            text = (
                result.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            print(f"  OK (global): response text = {text.strip()!r}")
        except VertexBackendError as e2:
            print(f"FAIL (sanity check): {e2}")
            sys.exit(1)

    print("\nAll checks passed. Vertex backend is reachable.")
    sys.exit(0)


def _cmd_smoke_test(args):
    """Validate Vertex API constraints discovered in v3.8.0 spike 5 Phase 2.

    **BUDGET-SAFE BY DESIGN (v3.8.1 lesson)**: an earlier draft of this
    subcommand submitted minimal valid requests to test model reachability,
    which accidentally charged ~$3.60 in VEO submissions before we realized
    that Vertex accepts the submit and validates asynchronously during
    generation. This version ONLY sends probes we have empirically verified
    fail at submit-time validation (free), plus a free auth ping. The
    remaining spike-5 constraints are documented rather than tested.

    Probes (all confirmed free during v3.8.1 debugging):
      1. Preview ID → 404 (preview suffix rejects at URL resolution, pre-validation)
      2. Invalid aspect ratio ("1:1") → HTTP 400 at submit validation
      3. Auth ping (Gemini text-gen on the same credentials)

    Documented-only constraints (require budget to empirically test):
      - GA -001 ID reachability (any valid submit = real generation = charged)
      - VEO duration {4,6,8} constraint (Vertex accepts submit, validation
        is async during generation — cannot probe without charging)
      - Scene Ext v2 720p forcing (requires real Scene Ext v2 call)
      - Scene Ext v2 15 MB inline upload limit (requires real video upload)

    Exit codes:
      0 — all free probes PASS (constraints confirmed)
      1 — one or more probes FAIL (constraint may have changed; investigate)
      2 — WARN on one or more probes
    """
    print("=== Vertex AI smoke test (v3.8.1 — budget-safe probes only) ===")
    print()

    # Load credentials once; all probes share the same project/location/key.
    try:
        creds = load_vertex_credentials(
            cli_api_key=args.vertex_api_key,
            cli_project=args.vertex_project,
            cli_location=args.vertex_location,
        )
    except VertexAuthError as e:
        print(f"FAIL (auth): {e}")
        sys.exit(1)

    print(f"  project:  {creds['project_id']}")
    print(f"  location: {creds['location']}")
    print(f"  api_key:  {creds['api_key'][:6]}...{creds['api_key'][-4:]}")
    print()

    results = []  # list of (probe_name, status, detail)

    # ── Probe 1: Preview ID returns 404 ────────────────────────────
    # Spike 5 Phase 2 confirmed that preview IDs (`-preview` suffix) return
    # HTTP 404 on some Vertex projects. This probe is free because the 404
    # happens at URL resolution, before any parameter validation or billing.
    print("## Probe 1: Preview ID returns 404 (free — URL-level rejection)")
    print()
    _minimal_request = {
        "instances": [{"prompt": "smoke-test probe (will 404 at URL level)"}],
        "parameters": {
            "sampleCount": 1,
            "durationSeconds": 8,
            "aspectRatio": "16:9",
            "resolution": "720p",
        },
    }

    url = build_vertex_url(
        model="veo-3.1-generate-preview",
        method=METHOD_SUBMIT,
        project=creds["project_id"],
        location=creds["location"],
        api_key=creds["api_key"],
    )
    try:
        vertex_post(url, _minimal_request, timeout=30)
        results.append((
            "Probe 1 (preview→404)",
            "WARN",
            "Submit on veo-3.1-generate-preview UNEXPECTEDLY SUCCEEDED — "
            "the preview-ID constraint may have relaxed on this project, "
            "and budget MAY have been charged. Investigate immediately.",
        ))
        print("    WARN — preview submit unexpectedly succeeded (budget may be charged!)")
    except VertexBackendError as e:
        msg = str(e)
        if "404" in msg or "NOT_FOUND" in msg:
            results.append((
                "Probe 1 (preview→404)",
                "PASS",
                f"veo-3.1-generate-preview returned 404 (constraint confirmed): {msg[:100]}",
            ))
            print("    PASS — veo-3.1-generate-preview returned 404")
        else:
            results.append((
                "Probe 1 (preview→404)",
                "WARN",
                f"Rejected but not with 404: {msg[:150]}",
            ))
            print(f"    WARN — rejected for different reason: {msg[:120]}")
    print()

    # ── Probe 2: Invalid aspect ratio ──────────────────────────────
    # Spike 5 Phase 2 confirmed VEO only accepts {16:9, 9:16}. v3.8.1
    # debugging confirmed "1:1" is REJECTED AT SUBMIT VALIDATION on GA -001
    # models — no budget charged. This is one of the few constraints Vertex
    # validates synchronously at submit time.
    print("## Probe 2: Invalid aspect ratio rejection (free — submit-time validation)")
    print()
    _bad_aspect_request = {
        "instances": [{"prompt": "smoke-test aspect probe"}],
        "parameters": {
            "sampleCount": 1,
            "durationSeconds": 8,
            "aspectRatio": "1:1",  # invalid for VEO
            "resolution": "720p",
        },
    }
    url = build_vertex_url(
        model="veo-3.1-lite-generate-001",
        method=METHOD_SUBMIT,
        project=creds["project_id"],
        location=creds["location"],
        api_key=creds["api_key"],
    )
    try:
        vertex_post(url, _bad_aspect_request, timeout=30)
        results.append((
            "Probe 2 (aspect→400)",
            "FAIL",
            "Submit with aspectRatio='1:1' unexpectedly SUCCEEDED — "
            "aspect constraint may have relaxed AND budget was charged. "
            "Investigate immediately.",
        ))
        print("    FAIL — aspectRatio='1:1' was accepted (budget may be charged!)")
    except VertexBackendError as e:
        msg = str(e)
        if "aspect" in msg.lower() or "1:1" in msg:
            results.append((
                "Probe 2 (aspect→400)",
                "PASS",
                f"Rejected at submit validation (free): {msg[:150]}",
            ))
            print(f"    PASS — rejected: {msg[:120]}")
        else:
            results.append((
                "Probe 2 (aspect→400)",
                "WARN",
                f"Rejected but not with 'aspect' message: {msg[:150]}",
            ))
            print(f"    WARN — rejected for different reason: {msg[:120]}")
    print()

    # ── Probe 3: Auth ping ─────────────────────────────────────────
    # Gemini text-gen via the same auth. Confirmed free (subscription-tier
    # or lowest-cost Gemini call).
    print("## Probe 3: Auth ping (free — Gemini text-gen on same credentials)")
    print()
    global_sanity_url = (
        f"https://aiplatform.googleapis.com/v1"
        f"/publishers/google/models/gemini-2.5-flash-lite:generateContent"
        f"?key={creds['api_key']}"
    )
    sanity_body = {
        "contents": [
            {"role": "user", "parts": [{"text": "reply with OK"}]}
        ]
    }
    try:
        result = vertex_post(global_sanity_url, sanity_body, timeout=30)
        text = (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        results.append((
            "Probe 3 (auth)",
            "PASS",
            f"Auth ping succeeded: {text.strip()!r}",
        ))
        print(f"    PASS — auth ping returned: {text.strip()!r}")
    except VertexBackendError as e:
        results.append((
            "Probe 3 (auth)",
            "FAIL",
            f"Auth ping failed: {e}",
        ))
        print(f"    FAIL — auth ping failed: {e}")
    print()

    # ── Documented-only constraints (can't probe for free) ─────────
    print("## Untested constraints (require budget to empirically verify)")
    print()
    print("    * GA -001 model reachability (veo-3.1-generate-001, -fast-, -lite-)")
    print("        Any valid submit = real generation = billed. See spike 5 Phase 2")
    print("        findings for empirical validation across all 5 tiers.")
    print()
    print("    * VEO duration constraint {4, 6, 8}")
    print("        Vertex ACCEPTS submits with invalid durations and validates")
    print("        asynchronously during generation (discovered during v3.8.1")
    print("        debugging — this differs from spike 5 Phase 2 behavior).")
    print("        Cannot probe safely without charging for the generation.")
    print()
    print("    * Scene Ext v2 720p forcing — requires a real Scene Ext v2")
    print("        submit with a 1080p base clip. Constraint documented in")
    print("        references/veo-models.md → 'Phase 2 Vertex API constraints'.")
    print()
    print("    * Scene Ext v2 15 MB inline base64 upload limit — requires a")
    print("        real video upload. Documented in the same reference section.")
    print()

    # ── Summary ─────────────────────────────────────────────────────
    print("## Summary")
    print()
    counts = {"PASS": 0, "FAIL": 0, "WARN": 0, "INFO": 0}
    for name, status, detail in results:
        counts[status] = counts.get(status, 0) + 1
        icon = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]", "INFO": "[INFO]"}.get(status, status)
        print(f"    {icon} {name}: {detail[:200]}")
    print()
    print(f"    Totals: {counts.get('PASS', 0)} PASS, "
          f"{counts.get('FAIL', 0)} FAIL, "
          f"{counts.get('WARN', 0)} WARN, "
          f"{counts.get('INFO', 0)} INFO")

    if counts.get("FAIL", 0) > 0:
        print("\n[FAIL] One or more probes FAILED. Investigate before using VEO.")
        sys.exit(1)
    if counts.get("WARN", 0) > 0:
        print("\n[WARN] One or more probes surfaced WARNings. Behaviour differs from spike 5 Phase 2; worth reviewing.")
        sys.exit(2)
    print("\n[OK] All probes PASS. Vertex constraints from spike 5 Phase 2 still in effect.")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Vertex AI backend helper for VEO video generation",
    )
    sub = parser.add_subparsers(dest="command")

    p_diag = sub.add_parser(
        "diagnose", help="Verify Vertex auth without burning VEO budget"
    )
    p_diag.add_argument("--vertex-api-key", default=None)
    p_diag.add_argument("--vertex-project", default=None)
    p_diag.add_argument("--vertex-location", default=None)

    p_smoke = sub.add_parser(
        "smoke-test",
        help="Validate 4 of the 5 Vertex API constraints from spike 5 Phase 2 (v3.8.1+)",
    )
    p_smoke.add_argument("--vertex-api-key", default=None)
    p_smoke.add_argument("--vertex-project", default=None)
    p_smoke.add_argument("--vertex-location", default=None)

    args = parser.parse_args()
    if args.command is None:
        # Default: diagnose
        args = parser.parse_args(["diagnose"])

    if args.command == "diagnose":
        _cmd_diagnose(args)
    elif args.command == "smoke-test":
        _cmd_smoke_test(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
