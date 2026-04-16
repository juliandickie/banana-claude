#!/usr/bin/env python3
"""nano-banana-studio -- multi-provider audio replacement pipeline (v3.7.4)

Generates continuous TTS narration (ElevenLabs) + background music (Lyria 2 default,
ElevenLabs Music alternative), mixes them with FFmpeg side-chain ducking, and
audio-swaps the result into a target video. This is the v3.7.1+v3.7.2 architecture
validated empirically in spikes 3 and 4 of the strategic reset session — see
ROADMAP.md and references/audio-pipeline.md for context.

History:
- v3.7.1 (2026-04-14): initial implementation as elevenlabs_audio.py with ElevenLabs Music
- v3.7.2 (2026-04-14): renamed to audio_pipeline.py, Lyria 2 added as default music source
                       after winning the 5-way bake-off in spike 4 (Lyria > ElevenLabs >
                       MusicGen > MiniMax > Stable Audio per user listening verdict)
- v3.7.4 (2026-04-15): audio polish bundle — real stereo mix (pan=stereo|c0=c0|c1=c0 +
                       explicit -ac 2), pre-flight named-creator stripping shared by
                       Lyria and ElevenLabs Music, multi-call Lyria with FFmpeg acrossfade
                       for music longer than 32.768s, ElevenLabs Instant Voice Cloning
                       (voice-clone subcommand), and auto-measured per-voice WPM
                       persisted to custom_voices.{role}.wpm on voice-promote /
                       voice-clone / retroactive voice-measure.

The script's purpose is to solve the multi-clip music-bed seam problem in stitched
VEO sequences: when 4 separately-generated VEO clips are concatenated, each clip's
emergent music intro/outro creates audible seams every clip-duration. By generating
ONE continuous TTS track and ONE continuous music track and replacing the entire
audio bed, the seams disappear by construction.

Architecture:
    1. ElevenLabs TTS: POST /v1/text-to-speech/{voice_id} (eleven_v3 model, audio tags)
    2. Eleven Music: POST /v1/music (music_v1 model, instrumental, length-locked)
    3. FFmpeg mix:    sidechaincompress with apad for full-length ducked output
    4. FFmpeg swap:   -map 0:v -map 1:a -c:v copy lossless audio replacement
    5. Voice Design:  POST /v1/text-to-voice/design + POST /v1/text-to-voice for custom voices

Usage:
    audio_pipeline.py status                            Check API keys, ffmpeg, music sources, voice library
    audio_pipeline.py narrate --text "..." [--voice ROLE] [--out PATH]
    audio_pipeline.py music --prompt "..." [--source lyria|elevenlabs] [--length-ms N] [--out PATH]
    audio_pipeline.py mix --narration N.mp3 --music M.mp3 --out OUT.mp3
    audio_pipeline.py swap --video V.mp4 --audio A.mp3 --out OUT.mp4
    audio_pipeline.py pipeline --video V.mp4 --text "..." --music-prompt "..." --out OUT.mp4
    audio_pipeline.py voice-design --description "..." [--name NAME] [--enhance]
    audio_pipeline.py voice-promote --generated-id ID --name NAME --role ROLE [--description "..."]
    audio_pipeline.py voice-clone --audio FILE_OR_DIR --name NAME --role ROLE [--label-accent ...]
    audio_pipeline.py voice-measure --role ROLE          (measure WPM for an existing voice)
    audio_pipeline.py voice-list

The pipeline subcommand is the canonical end-to-end command — it takes a silent or
audio-bearing video, a narration script, and a music prompt, then runs all five
stages and writes a final MP4 with the new audio swapped in. The TTS and music API
calls run in parallel (concurrent.futures.ThreadPoolExecutor) to roughly halve the
user-perceived latency from ~19s sequential to ~12s parallel.

Configuration is read from ~/.banana/config.json:
    elevenlabs_api_key:        ElevenLabs API key (xi-api-key header)
    custom_voices:             Nested dict of role -> voice metadata (see schema below)

Custom voice schema (v3.7.1+):
    custom_voices: {
      "narrator": {
        "voice_id":      ElevenLabs permanent voice ID (string)
        "name":          Display name (string)
        "description":   Original design description (string)
        "source_type":   "designed" | "cloned" | "library"
        "design_method": For source_type=designed: "text_to_voice" | "remix"
        "model_id":      Model used to create the voice (eleven_ttv_v3, etc.)
        "guidance_scale":  Voice Design guidance value (0-30, default 5)
        "should_enhance":  Voice Design enhance flag (bool)
        "created_at":    ISO date
        "provider":      "elevenlabs" (forward-compatible for multi-provider future)
        "notes":         Free-form context (pacing observations, A/B history, etc.)
      },
      "character_a": { ... },
      ...
    }

Stdlib only — uses urllib.request for HTTP, concurrent.futures for parallelism,
subprocess for FFmpeg invocation. Zero pip dependencies, matching the plugin's
existing fallback-script pattern.
"""

import argparse
import base64
import concurrent.futures
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONFIG_PATH = Path.home() / ".banana" / "config.json"
DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "nano-banana-audio"

ELEVENLABS_API = "https://api.elevenlabs.io"

# TTS defaults — eleven_v3 with Natural stability mode (honors audio tags)
DEFAULT_TTS_MODEL = "eleven_v3"
DEFAULT_VOICE_SETTINGS = {
    "stability": 0.5,           # Natural mode (between Creative and Robust)
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
}

# Music defaults
# v3.7.2: Lyria 2 is the default music source after the 5-way bake-off in spike 4
# (Lyria > ElevenLabs > MusicGen > MiniMax > Stable Audio per user listening verdict).
# ElevenLabs Music is retained as the alternative for users who prefer its character
# or want subscription-billed cost (Lyria is fixed $0.06 per call regardless of subscription).
DEFAULT_MUSIC_SOURCE = "elevenlabs"  # "elevenlabs" | "lyria" — v3.8.3: flipped after 12-genre blind bake-off (ElevenLabs 12-0 sweep)
DEFAULT_MUSIC_LENGTH_MS = 32000  # Lyria fixed at 32.768s; ElevenLabs configurable up to 600000

# Lyria 2 defaults — google vertex AI lyria-002
LYRIA_MODEL_ID = "lyria-002"
# Lyria has a fixed clip duration of 32.768 seconds. The music_length_ms parameter
# is ignored when source=lyria. Users who need different lengths must use elevenlabs.
LYRIA_FIXED_DURATION_SEC = 32.768

# ElevenLabs Music defaults — music_v1
DEFAULT_ELEVEN_MUSIC_MODEL = "music_v1"

# Voice Design defaults — eleven_ttv_v3 (v3-native)
DEFAULT_TTV_MODEL = "eleven_ttv_v3"
DEFAULT_GUIDANCE_SCALE = 5

