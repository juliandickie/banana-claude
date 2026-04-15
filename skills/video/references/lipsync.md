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
| Pricing | **~$0.15 per second of output video** — authoritative, verified 2026-04-15 via Replicate predictions dashboard. Linear formula, cold-start-independent. A 7s clip = $1.05, 8s = $1.20, 60s maximum = $9.00. See §Empirical verification (v3.8.1). |

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

Total cost: ~$0.08 (face image) + **~$1.05** (Fabric lip-sync at $0.15/s × 7s)
+ ElevenLabs subscription ≈ **$1.13**. Wall time: ~2-3 minutes for all 3 steps.
The Fabric component is the dominant cost — see §Empirical verification for
the per-second pricing formula and the $9.00 cost ceiling at 60s output.

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
| `/video lipsync` (Fabric, 720p, 7s audio) | **$1.05** | $0.15/s output. Talking head only, no motion. |
| `/video lipsync` (Fabric, 720p, 8s audio) | **$1.20** | Same $0.15/s rate; cold-start adds wall time but not cost. |
| `/video lipsync` (Fabric, 720p, 60s max) | **$9.00** | The cost ceiling. Split longer narrations across multiple clips if cost matters. |
| `/video generate --provider kling` (8s, 1080p) | $0.16 | Full motion + native audio, but no custom voice |
| `/video generate --provider veo --tier lite` (8s) | $0.40 | Full motion + VEO-generated voice, no custom voice |
| `audio_pipeline.py pipeline` (8s) | ~$0.06-0.10 | Audio only, no visual |
| Kling + Fabric (compose separately) | ~$1.21 ($0.16 + $1.05) | Motion from Kling, lip-sync overlay from Fabric — manual workflow, no auto-compose. |

**Fabric at $1.05-$1.20 per 7-8s clip is ~2-3× MORE expensive than VEO Lite**
($0.40/8s) — the reverse of what session 18's first draft of this doc claimed.
Fabric is still the only path to pair a custom-designed ElevenLabs voice with
a visible face — VEO generates speech internally (no external audio input)
and Kling doesn't accept audio input at all. **The trade-off is voice-control
for cost**, not voice-control plus savings. For cost-sensitive workflows where
the voice identity doesn't have to match a specific brand voice, use `/video
generate --provider veo --tier lite` with dialogue in the prompt instead —
it's roughly one-third the cost.

## Empirical verification (v3.8.1)

`/video lipsync` was verified end-to-end via three successful Replicate
predictions on 2026-04-15 using a Banana-generated portrait + an ElevenLabs
custom voice (the `narrator_female` voice designed specifically for this test
during session 18 — see `~/.banana/config.json` `custom_voices.narrator_female`).

| Metric | Cold start (run 1) | Warm (run 2) | Warm (run 3) |
|---|---|---|---|
| Prediction ID | `w36styf3c9rmw0cxj3cbyvnxz8` | `j3qp5ndaanrmr0cxj4qrnrhhf4` | `55qej5ghs1rmw0cxj4wr1wjgdg` |
| `predict_time` (Replicate metrics) | **161.04 s** | **123.44 s** | **125.22 s** |
| Output duration | 8 s | 7 s | 7 s |
| Output resolution | 720p | 720p | 720p |
| Output size (downloaded MP4) | 5.4 MB | 4.5 MB | 4.5 MB |
| Status | succeeded | succeeded | succeeded |

**Key operational findings:**

- **Cold-start penalty is ~36 seconds.** The first Fabric call of a batch hits
  a fresh Replicate worker and takes ~161s wall time; subsequent warm calls
  settle at ~125s. For interactive use the default `--max-wait 600` has
  plenty of headroom, but if you're queuing a large batch expect the first
  call to be the slowest.
- **Output duration matches audio duration.** Fabric does not pad or trim —
  a 7s audio input produces a 7s video output.
- **End-to-end submission + poll + download works.** All three runs completed
  with `data_removed: False`, valid MP4 outputs, zero errors. This was the
  first time `video_lipsync.py` was exercised against the real Replicate API
  beyond the validation-layer unit tests that shipped with v3.8.1.

**Cost per prediction** — authoritative, extracted from the Replicate
predictions dashboard at `replicate.com/predictions` on 2026-04-15:

| Run | Output duration | Wall time | Approximate cost | Implied rate |
|---|---|---|---|---|
| Run 1 (cold start) | 8 s | 2m 41.2s | **$1.20** | $0.150/s |
| Run 2 (warm) | 7 s | 2m 3.6s | **$1.05** | $0.150/s |
| Run 3 (warm) | 7 s | 2m 5.4s | **$1.05** | $0.150/s |

**Fabric pricing is linear at ~$0.15 per second of output video.** The
cold-start penalty (~36s extra wall time on the first call of a batch) adds
latency but does NOT increase cost — Replicate bills Fabric on output
duration, not on GPU wall time. The formula is
`cost ≈ $0.15 × output_duration_seconds`, so a 5s clip ≈ $0.75, a 10s clip ≈
$1.50, and the 60s maximum ≈ **$9.00**. Budget accordingly — a 60-second
Fabric lip-sync is not a cheap action.

**Why this isn't in the Replicate API**: `/v1/predictions/<id>` returns
`metrics.predict_time` and `metrics.video_output_duration_seconds` but no
`cost_usd` field. `/v1/models/veed/fabric-1.0` has `run_count` (22,603 as
of 2026-04-15) but no pricing. Replicate's public web model page also has
no pricing. The authoritative sources are the Replicate billing dashboard
and the predictions list view at `replicate.com/predictions` (both web-only,
logged-in). The $0.15/s rate in this section was extracted from the
predictions dashboard's "Approximate cost" column during session 19
verification — the user pasted the dashboard screenshot into the session
as the final evidence.

**Superseded claim**: session 18's first draft of this doc estimated
Fabric at `~$0.30/call` and concluded "Fabric is cheaper than VEO Lite".
Both parts were wrong — the estimate was ~3.5× too low, and Fabric is
actually ~2-3× more expensive per clip than VEO Lite. Fabric is still the
only viable path for custom-voice-to-visible-face, but the cost comparison
is now a premium, not a discount.

**Known follow-up**: `video_lipsync.py` does not currently integrate with
`cost_tracker.py` (which only logs Gemini image-gen spend). With the
$0.15/s formula now authoritative, wiring Fabric into the cost tracker is
straightforward — the output duration is already in the Replicate poll
response (`metrics.video_output_duration_seconds`), so per-prediction cost
can be computed client-side as `$0.15 × output_duration` with no dashboard
lookup required. v3.8.x candidate; would close the budget-tracking loop
for Fabric permanently.

## Deferred to v3.9.x+

- **Auto-pipeline from text → voice → face → lip-sync** in a single command.
  Currently requires 3 separate script invocations.
- **DreamActor M2.0 integration** for full-body character animation (not
  just face). Would require a new script + reference doc; queued for future
  research if a user workflow demands it.
- **Upscaling post-Fabric** via an image-upres model (Real-ESRGAN on
  Replicate) for 1080p talking-head output. Not in scope for v3.8.1.
