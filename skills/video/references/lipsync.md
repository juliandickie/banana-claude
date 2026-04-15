# Fabric 1.0 Audio-Driven Lip-Sync (v3.8.1+)

> Load this when the user wants to pair a custom-voice narration with a
> visible character in a video. The authoritative source for Fabric 1.0
> capabilities is the model card at `dev-docs/veed-fabric-1.0-llms.md`.

## Why `/video lipsync` exists

Before v3.8.1, the plugin had a concrete UX gap:

- **VEO 3.1** generates speech internally from prompts. You can't feed it a
  pre-recorded audio file or a custom-designed ElevenLabs voice — VEO decides
  what the speaker sounds like.
- **Kling v3 Std** (v3.8.0 default) doesn't accept audio input at all. Its
  `generate_audio` flag produces emergent audio from the prompt, not from
  user-supplied voice files.
- **audio_pipeline.py narrate** (v3.7.1) generates high-quality ElevenLabs
  TTS narrations using custom-designed or cloned voices — but there was no
  way to attach those narrations to a visible character's face in a video.

**VEED Fabric 1.0** (via Replicate) closes the gap. It's a specialized
audio-driven talking-head model: give it a face image + any audio file, and
it produces a video where the face is lip-synced to the audio. This enables
the workflow the v3.7.x audio stack was always pointing at:

1. Generate a custom voice via `audio_pipeline.py voice-design` or
   `voice-clone` (v3.7.1 / v3.7.4)
2. Generate narration with that voice via `audio_pipeline.py narrate`
3. Generate a face via `banana generate` (or use any photo)
4. Call `/video lipsync` to combine the face + narration into a lip-synced MP4

## Model capabilities (Fabric 1.0)

| Property | Value |
|---|---|
| Input image formats | `jpg`, `jpeg`, `png` (max 10 MB enforced client-side) |
| Input audio formats | `mp3`, `wav`, `m4a`, `aac` (max ~50 MB enforced client-side) |
| Output resolution | **480p** or **720p** (no 1080p or 4K) |
| Maximum output duration | **60 seconds** (driven by audio length) |
| Output format | MP4 (single URI string from Replicate) |
| Pricing | Approximately $0.30/call — estimate only; v3.8.1 verification measures empirically |

**Important**: Fabric does NOT generate new content from a prompt. It only
drives the existing image's face to match the audio's speech. Everything
else in the frame stays static. If you want motion beyond lip-sync, use
Kling or VEO with a narrative prompt instead.

## Canonical 2-step workflow

```bash
# Step 1 — generate the narration with your custom voice
python3 audio_pipeline.py narrate \
    --text "Hey everyone, welcome to our product demo. Today I'll show you what makes our approach different." \
    --voice narrator \
    --out /tmp/narration.mp3

# Step 2 — lip-sync a face image to the narration
python3 video_lipsync.py \
    --image face.png \
    --audio /tmp/narration.mp3 \
    --resolution 720p \
    --output ~/Documents/nanobanana_generated
```

The two scripts are deliberately decoupled: `audio_pipeline.py` outputs an
MP3 at a path you control, and `video_lipsync.py` accepts any path. No
coupling, no cross-skill imports. Users can also feed `video_lipsync.py`
any pre-recorded voice-over, not just audio_pipeline.py output.

## When to use `/video lipsync` vs alternatives

| Use case | Recommended path |
|---|---|
| **Custom-designed voice speaks from a visible face** | `/video lipsync` (Fabric) — the reason this subcommand exists |
| Real human's recorded voice-over + face photo | `/video lipsync` — Fabric accepts any audio file |
| Simple talking-head from text with any voice VEO picks | `/video generate --provider veo` with dialogue in the prompt |
| Multi-shot narrative with motion beyond lip-sync | `/video generate --provider kling` (default) or `/video sequence` |
| Character animating through a full scene (not just face) | Not available in v3.8.1 — queued for potential v3.9.x DreamActor M2.0 integration |
| Background music + narration + video | `audio_pipeline.py pipeline` — generates a full stitched A/V track |

## Example: ElevenLabs custom voice + Banana face + Fabric lip-sync

This is the showcase workflow the audio pipeline was designed for:

