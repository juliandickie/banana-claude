#!/usr/bin/env python3
"""Nano Banana Studio -- Audio-driven lip-sync via VEED Fabric 1.0 (v3.8.1+)

Generates a talking-head video by pairing a face image with an audio file.
Fabric 1.0 is a specialised model on Replicate — it doesn't generate speech
or motion from a prompt, it takes an existing image + an existing audio file
and lip-syncs the face to the audio. This closes the v3.8.0 gap where VEO
generates speech internally and can't accept external custom voices, and
Kling doesn't accept audio input at all.

Typical workflow (two-step, decoupled from audio_pipeline.py):

    # Step 1 — generate the narration with your custom voice
    python3 audio_pipeline.py narrate \\
        --text "Welcome to our product demo..." \\
        --voice brand_voice \\
        --out /tmp/narration.mp3

    # Step 2 — lip-sync a face image to the narration
    python3 video_lipsync.py \\
        --image face.png \\
        --audio /tmp/narration.mp3 \\
        --resolution 720p \\
        --output ~/Documents/nanobanana_generated

Uses only Python stdlib via _replicate_backend.py helpers. Zero pip deps.

See:
- skills/video/references/lipsync.md (reference doc)
- dev-docs/veed-fabric-1.0-llms.md (authoritative model card)
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Reuse the v3.8.0 Replicate backend for HTTP + auth + parsing. We don't
# duplicate the poll loop — just import the low-level helpers and orchestrate.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _replicate_backend as replicate  # noqa: E402


# ─── Constants ──────────────────────────────────────────────────────

FABRIC_MODEL_SLUG = "veed/fabric-1.0"
DEFAULT_RESOLUTION = "720p"
DEFAULT_POLL_INTERVAL = 10
DEFAULT_MAX_WAIT = 600
OUTPUT_DIR = Path.home() / "Documents" / "nanobanana_generated"


# ─── Progress + error helpers (mirror video_generate.py) ────────────

def _error_exit(message):
    """Print JSON error to stdout and exit 1."""
    print(json.dumps({"error": True, "message": message}))
    sys.exit(1)


def _progress(data):
    """Print progress JSON to stderr."""
    print(json.dumps(data), file=sys.stderr)


# ─── Fabric API flow ────────────────────────────────────────────────

def _submit_fabric(*, image_uri, audio_uri, resolution, token):
    """Submit a Fabric 1.0 prediction and return the poll URL.

    image_uri and audio_uri must already be data URIs or HTTPS URLs —
    the caller is responsible for converting local files via
    image_path_to_data_uri() / audio_path_to_data_uri().
    """
    body = replicate.build_fabric_request_body(
        image=image_uri,
        audio=audio_uri,
        resolution=resolution,
    )
    url = replicate.build_predictions_url(FABRIC_MODEL_SLUG)

    _progress({
        "status": "submitting",
        "backend": "replicate",
        "model": FABRIC_MODEL_SLUG,
        "resolution": resolution,
    })

    try:
        result = replicate.replicate_post(
            url, body, token=token, timeout=120
        )
        prediction_id, poll_url = replicate.parse_replicate_submit_response(result)
    except replicate.ReplicateBackendError as e:
        _error_exit(f"Fabric submit failed: {e}")

    _progress({
        "status": "submitted",
        "backend": "replicate",
        "prediction_id": prediction_id,
    })
    return poll_url


def _poll_fabric(poll_url, token, interval, max_wait):
    """Poll the Fabric prediction URL until terminal state.

    Returns the output URL string on success. Exits with error on
    failed / canceled / aborted / timeout.
    """
    start = time.time()

    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            _error_exit(
                f"Timeout: Fabric prediction not done after {max_wait}s. "
                f"Poll URL: {poll_url}"
            )

        try:
            result = replicate.replicate_get(
                poll_url, token=token, timeout=30
            )
            status, payload = replicate.parse_replicate_poll_response(result)
        except replicate.ReplicateBackendError as e:
            _error_exit(f"Fabric poll failed: {e}")

        if status == "running":
            _progress({
                "polling": True,
                "backend": "replicate",
                "elapsed": int(elapsed),
                "status": "processing",
            })
            time.sleep(interval)
            continue

        if status == "done":
            # Fabric output is a single URI string per the model card.
            # Defensively handle list shape for forward-compat.
            if isinstance(payload, list):
                payload = payload[0] if payload else None
            if not payload:
                _error_exit("Fabric prediction succeeded but output is empty.")
            return payload

        # status == "failed" (covers failed | canceled | aborted)
        err_str = str(payload) if payload else "unknown error"
        if "safety" in err_str.lower() or "nsfw" in err_str.lower():
            _error_exit(f"VIDEO_SAFETY: {err_str}")
        _error_exit(f"Fabric prediction failed: {err_str}")


def _download_output(output_url, output_dir):
    """Download the Fabric output MP4 and save it locally."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"lipsync_{timestamp}.mp4"
    output_path = (out / filename).resolve()

    _progress({
        "status": "downloading",
        "backend": "replicate",
        "url": output_url,
    })

    try:
        req = urllib.request.Request(
            output_url,
            headers={"User-Agent": replicate.REPLICATE_USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        _error_exit(f"Failed to download Fabric output: {e}")

    return str(output_path)


# ─── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate a talking-head video via VEED Fabric 1.0",
    )
    parser.add_argument(
        "--image", required=True,
        help="Face image file path (jpg/jpeg/png). The subject whose face "
             "will be lip-synced to the audio.",
    )
    parser.add_argument(
        "--audio", required=True,
        help="Audio file path (mp3/wav/m4a/aac). Any voice audio — typically "
             "an ElevenLabs TTS narration from audio_pipeline.py, a recorded "
             "voice-over, or any pre-existing audio track.",
    )
    parser.add_argument(
        "--resolution", default=DEFAULT_RESOLUTION,
        choices=["480p", "720p"],
        help=f"Output resolution. Fabric 1.0 supports 480p or 720p only. "
             f"(default: {DEFAULT_RESOLUTION})",
    )
    parser.add_argument(
        "--output", default=str(OUTPUT_DIR),
        help=f"Output directory for the lip-synced MP4. (default: {OUTPUT_DIR})",
    )
    parser.add_argument(
        "--replicate-key", default=None,
        help="Replicate API token. Loads from REPLICATE_API_TOKEN env var "
             "or ~/.banana/config.json replicate_api_token field if unset.",
    )
    parser.add_argument(
        "--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL,
        help=f"Seconds between polls (default: {DEFAULT_POLL_INTERVAL})",
    )
    parser.add_argument(
        "--max-wait", type=int, default=DEFAULT_MAX_WAIT,
        help=f"Max wait seconds (default: {DEFAULT_MAX_WAIT})",
    )

    args = parser.parse_args()

    # ── Validation (pre-flight, catches bad input without burning an API call) ──
    try:
        replicate.validate_fabric_params(
            image=Path(args.image),
            audio=Path(args.audio),
            resolution=args.resolution,
        )
    except replicate.ReplicateValidationError as e:
        _error_exit(str(e))

    # ── Credentials ──
    try:
        creds = replicate.load_replicate_credentials(cli_token=args.replicate_key)
    except replicate.ReplicateAuthError as e:
        _error_exit(str(e))

    _progress({
        "status": "backend_selected",
        "backend": "replicate",
        "model": FABRIC_MODEL_SLUG,
    })

    # ── Encode inputs as data URIs ──
    try:
        image_uri = replicate.image_path_to_data_uri(Path(args.image))
        audio_uri = replicate.audio_path_to_data_uri(Path(args.audio))
    except replicate.ReplicateValidationError as e:
        _error_exit(str(e))

    # ── Submit + poll + download ──
    gen_start = time.time()

    poll_url = _submit_fabric(
        image_uri=image_uri,
        audio_uri=audio_uri,
        resolution=args.resolution,
        token=creds["api_token"],
    )

    output_url = _poll_fabric(
        poll_url=poll_url,
        token=creds["api_token"],
        interval=args.poll_interval,
        max_wait=args.max_wait,
    )

    output_path = _download_output(output_url, args.output)
    gen_time = round(time.time() - gen_start, 1)

    result = {
        "path": output_path,
        "model": FABRIC_MODEL_SLUG,
        "resolution": args.resolution,
        "source_image": args.image,
        "source_audio": args.audio,
        "generation_time_seconds": gen_time,
        "backend": "replicate",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