# FFmpeg sidechain compression parameters — empirically tuned in spike 3.
#
# v3.7.4: the narration branch now uses `pan=stereo|c0=c0|c1=c0` to explicitly
# duplicate the mono ElevenLabs TTS source onto both left and right channels
# BEFORE apad and sidechaincompress. v3.7.1's `aformat=channel_layouts=stereo`
# alone declared the stream metadata as stereo but did not actually upmix the
# signal — the result was stereo-in-container with a silent right channel,
# audible as "speaker-left-only" narration on headphones. The pan filter is
# the canonical ffmpeg way to force a real mono-to-stereo duplication.
# The mix output is also explicitly encoded as 2-channel stereo (`-ac 2` in
# mix_narration_with_music below) to lock the container channel count.
SIDECHAIN_FILTER = (
    "[0:a]aformat=channel_layouts=mono,pan=stereo|c0=c0|c1=c0,"
    "apad=whole_dur={duration}[narration_padded];"
    "[1:a]volume=0.55[music_quiet];"
    "[music_quiet][narration_padded]sidechaincompress="
    "threshold=0.04:ratio=10:attack=15:release=350[ducked];"
    "[narration_padded][ducked]amix=inputs=2:duration=longest:weights='1.6 1.0'[mixed]"
)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    """Read ~/.banana/config.json. Returns {} if missing."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        _error_exit(f"failed to read {CONFIG_PATH}: {e}")
        return {}  # unreachable, satisfies linter


def _atomic_write_config(config: dict) -> None:
    """Write config.json atomically: tempfile in same dir → fsync → rename."""
    config_dir = CONFIG_PATH.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(config_dir), prefix=".config.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, 0o600)
        os.rename(tmp_path, CONFIG_PATH)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _get_api_key(cli_key: str | None = None) -> str:
    """Resolve API key: CLI flag → env var → config file."""
    if cli_key:
        return cli_key
    env_key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("XI_API_KEY")
    if env_key:
        return env_key
    config = _load_config()
    cfg_key = config.get("elevenlabs_api_key")
    if cfg_key:
        return cfg_key
    _error_exit(
        "no ElevenLabs API key found. Set ELEVENLABS_API_KEY env var, "
        "pass --api-key, or add 'elevenlabs_api_key' to ~/.banana/config.json"
    )
    return ""  # unreachable


def _resolve_voice(role_or_id: str | None, config: dict | None = None) -> tuple[str, dict | None]:
    """Resolve a voice reference to (voice_id, metadata).

    Accepts:
      - A semantic role name (e.g. "narrator") → looked up in custom_voices
      - A literal ElevenLabs voice_id (any 20-char alphanumeric)
      - None → defaults to "narrator" role if it exists, else error

    Returns (voice_id, metadata_dict_or_None).
    """
    config = config or _load_config()
    custom = config.get("custom_voices", {}) or {}

    if role_or_id is None:
        # Default to narrator role if it exists
        if "narrator" in custom:
            meta = custom["narrator"]
            return meta["voice_id"], meta
        _error_exit(
            "no voice specified and no 'narrator' role in custom_voices. "
            "Pass --voice ROLE or --voice VOICE_ID, or design one with voice-design subcommand."
        )
        return "", None  # unreachable

    # Check if it's a known role first
    if role_or_id in custom:
        meta = custom[role_or_id]
        return meta["voice_id"], meta

    # Otherwise treat it as a literal voice_id
    return role_or_id, None


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _http_post_json(url: str, body: dict, api_key: str, accept: str = "application/json", timeout: int = 180) -> bytes:
    """POST JSON body, return raw response bytes. Raises on HTTP error."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": accept,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _http_get_json(url: str, api_key: str, timeout: int = 30) -> dict:
    """GET JSON, return parsed dict. Raises on HTTP error."""
    req = urllib.request.Request(
        url,
        headers={"xi-api-key": api_key, "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _http_error_message(e: urllib.error.HTTPError) -> str:
    """Extract a useful error message from an HTTPError, including ElevenLabs's
    structured `detail.message` when present and `detail.data.prompt_suggestion`
    when the music API returns a TOS guardrail rejection."""
    body_text = ""
    try:
        body_text = e.read().decode()
    except Exception:
        pass
    msg = f"HTTP {e.code}"
    try:
        body_json = json.loads(body_text)
        detail = body_json.get("detail", {})
        if isinstance(detail, dict):
            if "message" in detail:
                msg += f": {detail['message']}"
            suggestion = detail.get("data", {}).get("prompt_suggestion")
            if suggestion:
                msg += f" (API suggestion: {suggestion[:200]})"
        elif isinstance(detail, str):
            msg += f": {detail}"
    except (json.JSONDecodeError, AttributeError):
        if body_text:
            msg += f": {body_text[:300]}"
    return msg


def _error_exit(message: str, exit_code: int = 1) -> None:
    """Print a structured error JSON to stdout and exit. Plugin convention."""
    print(json.dumps({"error": True, "message": message}))
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# Stage 1: TTS narration
# ---------------------------------------------------------------------------


def generate_narration(text: str, voice_id: str, api_key: str, model_id: str = DEFAULT_TTS_MODEL,
                       voice_settings: dict | None = None, output_path: Path | None = None) -> dict:
    """Call ElevenLabs TTS for a continuous narration. Returns a result dict.

    Default model is eleven_v3 with Natural stability — honors audio tags,
    selective capitalization, and ellipses for pacing control.
    """
    settings = voice_settings or DEFAULT_VOICE_SETTINGS
    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"narration_{ts}.mp3"

    body = {
        "text": text,
        "model_id": model_id,
        "voice_settings": settings,
    }
    url = f"{ELEVENLABS_API}/v1/text-to-speech/{voice_id}"

    t0 = time.time()
    try:
        audio_bytes = _http_post_json(url, body, api_key, accept="audio/mpeg", timeout=180)
    except urllib.error.HTTPError as e:
        _error_exit(f"TTS failed: {_http_error_message(e)}")
    except Exception as e:
        _error_exit(f"TTS failed: {type(e).__name__}: {e}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    return {
        "path": str(output_path),
        "bytes": len(audio_bytes),
        "voice_id": voice_id,
        "model_id": model_id,
        "char_count": len(text),
        "elapsed_seconds": round(time.time() - t0, 2),
    }


# ---------------------------------------------------------------------------
# Stage 2: Music generation (multi-provider)
#
# v3.7.2 supports two music providers, validated empirically in spike 4 of the
# strategic reset session:
#
#   - Lyria 2 (Google Vertex AI, source="lyria") — DEFAULT
#       * Highest fidelity in the spike 4 5-way bake-off (48kHz/192kbps stereo)
#       * Fixed $0.06 per call, fixed 32.768s clip duration
#       * Supports negative_prompt for explicit exclusions
#       * Reuses existing Vertex API-key auth from ~/.banana/config.json
#
#   - ElevenLabs Music (source="elevenlabs") — ALTERNATIVE
#       * Close second in the bake-off (44.1kHz/128kbps stereo)
#       * Subscription-billed (effectively free on Creator tier within quota)
#       * Configurable duration 3000-600000ms
#       * No negative prompt support
#       * Music API blocks named-creator/brand prompts (HTTP 400 with prompt_suggestion)
#
# Spike 4 also tested Stable Audio 2.5, MiniMax Music 1.5, and Meta MusicGen.
# All three lost the listening test to Lyria + ElevenLabs and are NOT integrated
# in v3.7.2. See references/audio-pipeline.md "5-way music model bake-off" for
# the full comparison and the F13 finding (specs vs subjective quality).
# ---------------------------------------------------------------------------


def generate_music(prompt: str, api_key: str | None = None, source: str = DEFAULT_MUSIC_SOURCE,
                   length_ms: int = DEFAULT_MUSIC_LENGTH_MS,
                   negative_prompt: str | None = None,
                   force_instrumental: bool = True,
                   output_path: Path | None = None,
                   keep_wav: bool = True,
                   mp3_bitrate: str = "256k",
                   allow_creators: bool = False) -> dict:
    """Generate background music via the configured provider.

    Dispatches to source-specific implementations:
      - source="lyria":      Google Vertex AI Lyria 2 (default)
      - source="elevenlabs": ElevenLabs Music v1

    Both produce stereo MP3 output of approximately the requested length. Lyria
    has a fixed 32.768s clip duration; the length_ms parameter is ignored when
    source=lyria. ElevenLabs respects length_ms in the 3000-600000ms range.

    keep_wav and mp3_bitrate apply to Lyria only — Lyria delivers a lossless
    WAV master that v3.7.2 preserves alongside the transcoded MP3 by default.
    ElevenLabs delivers MP3 directly with no lossless source available.

    The api_key parameter is provider-dependent: Lyria reads vertex_api_key from
    config and ignores api_key; ElevenLabs uses elevenlabs_api_key.
    """
    if source == "lyria":
        # v3.7.4: if the requested length exceeds Lyria's 32.768s hard cap, use
        # the multi-call + acrossfade path. Otherwise fall back to the single-
        # call primitive for efficiency (one API call vs. N + FFmpeg concat).
        requested_sec = (length_ms or 0) / 1000.0
        if requested_sec > LYRIA_FIXED_DURATION_SEC + 0.5:
            return generate_music_lyria_extended(
                prompt=prompt,
                target_duration_sec=requested_sec,
                negative_prompt=negative_prompt,
                output_path=output_path,
                keep_wav=keep_wav,
                mp3_bitrate=mp3_bitrate,
                allow_creators=allow_creators,
            )
        return generate_music_lyria(
            prompt=prompt,
            negative_prompt=negative_prompt,
            output_path=output_path,
            keep_wav=keep_wav,
            mp3_bitrate=mp3_bitrate,
            allow_creators=allow_creators,
        )
    elif source == "elevenlabs":
        return generate_music_elevenlabs(
            prompt=prompt,
            api_key=api_key or _get_elevenlabs_key(),
            length_ms=length_ms,
            force_instrumental=force_instrumental,
            output_path=output_path,
            allow_creators=allow_creators,
        )
    else:
        _error_exit(f"unknown music source: {source!r}. Valid: 'lyria', 'elevenlabs'")
        return {}  # unreachable


def generate_music_lyria(prompt: str, negative_prompt: str | None = None,
                         output_path: Path | None = None,
                         keep_wav: bool = True,
                         mp3_bitrate: str = "256k",
                         allow_creators: bool = False) -> dict:
    """Call Google Vertex AI Lyria 2 (lyria-002) for a 32.768s instrumental clip.

    Uses bound-to-service-account API-key auth via the existing vertex_api_key
    in ~/.banana/config.json. The same auth path the rest of the plugin uses
    for VEO video generation. No OAuth or service account JSON required.

    Lyria 2 has a fixed 32.768-second clip length — there is no duration
    parameter. The output is high-fidelity 48kHz stereo PCM WAV.

    v3.7.2 dual-output: this function preserves BOTH the lossless WAV source
    AND a 256 kbps MP3 transcoded copy. The WAV is the canonical master for
    downstream editing (layering, EQ, mastering); the MP3 is for preview,
    sharing, and the audio pipeline mix stage. Storage cost is ~6.3 MB per
    WAV vs ~1 MB per MP3 — both are kept by default since the MP3 alone
    discards the lossless source which can't be recovered.

    Pass keep_wav=False to skip the WAV file (output_path will be MP3 only).
    Pass mp3_bitrate="192k" or other libmp3lame bitrate to override the default
    256k MP3 quality (192k matches v3.7.1 ElevenLabs convention; 256k is the
    new v3.7.2 default for more transparent preview quality).

    Lyria supports negative_prompt for explicit exclusions ("vocals, dissonance,
    harsh percussion") — use this generously since Lyria honors it cleanly.

    Cost: $0.06 per call (10 RPM rate limit per Google docs).

    Empirically validated in spike 4 of the strategic reset session — Lyria 2
    won the 5-way bake-off against ElevenLabs, Stable Audio 2.5, MiniMax 1.5,
    and Meta MusicGen.
    """
    config = _load_config()
    api_key = config.get("vertex_api_key")
    project = config.get("vertex_project_id")
    location = config.get("vertex_location", "us-central1")

    if not (api_key and project and location):
        _error_exit(
            "Lyria requires vertex_api_key, vertex_project_id, and vertex_location "
            "in ~/.banana/config.json. These are the same credentials used for VEO. "
            "See video/references/veo-models.md → Backend Availability for setup."
        )

    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"music_lyria_{ts}.mp3"
    output_path = Path(output_path)

    # v3.7.4: pre-flight strip of known named-creator triggers. Both Lyria and
    # ElevenLabs Music reject these server-side, but Lyria's error message is
    # generic ("content policy") while ElevenLabs's is actionable. Strip here
    # so Lyria gets a clean prompt and so BOTH providers behave consistently.
    removed_terms: list[str] = []
    if not allow_creators:
        prompt, removed_terms = strip_named_creators(prompt)
        if negative_prompt:
            negative_prompt, _ = strip_named_creators(negative_prompt)

    # Construct Vertex AI Lyria endpoint URL
    endpoint = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/"
        f"locations/{location}/publishers/google/models/{LYRIA_MODEL_ID}:predict"
    )
    url_with_key = f"{endpoint}?key={api_key}"

    instance: dict = {"prompt": prompt}
    if negative_prompt:
        instance["negative_prompt"] = negative_prompt

    body = json.dumps({
        "instances": [instance],
        "parameters": {},
    }).encode()

    t0 = time.time()
    req = urllib.request.Request(
        url_with_key,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        _error_exit(f"Lyria gen failed: {_http_error_message(e)}")
    except Exception as e:
        _error_exit(f"Lyria gen failed: {type(e).__name__}: {e}")

    predictions = data.get("predictions", [])
    if not predictions:
        _error_exit(f"Lyria returned no predictions. Response keys: {list(data.keys())}")

    pred = predictions[0]
    audio_b64 = pred.get("audioContent") or pred.get("bytesBase64Encoded")
    if not audio_b64:
        _error_exit(f"Lyria prediction missing audioContent. Keys: {list(pred.keys())}")
    wav_bytes = base64.b64decode(audio_b64)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _check_ffmpeg()

    # v3.7.2 dual output: write the lossless WAV source first, then transcode
    # to MP3. Both files share the same basename so they're paired on disk.
    wav_path = output_path.with_suffix(".wav") if keep_wav else None
    if keep_wav:
        with open(wav_path, "wb") as f:
            f.write(wav_bytes)

    # Transcode WAV → MP3. Read from the WAV file on disk (if kept) for
    # cleaner ffmpeg behavior on unusual WAV headers; fall back to stdin pipe
    # if WAV wasn't saved.
    if keep_wav:
        ffmpeg_input = ["-i", str(wav_path)]
        ffmpeg_stdin = None
    else:
        ffmpeg_input = ["-f", "wav", "-i", "pipe:0"]
        ffmpeg_stdin = wav_bytes

    proc = subprocess.run(
        ["ffmpeg", "-y", *ffmpeg_input,
         "-c:a", "libmp3lame", "-b:a", mp3_bitrate, str(output_path)],
        input=ffmpeg_stdin,
        capture_output=True,
    )
    if proc.returncode != 0:
        # Fall back to writing only the WAV if transcoding fails
        if not keep_wav:
            wav_path = output_path.with_suffix(".wav")
            with open(wav_path, "wb") as f:
                f.write(wav_bytes)
        # Return WAV path as the primary output
        output_path = wav_path

    return {
        "mp3_path": str(output_path) if output_path.suffix == ".mp3" else None,
        "wav_path": str(wav_path) if wav_path else None,
        "path": str(output_path),  # back-compat: primary output for downstream callers
        "mp3_bytes": output_path.stat().st_size if output_path.suffix == ".mp3" else None,
        "wav_bytes": len(wav_bytes),
        "mp3_bitrate": mp3_bitrate if output_path.suffix == ".mp3" else None,
        "source": "lyria",
        "model_id": LYRIA_MODEL_ID,
        "duration_seconds": LYRIA_FIXED_DURATION_SEC,
        "elapsed_seconds": round(time.time() - t0, 2),
        "stripped_terms": removed_terms,  # v3.7.4: empty if no triggers matched
    }


def generate_music_lyria_extended(prompt: str, target_duration_sec: float,
                                  negative_prompt: str | None = None,
                                  output_path: Path | None = None,
                                  keep_wav: bool = True,
                                  mp3_bitrate: str = "256k",
                                  crossfade_sec: float = 2.0,
                                  allow_creators: bool = False) -> dict:
    """Generate a Lyria music track longer than the 32.768s hard cap.

    Strategy (v3.7.4):
      1. Compute N = ceil((target - crossfade) / (clip_len - crossfade))
         so that after N-1 crossfades the total duration >= target.
      2. Call Lyria N times with the same prompt (different seeds → varied clips).
      3. Chain them with FFmpeg `acrossfade` filters (equal-power curves by
         default — smooth transition without a noticeable dip).
      4. Trim the final concatenation to the exact target duration.

    Returns the same result shape as generate_music_lyria with the addition
    of `clip_count`, `clips` (list of intermediate paths), and `requested_duration_sec`.

    Cost: N × $0.06 per call. A 90s track = 3 calls = $0.18.

    Note on variety: each Lyria call produces a slightly different rendering
    from the same prompt. For short extensions (N=2-3) the clips usually
    cohere musically. For longer requests (N>5) you may hear tempo or key
    drift between segments — add more constraints to the prompt
    ("constant 90 BPM, C minor") to improve continuity.

    Note on cost predictability: if cost matters and the target is
    significantly longer than 60 seconds, consider falling back to
    --music-source elevenlabs, which is subscription-billed and handles
    any length up to 600000ms in a single call.
    """
    if target_duration_sec <= LYRIA_FIXED_DURATION_SEC + 0.5:
        # Caller shouldn't have routed us here, but be defensive.
        return generate_music_lyria(
            prompt=prompt,
            negative_prompt=negative_prompt,
            output_path=output_path,
            keep_wav=keep_wav,
            mp3_bitrate=mp3_bitrate,
            allow_creators=allow_creators,
        )

    # v3.7.4: strip creators once at the top so all N calls use the same cleaned prompt
    removed_terms: list[str] = []
    if not allow_creators:
        prompt, removed_terms = strip_named_creators(prompt)
        if negative_prompt:
            negative_prompt, _ = strip_named_creators(negative_prompt)

    clip_len = LYRIA_FIXED_DURATION_SEC
    import math
    effective_per_clip = clip_len - crossfade_sec
    clip_count = max(2, math.ceil((target_duration_sec - crossfade_sec) / effective_per_clip))

    _check_ffmpeg()

    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"music_lyria_extended_{ts}.mp3"
    output_path = Path(output_path)

    # Generate N clips to a staging directory. Use WAVs throughout for lossless
    # intermediate chaining, then transcode the final concat to MP3 at the end.
    staging = output_path.parent / f".lyria_ext_{os.getpid()}_{int(time.time())}"
    staging.mkdir(parents=True, exist_ok=True)
    clip_paths: list[Path] = []
    t0 = time.time()
    try:
        print(json.dumps({
            "status": "lyria_extended",
            "step": "generating_clips",
            "target_duration_sec": target_duration_sec,
            "clip_count": clip_count,
            "crossfade_sec": crossfade_sec,
        }), file=sys.stderr)

        for i in range(clip_count):
            clip_out = staging / f"clip_{i:02d}.mp3"
            # Pass allow_creators=True because we already stripped above — avoids
            # double-stripping (idempotent but wastes work).
            result = generate_music_lyria(
                prompt=prompt,
                negative_prompt=negative_prompt,
                output_path=clip_out,
                keep_wav=True,  # keep WAV so we can chain losslessly
                mp3_bitrate=mp3_bitrate,
                allow_creators=True,
            )
            wav_path = Path(result.get("wav_path") or clip_out.with_suffix(".wav"))
            clip_paths.append(wav_path)

        # Chain clips with acrossfade. FFmpeg's acrossfade only takes 2 inputs
        # per invocation, so we fold left-to-right: result = fade(result, next).
        # For N=2 we do one fade; for N=3 we do two; for N=K we do K-1.
        current = clip_paths[0]
        for i in range(1, clip_count):
            nxt = clip_paths[i]
            merged = staging / f"merge_{i:02d}.wav"
            cmd = [
                "ffmpeg", "-y",
                "-i", str(current),
                "-i", str(nxt),
                "-filter_complex",
                f"[0][1]acrossfade=d={crossfade_sec}:c1=tri:c2=tri[a]",
                "-map", "[a]",
                "-c:a", "pcm_s16le",
                "-ar", "48000",
                "-ac", "2",
                str(merged),
            ]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                _error_exit(f"Lyria acrossfade failed at clip {i}: {r.stderr[-500:]}")
            current = merged

        # Trim to the exact requested duration (acrossfade chain may exceed target
        # by up to clip_len-crossfade_sec due to the ceil rounding).
        final_wav = staging / "final.wav"
        trim_cmd = [
            "ffmpeg", "-y",
            "-i", str(current),
            "-t", f"{target_duration_sec:.3f}",
            "-c:a", "pcm_s16le",
            "-ar", "48000",
            "-ac", "2",
            str(final_wav),
        ]
        r = subprocess.run(trim_cmd, capture_output=True, text=True)
        if r.returncode != 0:
            _error_exit(f"Lyria final trim failed: {r.stderr[-500:]}")

        # Transcode to MP3 at the requested output path
        mp3_cmd = [
            "ffmpeg", "-y",
            "-i", str(final_wav),
            "-c:a", "libmp3lame",
            "-b:a", mp3_bitrate,
            "-ac", "2",
            str(output_path),
        ]
        r = subprocess.run(mp3_cmd, capture_output=True, text=True)
        if r.returncode != 0:
            _error_exit(f"Lyria final MP3 transcode failed: {r.stderr[-500:]}")

        # Save or discard the final WAV alongside the MP3
        if keep_wav:
            final_wav_persisted = output_path.with_suffix(".wav")
            # Copy by read-write (wav is small by intent — no need for os.rename across fs)
            with open(final_wav, "rb") as src, open(final_wav_persisted, "wb") as dst:
                dst.write(src.read())
        else:
            final_wav_persisted = None

        mp3_size = output_path.stat().st_size
        wav_size = final_wav_persisted.stat().st_size if final_wav_persisted else None

        return {
            "mp3_path": str(output_path),
            "wav_path": str(final_wav_persisted) if final_wav_persisted else None,
            "path": str(output_path),
            "mp3_bytes": mp3_size,
            "wav_bytes": wav_size,
            "mp3_bitrate": mp3_bitrate,
            "source": "lyria_extended",
            "model_id": LYRIA_MODEL_ID,
            "duration_seconds": target_duration_sec,
            "requested_duration_sec": target_duration_sec,
            "clip_count": clip_count,
            "crossfade_sec": crossfade_sec,
            "cost_usd_estimate": round(clip_count * 0.06, 2),
            "elapsed_seconds": round(time.time() - t0, 2),
            "stripped_terms": removed_terms,
        }
    finally:
        # Clean up the staging directory (keep the user's final output)
        try:
            for p in staging.iterdir():
                try:
                    p.unlink()
                except Exception:
                    pass
            staging.rmdir()
        except Exception:
            pass  # non-fatal


def generate_music_elevenlabs(prompt: str, api_key: str,
                              length_ms: int = DEFAULT_MUSIC_LENGTH_MS,
                              force_instrumental: bool = True,
                              model_id: str = DEFAULT_ELEVEN_MUSIC_MODEL,
                              output_path: Path | None = None,
                              allow_creators: bool = False) -> dict:
    """Call Eleven Music for an instrumental background bed.

    Important: prompts must NOT name copyrighted creators or brands (e.g.
    "Annie Leibovitz", "BBC Earth"). The API blocks these with HTTP 400 and
    a `prompt_suggestion` in the response. v3.7.4 strips known triggers
    client-side before sending — pass allow_creators=True to disable the
    strip if you want to test whether the upstream filter has changed for a
    specific term. Empirical finding from spike 3 v1 —
    see references/audio-pipeline.md.

    This is the v3.7.1 implementation. v3.7.2 retains it as the alternative
    music source after Lyria became the default; v3.7.4 adds shared
    pre-flight stripping with the Lyria path.
    """
    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"music_elevenlabs_{ts}.mp3"

    # v3.7.4: pre-flight strip of named-creator triggers (shared with Lyria path)
    removed_terms: list[str] = []
    if not allow_creators:
        prompt, removed_terms = strip_named_creators(prompt)

    body = {
        "prompt": prompt,
        "music_length_ms": length_ms,
        "model_id": model_id,
        "force_instrumental": force_instrumental,
    }
    url = f"{ELEVENLABS_API}/v1/music"

    t0 = time.time()
    try:
        audio_bytes = _http_post_json(url, body, api_key, accept="audio/mpeg", timeout=300)
    except urllib.error.HTTPError as e:
        _error_exit(f"ElevenLabs music gen failed: {_http_error_message(e)}")
    except Exception as e:
        _error_exit(f"ElevenLabs music gen failed: {type(e).__name__}: {e}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(audio_bytes)

    return {
        "path": str(output_path),
        "bytes": len(audio_bytes),
        "source": "elevenlabs",
        "model_id": model_id,
        "length_ms": length_ms,
        "force_instrumental": force_instrumental,
        "elapsed_seconds": round(time.time() - t0, 2),
        "stripped_terms": removed_terms,  # v3.7.4: empty if no triggers matched
    }


def _get_elevenlabs_key() -> str:
    """Helper to look up the ElevenLabs key without requiring it on Lyria-only calls."""
    config = _load_config()
    key = config.get("elevenlabs_api_key") or os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        _error_exit(
            "ElevenLabs API key not found. Required when using --music-source elevenlabs. "
            "Add elevenlabs_api_key to ~/.banana/config.json or set ELEVENLABS_API_KEY env var."
        )
    return key


# ---------------------------------------------------------------------------
# Pre-flight music prompt validation (v3.7.4)
#
# Both Lyria 2 and ElevenLabs Music reject prompts that name copyrighted
# creators, publications, or brands. The rejection path differs:
#   - ElevenLabs returns HTTP 400 with a structured `bad_prompt` error and a
#     `prompt_suggestion` in `detail.data.prompt_suggestion`. Actionable.
#   - Lyria returns HTTP 400 with a generic content-policy message. Less
#     actionable — the user has to guess which token triggered the filter.
#
# Rather than surface the upstream error every time, v3.7.4 strips known
# trigger terms client-side and emits a warning in the result dict. Users
# can pass --allow-creators to bypass the strip (useful if they want to
# test whether the upstream filter has been relaxed for a specific term).
#
# The list is intentionally small and maintainable — it covers the terms
# empirically known to trigger the filter from spikes 3 and 6, plus a
# short list of high-profile additions. It's NOT an attempt at an
# exhaustive TOS database. If a user hits an unlisted trigger they still
# get the upstream error, which now correctly surfaces the `prompt_suggestion`
# via _http_error_message().
# ---------------------------------------------------------------------------

# Case-insensitive substring match. Order matters for longer-phrase matches
# (more specific → less specific) so we strip "Annie Leibovitz" before "Annie"
# would catch a partial. The strip replaces the term with a space to avoid
# word concatenation issues.
NAMED_CREATOR_TRIGGERS = [
    # Photographers (spike 6 empirical: "Annie Leibovitz" forced magazine-cover rendering)
    "Annie Leibovitz",
    "Dorothea Lange",
    "Ansel Adams",
    "Richard Avedon",
    "Helmut Newton",
    "Steve McCurry",
    # Publications that render as literal magazine covers on Gemini 3.1 (spike 6)
    # and reject on Eleven Music as brand trademarks (spike 3).
    "Vanity Fair",
    "National Geographic",
    "Harper's Bazaar",
    "Vogue",
    "WIRED magazine",
    "Wallpaper*",
    "Architectural Digest",
    "Bon Appetit",
    "Kinfolk",
    "Rolling Stone",
    # Broadcasters + production brands that hit the Eleven Music content filter
    "BBC Earth",
    "BBC",
    "Pixar",
    "Disney",
    "Netflix",
    "HBO",
    # Film-score composers (trigger TOS filter on both music APIs)
    "Hans Zimmer",
    "John Williams",
    "Ennio Morricone",
    "Ludovico Einaudi",
    "Max Richter",
    "Philip Glass",
    # Pop artists (most common Eleven Music rejections per docs)
    "Taylor Swift",
    "Beyoncé",
    "Drake",
    "Kanye",
    "The Beatles",
]


def _load_custom_triggers() -> list[str] | None:
    """Load user-defined strip triggers from ~/.banana/config.json if present.

    Returns the list if the config has a `named_creator_triggers` key, else None
    (meaning: fall back to the hardcoded NAMED_CREATOR_TRIGGERS list).
    """
    try:
        cfg = _load_config()
        custom = cfg.get("named_creator_triggers")
        if isinstance(custom, list) and custom:
            return custom
    except Exception:
        pass
    return None


# Phrases that wrap creator names — when the creator is stripped, these
# become dangling fragments ("in the style of , warm strings"). We detect
# and clean them after the main strip pass.
_DANGLING_PHRASES = [
    "in the style of",
    "inspired by",
    "reminiscent of",
    "like",
    "à la",
    "a la",
    "channeling",
    "evoking",
]


def strip_named_creators(prompt: str, triggers: list[str] | None = None) -> tuple[str, list[str]]:
    """Remove known copyrighted-creator triggers from a music prompt.

    Returns (cleaned_prompt, list_of_removed_terms). Case-insensitive substring
    match. If no triggers fire, returns the original prompt and an empty list.
    Whitespace is normalised after stripping to avoid double-spaces.

    Trigger list precedence:
      1. Explicit `triggers` parameter (caller override)
      2. `named_creator_triggers` list in ~/.banana/config.json (user override)
      3. Hardcoded NAMED_CREATOR_TRIGGERS (default)

    After stripping creator names, any dangling wrapper phrases ("in the style
    of , warm strings") are cleaned up by detecting phrase + comma/end patterns.
    """
    if not prompt:
        return prompt, []
    if triggers is None:
        triggers = _load_custom_triggers() or NAMED_CREATOR_TRIGGERS
    cleaned = prompt
    removed: list[str] = []
    low = cleaned.lower()
    for term in triggers:
        tlow = term.lower()
        idx = low.find(tlow)
        while idx != -1:
            cleaned = cleaned[:idx] + " " + cleaned[idx + len(term):]
            low = cleaned.lower()
            removed.append(term)
            idx = low.find(tlow)
    # Collapse double+ spaces and trim
    cleaned = " ".join(cleaned.split()).strip()

    # Clean dangling wrapper phrases: "in the style of , warm strings" → "warm strings"
    # Pattern: phrase + optional whitespace + comma (the comma that followed the name)
    import re
    for phrase in _DANGLING_PHRASES:
        # "in the style of , rest" → "rest"
        # "in the style of rest" (no comma, name was at end) → "rest"
        pattern = re.compile(
            r'\b' + re.escape(phrase) + r'\s*,?\s*',
            re.IGNORECASE,
        )
        cleaned = pattern.sub(' ', cleaned)
    # Re-collapse whitespace after dangling-phrase removal
    cleaned = " ".join(cleaned.split()).strip()
    # Fix leading comma if the phrase was at the start
    cleaned = cleaned.lstrip(", ").strip()

    # De-duplicate removed list while preserving order
    seen: set[str] = set()
    dedup: list[str] = []
    for t in removed:
        if t not in seen:
            seen.add(t)
            dedup.append(t)
    return cleaned, dedup


# ---------------------------------------------------------------------------
# Stage 3: FFmpeg mix (narration + music + ducking)
# ---------------------------------------------------------------------------


def _check_ffmpeg() -> str:
    """Return ffmpeg path or exit with error."""
    path = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True).stdout.strip()
    if not path:
        _error_exit("ffmpeg not found in PATH. Install via brew install ffmpeg (macOS) or apt install ffmpeg (Linux).")
    return path


def _probe_duration(path: str | Path) -> float:
    """Return media duration in seconds via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def mix_narration_with_music(narration_path: Path, music_path: Path,
                             output_path: Path | None = None,
                             duration: float | None = None) -> dict:
    """Mix narration over music with side-chain ducking (lossy → mp3 192k).

    The narration is padded with silence to match the music length so the
    sidechain trigger lasts the full duration; this prevents the music tail
    from being truncated when narration is shorter than music.
    """
    _check_ffmpeg()

    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"mix_{ts}.mp3"

    # Determine target duration: explicit param, music length, or narration length
    if duration is None:
        music_dur = _probe_duration(music_path)
        narr_dur = _probe_duration(narration_path)
        duration = max(music_dur, narr_dur)
    duration = max(duration, 1.0)

    filter_graph = SIDECHAIN_FILTER.format(duration=duration)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(narration_path),
        "-i", str(music_path),
        "-filter_complex", filter_graph,
        "-map", "[mixed]",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        "-ac", "2",  # v3.7.4: force stereo output container (see SIDECHAIN_FILTER comment)
        str(output_path),
    ]

    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        _error_exit(f"ffmpeg mix failed: {result.stderr[-500:]}")

    return {
        "path": str(output_path),
        "bytes": output_path.stat().st_size,
        "duration_seconds": duration,
        "elapsed_seconds": round(time.time() - t0, 2),
    }


# ---------------------------------------------------------------------------
# Stage 4: FFmpeg audio-swap into video
# ---------------------------------------------------------------------------


def swap_audio_into_video(video_path: Path, audio_path: Path,
                          output_path: Path | None = None) -> dict:
    """Replace a video's audio track with the given audio file.

    Stream-copies the video (lossless, fast) and re-encodes audio to AAC for
    MP4 container compatibility. Uses -shortest to handle minor duration
    mismatches between video and audio (typically <100ms / 1 frame).
    """
    _check_ffmpeg()

    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"swapped_{ts}.mp4"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]

    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        _error_exit(f"ffmpeg audio-swap failed: {result.stderr[-500:]}")

    return {
        "path": str(output_path),
        "bytes": output_path.stat().st_size,
        "duration_seconds": _probe_duration(output_path),
        "elapsed_seconds": round(time.time() - t0, 2),
    }


# ---------------------------------------------------------------------------
# End-to-end pipeline (parallel TTS + music)
# ---------------------------------------------------------------------------


def pipeline(video_path: Path, narration_text: str, music_prompt: str,
             voice_id: str, api_key: str,
             output_path: Path | None = None,
             music_length_ms: int | None = None,
             music_source: str = DEFAULT_MUSIC_SOURCE,
             music_negative_prompt: str | None = None,
             tts_model: str = DEFAULT_TTS_MODEL,
             voice_settings: dict | None = None,
             allow_creators: bool = False) -> dict:
    """Full v3.7.1+ audio replacement: TTS + music in parallel, mix, swap.

    Returns a structured result with paths and timing for each stage. The TTS
    and music API calls run concurrently via ThreadPoolExecutor — they are
    independent so parallelization roughly halves the user-perceived latency.

    v3.7.2: music_source can be "lyria" (default, Google Vertex AI Lyria 2)
    or "elevenlabs" (ElevenLabs Music v1). The api_key parameter is always
    the ElevenLabs key (used for TTS narration); the Vertex API key for Lyria
    is read from ~/.banana/config.json automatically.
    """
    if output_path is None:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        output_path = DEFAULT_OUTPUT_DIR / f"pipeline_{ts}.mp4"

    # Compute target music length from video duration if not specified.
    # NOTE: Lyria has a fixed 32.768s clip duration regardless of this value;
    # the parameter only matters for source=elevenlabs. We still compute it for
    # the mix stage which uses the actual generated music length as the apad target.
    if music_length_ms is None:
        video_duration = _probe_duration(video_path)
        music_length_ms = max(int(video_duration * 1000), 3000)

    # Stage A: parallel TTS + music generation
    pipeline_t0 = time.time()
    print(json.dumps({"status": "stage_a", "step": "parallel_api_calls",
                      "music_source": music_source,
                      "tts_chars": len(narration_text),
                      "music_length_ms": music_length_ms}), file=sys.stderr)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        narr_future = executor.submit(
            generate_narration,
            text=narration_text,
            voice_id=voice_id,
            api_key=api_key,
            model_id=tts_model,
            voice_settings=voice_settings,
        )
        music_future = executor.submit(
            generate_music,
            prompt=music_prompt,
            api_key=api_key,  # only used if source=elevenlabs
            source=music_source,
            length_ms=music_length_ms,
            negative_prompt=music_negative_prompt,
            allow_creators=allow_creators,
        )
        narr_result = narr_future.result()
        music_result = music_future.result()

    # Stage B: mix narration over music with ducking
    print(json.dumps({"status": "stage_b", "step": "ffmpeg_mix"}), file=sys.stderr)
    # Use the ACTUAL generated music duration (probed from disk) rather than the
    # requested length_ms. Lyria delivers a fixed 32.768s clip regardless of the
    # requested length, and ElevenLabs may also produce slightly off-target durations.
    # The apad target in the mix stage must match what's actually on disk.
    actual_music_duration = _probe_duration(music_result["path"])
    mix_result = mix_narration_with_music(
        narration_path=Path(narr_result["path"]),
        music_path=Path(music_result["path"]),
        duration=actual_music_duration,
    )

    # Stage C: audio-swap into video
    print(json.dumps({"status": "stage_c", "step": "audio_swap"}), file=sys.stderr)
    swap_result = swap_audio_into_video(
        video_path=video_path,
        audio_path=Path(mix_result["path"]),
        output_path=output_path,
    )

    return {
        "final_path": str(output_path),
        "stages": {
            "narration": narr_result,
            "music": music_result,
            "mix": mix_result,
            "swap": swap_result,
        },
        "total_elapsed_seconds": round(time.time() - pipeline_t0, 2),
    }


# ---------------------------------------------------------------------------
# Voice Design (text-to-voice)
# ---------------------------------------------------------------------------


def design_voice(description: str, api_key: str, sample_text: str | None = None,
                 model_id: str = DEFAULT_TTV_MODEL,
                 guidance_scale: float = DEFAULT_GUIDANCE_SCALE,
                 should_enhance: bool = False) -> dict:
    """Call /v1/text-to-voice/design to generate 3 candidate voice previews.

    Returns a dict with the previews list (each containing generated_voice_id
    and a saved-to-disk MP3 path). The user listens to the previews and picks
    one to promote via voice-promote.
    """
    if sample_text is None:
        sample_text = (
            "The seasons change across this valley, painting the forest in red and gold. "
            "The river runs cold here, fed by mountain springs that have flowed for ten thousand years. "
            "Soon the forest sleeps, conserving its strength as winter slowly settles into the hollows."
        )

    body = {
        "voice_description": description,
        "model_id": model_id,
        "text": sample_text,
        "auto_generate_text": False,
        "loudness": 0.5,
        "guidance_scale": guidance_scale,
        "should_enhance": should_enhance,
    }
    url = f"{ELEVENLABS_API}/v1/text-to-voice/design"

    try:
        raw = _http_post_json(url, body, api_key, accept="application/json", timeout=240)
        data = json.loads(raw.decode())
    except urllib.error.HTTPError as e:
        _error_exit(f"voice design failed: {_http_error_message(e)}")
    except Exception as e:
        _error_exit(f"voice design failed: {type(e).__name__}: {e}")

    previews = data.get("previews") or data.get("voice_previews") or []
    if not previews:
        _error_exit(f"voice design returned no previews. Response keys: {list(data.keys())}")

    # Save each preview to disk
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    voice_dir = DEFAULT_OUTPUT_DIR / "voice-design" / time.strftime("%Y%m%d_%H%M%S")
    voice_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for i, p in enumerate(previews, start=1):
        gvid = p.get("generated_voice_id")
        audio_b64 = p.get("audio_base_64") or p.get("audio_base64") or p.get("audio")
        if not gvid or not audio_b64:
            continue
        audio_bytes = base64.b64decode(audio_b64)
        out = voice_dir / f"preview-{i}-{gvid[:12]}.mp3"
        with open(out, "wb") as f:
            f.write(audio_bytes)
        saved.append({
            "index": i,
            "generated_voice_id": gvid,
            "path": str(out),
            "bytes": len(audio_bytes),
        })

    # Save metadata file alongside the previews for later promote-step
    meta = {
        "voice_description": description,
        "sample_text": sample_text,
        "model_id": model_id,
        "guidance_scale": guidance_scale,
        "should_enhance": should_enhance,
        "previews": saved,
    }
    meta_path = voice_dir / "previews-metadata.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return {
        "voice_dir": str(voice_dir),
        "metadata_path": str(meta_path),
        "previews": saved,
        "voice_description": description,
    }


def promote_voice(generated_voice_id: str, name: str, role: str, api_key: str,
                  description: str | None = None,
                  source_type: str = "designed",
                  design_method: str = "text_to_voice",
                  model_id: str = DEFAULT_TTV_MODEL,
                  guidance_scale: float = DEFAULT_GUIDANCE_SCALE,
                  should_enhance: bool = False,
                  notes: str | None = None) -> dict:
    """POST /v1/text-to-voice to promote a preview to a permanent voice,
    then save the metadata to ~/.banana/config.json under custom_voices.{role}.
    """
    if description is None:
        description = name

    # Step 1: promote via API
    body = {
        "voice_name": name,
        "voice_description": description,
        "generated_voice_id": generated_voice_id,
    }
    url = f"{ELEVENLABS_API}/v1/text-to-voice"
    try:
        raw = _http_post_json(url, body, api_key, accept="application/json", timeout=60)
        data = json.loads(raw.decode())
    except urllib.error.HTTPError as e:
        _error_exit(f"voice promote failed: {_http_error_message(e)}")
    except Exception as e:
        _error_exit(f"voice promote failed: {type(e).__name__}: {e}")

    permanent_voice_id = data.get("voice_id")
    if not permanent_voice_id:
        _error_exit(f"promote response missing voice_id. Response keys: {list(data.keys())}")

    # Step 2: save to config under custom_voices.{role}
    config = _load_config()
    custom = config.get("custom_voices", {}) or {}
    custom[role] = {
        "voice_id": permanent_voice_id,
        "name": name,
        "description": description,
        "source_type": source_type,
        "design_method": design_method,
        "model_id": model_id,
        "guidance_scale": guidance_scale,
        "should_enhance": should_enhance,
        "created_at": date.today().isoformat(),
        "provider": "elevenlabs",
        "notes": notes or "",
    }
    config["custom_voices"] = custom
    _atomic_write_config(config)

    # v3.7.4: auto-measure WPM so the line-length calibration is ready
    # from the first real TTS call. Non-fatal if measurement fails — the
    # voice is already persisted; measurement can be re-run via voice-measure.
    measured_wpm = None
    try:
        measured_wpm = measure_voice_wpm(voice_id=permanent_voice_id, api_key=api_key)
        config2 = _load_config()
        custom2 = config2.get("custom_voices", {}) or {}
        if role in custom2:
            custom2[role]["wpm"] = measured_wpm
            custom2[role]["wpm_measured_at"] = date.today().isoformat()
            config2["custom_voices"] = custom2
            _atomic_write_config(config2)
    except Exception as e:
        print(json.dumps({
            "warning": "wpm_measurement_failed",
            "message": f"{type(e).__name__}: {e}",
            "note": "Voice was promoted successfully. Run `voice-measure --role {role}` to retry.",
        }), file=sys.stderr)

    return {
        "permanent_voice_id": permanent_voice_id,
        "role": role,
        "name": name,
        "measured_wpm": measured_wpm,
        "config_path": str(CONFIG_PATH),
    }


def list_voices() -> dict:
    """List all custom voices from ~/.banana/config.json."""
    config = _load_config()
    custom = config.get("custom_voices", {}) or {}
    return {
        "config_path": str(CONFIG_PATH),
        "voice_count": len(custom),
        "voices": custom,
    }


# ---------------------------------------------------------------------------
# Voice Cloning (Instant Voice Cloning — IVC) — v3.7.4
#
# IVC creates a custom voice from 30+ seconds of recorded audio. The user
# uploads one or more audio files describing a target speaker; ElevenLabs
# creates a permanent voice_id that can then be used with any TTS model.
#
# Endpoint: POST /v1/voices/add (multipart/form-data)
#   Required fields:
#     - name: display name for the voice
#     - files: one or more audio files (mp3/wav/m4a/flac/ogg/opus/webm/aiff)
#   Optional fields:
#     - description: free-form description of the voice
#     - labels: JSON-encoded dict with language/accent/gender/age keys
#     - remove_background_noise: "true" | "false" (default false)
#
# Response:
#   - voice_id: the permanent ID (save to custom_voices.{role})
#   - requires_verification: if true, user must complete voice captcha in
#     the ElevenLabs dashboard before the voice is usable
#
# Delta vs PVC (Professional Voice Cloning): PVC needs 30+ minutes of audio,
# Creator+ plan, and a multi-step fine-tuning workflow. Deferred to v3.7.5+.
#
# CRITICAL TOS: the user must have permission to clone the target voice.
# The plugin does not verify consent — that's the user's responsibility.
# ---------------------------------------------------------------------------


def _http_post_multipart(url: str, fields: dict[str, str], files: list[tuple[str, str, bytes]],
                         api_key: str, timeout: int = 240) -> dict:
    """POST multipart/form-data with one or more file parts. Returns parsed JSON.

    `fields` is a flat dict of text form fields (name → value).
    `files` is a list of (form_field_name, filename, bytes) tuples — multiple
    parts can share the same form_field_name (e.g. "files") to upload several
    audio samples in one request, which is how ElevenLabs IVC expects them.

    Uses only stdlib — constructs the multipart body by hand with a random
    boundary. No external dependencies.
    """
    import uuid
    boundary = f"----nanobanana{uuid.uuid4().hex}"
    crlf = b"\r\n"
    body = bytearray()

    # Text fields first
    for k, v in fields.items():
        body += f"--{boundary}".encode() + crlf
        body += f'Content-Disposition: form-data; name="{k}"'.encode() + crlf + crlf
        body += v.encode("utf-8") + crlf

    # File parts
    for form_name, filename, data in files:
        body += f"--{boundary}".encode() + crlf
        body += (
            f'Content-Disposition: form-data; name="{form_name}"; filename="{filename}"'
        ).encode() + crlf
        body += b"Content-Type: application/octet-stream" + crlf + crlf
        body += data + crlf

    body += f"--{boundary}--".encode() + crlf

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "xi-api-key": api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _collect_audio_files(audio_arg: str) -> list[Path]:
    """Resolve the --audio argument to a list of audio files.

    Accepts either a single file path or a directory. If a directory, returns
    all files with common audio extensions (.mp3 .wav .m4a .flac .ogg .opus .aiff
    .webm) sorted alphabetically. Errors if no audio files are found.
    """
    p = Path(audio_arg).expanduser().resolve()
    extensions = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".opus", ".aiff", ".webm"}
    if p.is_file():
        return [p]
    if p.is_dir():
        files = sorted(f for f in p.iterdir() if f.is_file() and f.suffix.lower() in extensions)
        if not files:
            _error_exit(f"no audio files found in {p} (looked for: {sorted(extensions)})")
        return files
    _error_exit(f"audio path not found: {p}")
    return []  # unreachable


def clone_voice(audio_paths: list[Path], name: str, role: str, api_key: str,
                description: str | None = None,
                labels: dict[str, str] | None = None,
                remove_background_noise: bool = False,
                notes: str | None = None,
                auto_measure_wpm: bool = True) -> dict:
    """Instant Voice Clone: upload audio sample(s), save to custom_voices.{role}.

    Requires at least 30 seconds of total audio across all uploaded files.
    Each audio file must be a supported format (mp3/wav/m4a/flac/ogg/opus/aiff/webm).

    On success, persists the new voice_id to ~/.banana/config.json under
    custom_voices.{role} with source_type="cloned" and design_method="ivc".
    If auto_measure_wpm is True (default), runs a one-shot WPM measurement
    immediately after cloning so the caller can use the voice with correct
    line-length calibration from the first real TTS call.

    The response may contain requires_verification=True — if so, the user
    must complete a voice-captcha in the ElevenLabs dashboard before the
    voice is usable. The function still persists the metadata in that case
    (so the user doesn't lose track of the voice_id) but includes a warning.
    """
    if not audio_paths:
        _error_exit("clone_voice requires at least one audio file")

    # Read file contents and build the multipart payload
    files_payload: list[tuple[str, str, bytes]] = []
    total_bytes = 0
    for p in audio_paths:
        with open(p, "rb") as f:
            data = f.read()
        files_payload.append(("files", p.name, data))
        total_bytes += len(data)

    # Sanity-check minimum duration via ffprobe on the first file as a
    # lightweight guard. 30 seconds is ElevenLabs's documented minimum —
    # not enforced client-side, but warn if the total looks suspicious.
    total_duration = 0.0
    for p in audio_paths:
        try:
            total_duration += _probe_duration(p)
        except Exception:
            pass
    if total_duration and total_duration < 25.0:
        # Warn-and-continue rather than block — ElevenLabs will give the
        # authoritative rejection if the total is too short.
        print(json.dumps({
            "warning": "total_audio_duration_below_ivc_minimum",
            "total_duration_seconds": round(total_duration, 1),
            "recommended_minimum": 30,
            "message": "ElevenLabs IVC recommends 30+ seconds of audio. Continuing anyway; upstream will reject if truly insufficient.",
        }), file=sys.stderr)

    fields: dict[str, str] = {
        "name": name,
        "remove_background_noise": "true" if remove_background_noise else "false",
    }
    if description:
        fields["description"] = description
    if labels:
        fields["labels"] = json.dumps(labels)

    url = f"{ELEVENLABS_API}/v1/voices/add"

    t0 = time.time()
    try:
        data = _http_post_multipart(url, fields, files_payload, api_key, timeout=300)
    except urllib.error.HTTPError as e:
        _error_exit(f"voice clone failed: {_http_error_message(e)}")
    except Exception as e:
        _error_exit(f"voice clone failed: {type(e).__name__}: {e}")

    voice_id = data.get("voice_id")
    requires_verification = bool(data.get("requires_verification", False))
    if not voice_id:
        _error_exit(f"clone response missing voice_id. Response keys: {list(data.keys())}")

    # Persist to config under custom_voices.{role}
    config = _load_config()
    custom = config.get("custom_voices", {}) or {}

    entry: dict = {
        "voice_id": voice_id,
        "name": name,
        "description": description or name,
        "source_type": "cloned",
        "design_method": "ivc",
        "model_id": DEFAULT_TTS_MODEL,  # cloned voices work with the default TTS model
        "created_at": date.today().isoformat(),
        "provider": "elevenlabs",
        "source_audio_count": len(audio_paths),
        "source_audio_total_bytes": total_bytes,
        "source_audio_total_duration_sec": round(total_duration, 1) if total_duration else None,
        "requires_verification": requires_verification,
        "labels": labels or {},
        "notes": notes or "",
    }
    custom[role] = entry
    config["custom_voices"] = custom
    _atomic_write_config(config)

    # v3.7.4: auto-measure WPM unless the voice requires verification
    # (measurement would fail with HTTP 400 until the captcha is completed).
    measured_wpm = None
    if auto_measure_wpm and not requires_verification:
        try:
            measured_wpm = measure_voice_wpm(voice_id=voice_id, api_key=api_key)
            # Re-load + patch WPM into the entry, then re-save atomically
            config2 = _load_config()
            custom2 = config2.get("custom_voices", {}) or {}
            if role in custom2:
                custom2[role]["wpm"] = measured_wpm
                config2["custom_voices"] = custom2
                _atomic_write_config(config2)
        except Exception as e:
            print(json.dumps({
                "warning": "wpm_measurement_failed",
                "message": f"{type(e).__name__}: {e}",
                "note": "Voice was cloned successfully; WPM can be measured later via voice-measure subcommand.",
            }), file=sys.stderr)

    return {
        "voice_id": voice_id,
        "role": role,
        "name": name,
        "requires_verification": requires_verification,
        "source_audio_count": len(audio_paths),
        "source_audio_total_bytes": total_bytes,
        "source_audio_total_duration_sec": round(total_duration, 1) if total_duration else None,
        "measured_wpm": measured_wpm,
        "config_path": str(CONFIG_PATH),
        "elapsed_seconds": round(time.time() - t0, 2),
        "verification_note": (
            "ElevenLabs requires voice captcha verification before this cloned voice can be used. "
            "Visit https://elevenlabs.io/app/voice-lab to complete verification."
        ) if requires_verification else None,
    }


# ---------------------------------------------------------------------------
# Auto-measured per-voice WPM — v3.7.4
#
# The line-length calibration rule (F8 in video-audio.md) needs a per-voice
# words-per-minute figure: target_words = duration_sec × (voice_wpm / 60).
# v3.7.1 hardcoded 137 wpm (Daniel) and 159 wpm (Nano Banana Narrator) in
# reference docs, leaving the calibration fragile for any new voice.
#
# v3.7.4 measures WPM empirically on first use: generate a known-word-count
# reference phrase through the voice, probe the audio duration with ffprobe,
# compute actual wpm. The result is persisted to custom_voices.{role}.wpm
# so the creative-director skill can read it without re-measuring.
#
# Automatically triggered by voice-promote and voice-clone. Can be invoked
# standalone via `voice-measure --role ROLE` for existing voices that pre-date
# v3.7.4 and don't have a measured wpm yet.
# ---------------------------------------------------------------------------

# Reference phrase: 30 words, neutral news-register content, no audio tags.
# 30 words is long enough to average out micro-pauses and short enough to
# stay well below ElevenLabs's character limits. The phrase is neutral so
# it doesn't trigger dramatic speech variations that would distort WPM.
WPM_REFERENCE_PHRASE = (
    "The autumn wind moved across the valley and gathered the fallen leaves "
    "into small bright drifts beneath the oaks. Above the ridge the first "
    "stars appeared, patient and distant, waiting for the long night."
)
WPM_REFERENCE_WORD_COUNT = 38  # len(WPM_REFERENCE_PHRASE.split())


def measure_voice_wpm(voice_id: str, api_key: str,
                      reference_phrase: str | None = None,
                      model_id: str = DEFAULT_TTS_MODEL) -> float:
    """Measure a voice's effective words-per-minute by generating the reference
    phrase and probing the resulting audio duration.

    Returns the measured WPM rounded to the nearest integer. Raises on failure.

    Cost: one TTS call with ~40 words → a fraction of a cent on subscription
    tiers (character-billed). Negligible compared to voice-design ($~0.01
    per 3-candidate design call).

    Known limitations:
    - Eleven v3 audio tags can change pacing dramatically, so the measurement
      is for the voice's NEUTRAL pace. Users applying heavy [contemplative]
      / [wistful] tagging should expect their effective output pace to be
      10-20% slower than the measured value.
    - A single 40-word sample has some variance. Run the measurement twice
      and average if you need precision better than ±5 WPM.
    """
    phrase = reference_phrase or WPM_REFERENCE_PHRASE
    word_count = len(phrase.split())

    # Generate to a temp file so we don't pollute the default output dir
    tmp = Path(tempfile.mkstemp(prefix="wpm_ref_", suffix=".mp3")[1])
    try:
        generate_narration(
            text=phrase,
            voice_id=voice_id,
            api_key=api_key,
            model_id=model_id,
            output_path=tmp,
        )
        duration_sec = _probe_duration(tmp)
        if duration_sec <= 0:
            raise RuntimeError("ffprobe returned zero duration")
        wpm = word_count / (duration_sec / 60.0)
        return round(wpm, 1)
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


def voice_measure(role: str, api_key: str) -> dict:
    """CLI entry point: measure WPM for an existing custom voice and persist.

    Looks up the voice by role in custom_voices, generates the reference
    phrase, computes WPM, updates custom_voices.{role}.wpm in config.
    Useful for voices that pre-date v3.7.4 and don't have a measured wpm yet.
    """
    voice_id, meta = _resolve_voice(role)
    if meta is None:
        _error_exit(
            f"role {role!r} not found in custom_voices. Use voice-list to see saved voices."
        )

    t0 = time.time()
    wpm = measure_voice_wpm(voice_id=voice_id, api_key=api_key)

    # Patch the custom_voices entry with the new WPM
    config = _load_config()
    custom = config.get("custom_voices", {}) or {}
    if role in custom:
        custom[role]["wpm"] = wpm
        custom[role]["wpm_measured_at"] = date.today().isoformat()
        config["custom_voices"] = custom
        _atomic_write_config(config)

    return {
        "role": role,
        "voice_id": voice_id,
        "wpm": wpm,
        "reference_word_count": WPM_REFERENCE_WORD_COUNT,
        "elapsed_seconds": round(time.time() - t0, 2),
        "note": (
            "Target words for an 8-second clip at this voice's pace: "
            f"{round(8 * (wpm / 60.0))} words. "
            "See skills/video/references/video-audio.md → F8 for the line-length rule."
        ),
    }


# ---------------------------------------------------------------------------
# Status check
# ---------------------------------------------------------------------------


def status() -> dict:
    """Verify both music sources (Lyria + ElevenLabs), ffmpeg, and custom voice library."""
    result: dict = {"checks": []}

    config = _load_config()

    # Lyria (Vertex AI) — primary music source as of v3.7.2
    has_vertex = bool(
        config.get("vertex_api_key")
        and config.get("vertex_project_id")
        and config.get("vertex_location")
    )
    result["checks"].append({
        "name": "lyria_vertex_credentials",
        "ok": has_vertex,
        "vertex_project_id": config.get("vertex_project_id") if has_vertex else None,
        "vertex_location": config.get("vertex_location") if has_vertex else None,
    })

    # ElevenLabs — narration TTS + alternative music source
    has_key = bool(config.get("elevenlabs_api_key")) or bool(os.environ.get("ELEVENLABS_API_KEY"))
    result["checks"].append({"name": "elevenlabs_api_key", "ok": has_key})

    # API auth
    if has_key:
        try:
            api_key = _get_api_key()
            data = _http_get_json(f"{ELEVENLABS_API}/v1/user", api_key, timeout=15)
            sub = data.get("subscription", {})
            result["checks"].append({
                "name": "elevenlabs_auth",
                "ok": True,
                "tier": sub.get("tier", "unknown"),
                "character_limit": sub.get("character_limit"),
                "character_count": sub.get("character_count"),
            })
        except Exception as e:
            result["checks"].append({"name": "elevenlabs_auth", "ok": False, "error": str(e)})

    # ffmpeg
    ffmpeg_path = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True).stdout.strip()
    result["checks"].append({"name": "ffmpeg", "ok": bool(ffmpeg_path), "path": ffmpeg_path})

    # ffprobe
    ffprobe_path = subprocess.run(["which", "ffprobe"], capture_output=True, text=True).stdout.strip()
    result["checks"].append({"name": "ffprobe", "ok": bool(ffprobe_path), "path": ffprobe_path})

    # Custom voices
    custom = config.get("custom_voices", {}) or {}
    result["checks"].append({
        "name": "custom_voices",
        "count": len(custom),
        "roles": sorted(custom.keys()),
    })

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audio replacement pipeline for nano-banana-studio v3.7.2+ (Lyria + ElevenLabs)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # status
    sub.add_parser("status", help="Check API keys, ffmpeg, custom voices, and music sources")

    # narrate
    p_narr = sub.add_parser("narrate", help="Generate TTS narration from text (ElevenLabs)")
    p_narr.add_argument("--text", required=True)
    p_narr.add_argument("--voice", help="Voice role name or literal voice_id (defaults to narrator role)")
    p_narr.add_argument("--model", default=DEFAULT_TTS_MODEL)
    p_narr.add_argument("--out", help="Output mp3 path (default: ~/Documents/nano-banana-audio/narration_TS.mp3)")
    p_narr.add_argument("--api-key")

    # music (multi-provider, v3.7.2+)
    p_music = sub.add_parser("music", help="Generate background music (Lyria default, ElevenLabs alternative)")
    p_music.add_argument("--prompt", required=True)
    p_music.add_argument("--source", choices=["lyria", "elevenlabs"], default=DEFAULT_MUSIC_SOURCE,
                         help=f"Music provider (default: {DEFAULT_MUSIC_SOURCE}). "
                              "Lyria: $0.06 fixed, 32.768s, 48kHz/192kbps, supports negative_prompt, Vertex auth. "
                              "ElevenLabs: subscription, configurable length, 44.1kHz/128kbps, no negative_prompt.")
    p_music.add_argument("--negative-prompt", default=None,
                         help="What to avoid (Lyria only — ElevenLabs ignores this)")
    p_music.add_argument("--length-ms", type=int, default=DEFAULT_MUSIC_LENGTH_MS,
                         help="Length in ms (ElevenLabs only — Lyria has fixed 32.768s)")
    p_music.add_argument("--with-vocals", action="store_true",
                         help="Allow vocals (ElevenLabs only — Lyria is always instrumental)")
    p_music.add_argument("--no-wav", action="store_true",
                         help="(Lyria only) Skip saving the lossless WAV source. By default both .mp3 and .wav are saved.")
    p_music.add_argument("--mp3-bitrate", default="256k",
                         help="(Lyria only) MP3 transcode bitrate (default: 256k for transparent quality). Use 192k to match v3.7.1 ElevenLabs convention.")
    p_music.add_argument("--out")
    p_music.add_argument("--api-key", help="ElevenLabs API key (only needed when source=elevenlabs)")
    p_music.add_argument("--allow-creators", action="store_true",
                         help="(v3.7.4) Bypass client-side named-creator stripping. "
                              "By default, prompts mentioning known copyrighted creators/publications "
                              "(Annie Leibovitz, Vanity Fair, BBC Earth, Hans Zimmer, etc.) are stripped "
                              "before sending — both Lyria and Eleven Music reject them server-side. "
                              "Pass this flag to disable the strip and test whether the upstream filter "
                              "has relaxed for a specific term.")

    # mix
    p_mix = sub.add_parser("mix", help="FFmpeg mix narration + music with side-chain ducking")
    p_mix.add_argument("--narration", required=True)
    p_mix.add_argument("--music", required=True)
    p_mix.add_argument("--out")
    p_mix.add_argument("--duration", type=float,
                       help="Target output duration in seconds (defaults to longer of inputs)")

    # swap
    p_swap = sub.add_parser("swap", help="Audio-swap an audio track into a video")
    p_swap.add_argument("--video", required=True)
    p_swap.add_argument("--audio", required=True)
    p_swap.add_argument("--out")

    # pipeline (the canonical end-to-end command)
    p_pipe = sub.add_parser("pipeline", help="End-to-end: parallel TTS + music, mix, swap into video")
    p_pipe.add_argument("--video", required=True, help="Source video file (audio will be replaced)")
    p_pipe.add_argument("--text", required=True, help="Narration text (with audio tags, ellipses, CAPS as desired)")
    p_pipe.add_argument("--music-prompt", required=True,
                        help="Music description (no named creators/brands — both Lyria and ElevenLabs reject these)")
    p_pipe.add_argument("--music-source", choices=["lyria", "elevenlabs"], default=DEFAULT_MUSIC_SOURCE,
                        help=f"Music provider (default: {DEFAULT_MUSIC_SOURCE}). See music subcommand for details.")
    p_pipe.add_argument("--music-negative-prompt", default=None,
                        help="What to avoid in music (Lyria only — improves prompt fidelity)")
    p_pipe.add_argument("--voice", help="Voice role or voice_id (default: narrator)")
    p_pipe.add_argument("--music-length-ms", type=int,
                        help="Music length in ms (ElevenLabs only — Lyria has fixed 32.768s)")
    p_pipe.add_argument("--out", help="Final output mp4 path")
    p_pipe.add_argument("--tts-model", default=DEFAULT_TTS_MODEL)
    p_pipe.add_argument("--api-key")
    p_pipe.add_argument("--allow-creators", action="store_true",
                        help="(v3.7.4) Bypass client-side named-creator stripping on the music prompt.")

    # voice-design
    p_vd = sub.add_parser("voice-design", help="Generate voice previews from a text description")
    p_vd.add_argument("--description", required=True, help="Voice description (20-1000 chars)")
    p_vd.add_argument("--sample-text", help="Sample text for the previews to speak")
    p_vd.add_argument("--model", default=DEFAULT_TTV_MODEL,
                      choices=["eleven_ttv_v3", "eleven_multilingual_ttv_v2"])
    p_vd.add_argument("--guidance-scale", type=float, default=DEFAULT_GUIDANCE_SCALE)
    p_vd.add_argument("--enhance", action="store_true", help="AI-expand the description")
    p_vd.add_argument("--api-key")

    # voice-promote
    p_vp = sub.add_parser("voice-promote", help="Promote a preview to a permanent saved voice")
    p_vp.add_argument("--generated-id", required=True, help="generated_voice_id from voice-design output")
    p_vp.add_argument("--name", required=True, help="Display name for the saved voice")
    p_vp.add_argument("--role", required=True,
                      help="Semantic role (e.g. narrator, character_a, brand_voice)")
    p_vp.add_argument("--description", help="Voice description (defaults to name)")
    p_vp.add_argument("--source-type", default="designed", choices=["designed", "cloned", "library"])
    p_vp.add_argument("--design-method", default="text_to_voice", choices=["text_to_voice", "remix"])
    p_vp.add_argument("--model", default=DEFAULT_TTV_MODEL)
    p_vp.add_argument("--guidance-scale", type=float, default=DEFAULT_GUIDANCE_SCALE)
    p_vp.add_argument("--should-enhance", action="store_true")
    p_vp.add_argument("--notes", help="Free-form context (pacing, A/B history, etc.)")
    p_vp.add_argument("--api-key")

    # voice-clone (v3.7.4 — ElevenLabs Instant Voice Cloning)
    p_vc = sub.add_parser("voice-clone",
                          help="(v3.7.4) Clone a voice from 30+ seconds of audio sample(s). "
                               "Saves to custom_voices.{role} with source_type=cloned.")
    p_vc.add_argument("--audio", required=True,
                      help="Path to a single audio file OR a directory of audio files. "
                           "Accepts mp3, wav, m4a, flac, ogg, opus, aiff, webm. "
                           "Total duration should be at least 30 seconds.")
    p_vc.add_argument("--name", required=True, help="Display name for the cloned voice")
    p_vc.add_argument("--role", required=True,
                      help="Semantic role (e.g. narrator, character_a, brand_voice, client_ceo)")
    p_vc.add_argument("--description", help="Free-form description of the voice character")
    p_vc.add_argument("--label-language", help="Language label (e.g. 'en', 'en-US', 'ja')")
    p_vc.add_argument("--label-accent", help="Accent label (e.g. 'british', 'midwest', 'australian')")
    p_vc.add_argument("--label-gender", help="Gender label (e.g. 'female', 'male', 'non-binary')")
    p_vc.add_argument("--label-age", help="Age label (e.g. 'young', 'middle_aged', 'old')")
    p_vc.add_argument("--remove-background-noise", action="store_true",
                      help="Enable ElevenLabs background noise removal during cloning")
    p_vc.add_argument("--notes", help="Free-form context (consent status, source recording details, etc.)")
    p_vc.add_argument("--no-auto-wpm", action="store_true",
                      help="Skip the automatic WPM measurement after cloning")
    p_vc.add_argument("--api-key")

    # voice-measure (v3.7.4 — retroactive WPM measurement)
    p_vm = sub.add_parser("voice-measure",
                          help="(v3.7.4) Measure words-per-minute for an existing custom voice "
                               "and persist to custom_voices.{role}.wpm. Used by the line-length "
                               "calibration rule (F8 in video-audio.md).")
    p_vm.add_argument("--role", required=True, help="Semantic role of an existing custom voice")
    p_vm.add_argument("--api-key")

    # voice-list
    sub.add_parser("voice-list", help="List custom voices saved in ~/.banana/config.json")

    args = parser.parse_args()

    # Dispatch
    if args.cmd == "status":
        result = status()
    elif args.cmd == "narrate":
        api_key = _get_api_key(args.api_key)
        voice_id, _ = _resolve_voice(args.voice)
        result = generate_narration(
            text=args.text,
            voice_id=voice_id,
            api_key=api_key,
            model_id=args.model,
            output_path=Path(args.out) if args.out else None,
        )
    elif args.cmd == "music":
        # Lyria reads vertex_api_key from config; ElevenLabs needs its own key.
        # Only fetch the ElevenLabs key when source=elevenlabs.
        api_key = None
        if args.source == "elevenlabs":
            api_key = _get_api_key(args.api_key)
        result = generate_music(
            prompt=args.prompt,
            api_key=api_key,
            source=args.source,
            length_ms=args.length_ms,
            negative_prompt=args.negative_prompt,
            force_instrumental=not args.with_vocals,
            output_path=Path(args.out) if args.out else None,
            keep_wav=not args.no_wav,
            mp3_bitrate=args.mp3_bitrate,
            allow_creators=args.allow_creators,
        )
    elif args.cmd == "mix":
        result = mix_narration_with_music(
            narration_path=Path(args.narration),
            music_path=Path(args.music),
            output_path=Path(args.out) if args.out else None,
            duration=args.duration,
        )
    elif args.cmd == "swap":
        result = swap_audio_into_video(
            video_path=Path(args.video),
            audio_path=Path(args.audio),
            output_path=Path(args.out) if args.out else None,
        )
    elif args.cmd == "pipeline":
        # ElevenLabs key is always needed (TTS narration uses it). Lyria for music
        # uses Vertex auth from config and doesn't need this key.
        api_key = _get_api_key(args.api_key)
        voice_id, _ = _resolve_voice(args.voice)
        result = pipeline(
            video_path=Path(args.video),
            narration_text=args.text,
            music_prompt=args.music_prompt,
            voice_id=voice_id,
            api_key=api_key,
            output_path=Path(args.out) if args.out else None,
            music_length_ms=args.music_length_ms,
            music_source=args.music_source,
            music_negative_prompt=args.music_negative_prompt,
            tts_model=args.tts_model,
            allow_creators=args.allow_creators,
        )
    elif args.cmd == "voice-design":
        api_key = _get_api_key(args.api_key)
        result = design_voice(
            description=args.description,
            api_key=api_key,
            sample_text=args.sample_text,
            model_id=args.model,
            guidance_scale=args.guidance_scale,
            should_enhance=args.enhance,
        )
    elif args.cmd == "voice-promote":
        api_key = _get_api_key(args.api_key)
        result = promote_voice(
            generated_voice_id=args.generated_id,
            name=args.name,
            role=args.role,
            api_key=api_key,
            description=args.description,
            source_type=args.source_type,
            design_method=args.design_method,
            model_id=args.model,
            guidance_scale=args.guidance_scale,
            should_enhance=args.should_enhance,
            notes=args.notes,
        )
    elif args.cmd == "voice-clone":
        api_key = _get_api_key(args.api_key)
        audio_paths = _collect_audio_files(args.audio)
        labels: dict[str, str] = {}
        if args.label_language:
            labels["language"] = args.label_language
        if args.label_accent:
            labels["accent"] = args.label_accent
        if args.label_gender:
            labels["gender"] = args.label_gender
        if args.label_age:
            labels["age"] = args.label_age
        result = clone_voice(
            audio_paths=audio_paths,
            name=args.name,
            role=args.role,
            api_key=api_key,
            description=args.description,
            labels=labels or None,
            remove_background_noise=args.remove_background_noise,
            notes=args.notes,
            auto_measure_wpm=not args.no_auto_wpm,
        )
    elif args.cmd == "voice-measure":
        api_key = _get_api_key(args.api_key)
        result = voice_measure(role=args.role, api_key=api_key)
    elif args.cmd == "voice-list":
        result = list_voices()
    else:
        parser.print_help()
        sys.exit(2)

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