```bash
# 0. One-time: design or clone a custom voice (skip if already done)
python3 audio_pipeline.py voice-design \
    --description "warm baritone with a slight British accent, BBC documentary register" \
    --role brand_voice

# 1. Generate the narration
python3 audio_pipeline.py narrate \
    --text "At our company, we believe every product should tell a story. Today, I want to share ours." \
    --voice brand_voice \
    --out /tmp/brand-narration.mp3

# 2. Generate a face via /banana
python3 skills/banana/scripts/generate.py \
    --prompt "A professional portrait of a woman in her 40s, warm expression, direct eye contact, soft studio lighting, business casual, slightly off-center framing. Photorealistic, shallow depth of field." \
    --output /tmp/brand-face.png

# 3. Lip-sync the face to the narration
python3 skills/video/scripts/video_lipsync.py \
    --image /tmp/brand-face.png \
    --audio /tmp/brand-narration.mp3 \
    --resolution 720p

# Output: ~/Documents/nanobanana_generated/lipsync_<timestamp>.mp4
```

Total cost: ~$0.08 (face image) + ~$0.30 (Fabric lip-sync) + ElevenLabs
subscription. Wall time: ~2-3 minutes for all 3 steps.

## Known limitations (from the Fabric model card)

- **Max 60 seconds per call** — driven by audio length. For longer content,
  split the narration into ≤60s chunks and stitch the resulting lip-sync
  clips with `video_stitch.py` (or the FFmpeg concat demuxer).
- **480p / 720p only** — no 1080p or 4K. For higher-resolution talking heads,
  no current plugin path exists. Upscaling post-hoc via an image model is
  possible but unsupported in v3.8.1.
- **Face quality depends on the input image** — Fabric preserves the input
  image's style, lighting, and framing. Garbage in = garbage out. A
  Banana-generated face gives more control than a real photo for
  brand-consistent workflows.
- **No emotional direction beyond the audio** — Fabric infers expression
  from the audio's prosody. You can't prompt "happy" or "serious"
  explicitly; bake emotion into the narration via audio_pipeline.py tags
  (`[warm]`, `[reverent]`, etc.) and Fabric will pick up the delivery.
- **No camera movement** — the camera is locked to the input image's frame.
  Everything outside the face stays static.
- **Mouth region only** — Fabric animates the mouth and face area. Body,
  hands, and background are not animated. For full-body motion, no current
  plugin path exists.

## Why Fabric is a separate script (not in `video_generate.py`)

Design note: `video_lipsync.py` is deliberately a standalone script rather
than a new `--provider fabric` flag on `video_generate.py`. The reason:
Fabric's input shape is fundamentally different from Kling and VEO.

- Kling / VEO: `--prompt "..."` + `--duration N` + `--aspect-ratio X:Y`.
  Fabric: `--image FACE.png` + `--audio FILE.mp3`. No prompt, no duration,
  no aspect ratio.

Folding Fabric into `video_generate.py` would have polluted the argparse
surface with flags that only apply to one path. The standalone script
reuses `_replicate_backend.py` for HTTP plumbing (zero duplication on the
Replicate side — same auth, same polling, same output handling) but keeps
its own narrow CLI that matches what Fabric actually accepts.

This is the same pattern as `video_sequence.py`, `video_extend.py`, and
`audio_pipeline.py` — each subcommand with a distinct input shape gets
its own script; the `_*_backend.py` helpers are shared.

## Cost compared to alternatives

| Workflow | Approx cost | Notes |
|---|---|---|
| `/video lipsync` (Fabric, 720p, ~8s audio) | ~$0.30 | Talking head only, no motion |
| `/video generate --provider kling` (8s, 1080p) | $0.16 | Full motion + native audio, but no custom voice |
| `/video generate --provider veo --tier lite` (8s) | $0.40 | Full motion + VEO-generated voice, no custom voice |
| `audio_pipeline.py pipeline` (8s) | ~$0.06-0.10 | Audio only, no visual |
| Kling + Fabric (compose separately) | ~$0.46 | Motion from Kling, lip-sync overlay from Fabric — but these don't auto-compose. Manual workflow. |

Fabric at ~$0.30 is cheaper than VEO Lite at $0.40 for the narrow
talking-head use case, while giving you full control over the voice.

## Deferred to v3.9.x+

- **Auto-pipeline from text → voice → face → lip-sync** in a single command.
  Currently requires 3 separate script invocations.
- **DreamActor M2.0 integration** for full-body character animation (not
  just face). Would require a new script + reference doc; queued for future
  research if a user workflow demands it.
- **Upscaling post-Fabric** via an image-upres model (Real-ESRGAN on
  Replicate) for 1080p talking-head output. Not in scope for v3.8.1.
