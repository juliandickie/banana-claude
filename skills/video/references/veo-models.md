# VEO Video Generation Models

> Load this when selecting a model for video generation or when the user
> asks about VEO capabilities, pricing, rate limits, or known limitations.

## ⚠️ Backend Availability (as of 2026-04-10)

VEO 3.1 is served via two different Google API backends with **different
model coverage**:

| Backend | Auth | Plugin support | Available models |
|---|---|---|---|
| **Gemini API** (`generativelanguage.googleapis.com`) | API key | ✅ Shipped since v3.0.0 | Standard preview (`veo-3.1-generate-preview`), Fast preview (`veo-3.1-fast-generate-preview`) |
| **Vertex AI** (`*-aiplatform.googleapis.com`) | OAuth / service account | ❌ **Not yet** — tracked as v3.6.0 ROADMAP item | All of the above **plus** Lite (`veo-3.1-lite-generate-001`), Legacy 3.0 (`veo-3.0-generate-001`), GA `-001` IDs for Standard/Fast, and Scene Extension v2 (`--video-input`) |

**What this means in practice:**

- **Standard and Fast preview IDs work today** through the plugin's existing API key path.
- **Lite, Legacy, GA `-001` IDs, and `--video-input`** are documented here for completeness and will be callable through the plugin **once the Vertex AI backend ships in v3.6.0**. Requesting them today returns a clear error pointing at this limitation.
- **`--quality-tier draft` currently maps to Fast** (`$0.15/sec`, 2.7× cheaper than Standard) instead of Lite (`$0.05/sec`, 8×). The draft-then-final workflow still pays off; the savings are just 2.7× instead of 8× until Vertex support lands.

This was discovered during v3.5.0 real-API verification: the Gemini API
returned HTTP 404 for every `-001` ID and rejected `--video-input` with
"inlineData isn't supported by this model." Google's documentation
describes the unified VEO 3.1 surface, but the Gemini API surface is a
subset.

## Release Timeline

| Date | Release |
|---|---|
| July 2025 | VEO 3.0 general availability |
| October 2025 | VEO 3.1 Standard + Fast preview |
| January 2026 | 4K output (AI-upscaled from 1080p base), Scene Extension v2 |
| March 2026 | VEO 3.1 Lite general availability, GA IDs for Standard + Fast |
| April 2026 | Current reference date for this document |

## Tier Comparison (VEO 3.1)

VEO 3.1 ships in three tiers plus a legacy VEO 3.0 option. Both the
preview IDs and the official GA (`-001`) IDs resolve correctly in the
plugin; use GA IDs for new work.

| Property | Standard | Fast | Lite |
|---|---|---|---|
| **Plugin callable today** | ✅ (preview ID) | ✅ (preview ID) | ❌ **Vertex AI only** |
| **GA ID** | `veo-3.1-generate-001` (Vertex) | `veo-3.1-fast-generate-001` (Vertex) | `veo-3.1-lite-generate-001` (Vertex) |
| **Preview ID** | `veo-3.1-generate-preview` ✅ | `veo-3.1-fast-generate-preview` ✅ | (no preview ID) |
| **Status** | GA + preview | GA + preview | GA |
| **Duration** | 4, 6, 8 s | 4, 6, 8 s | **5–60 s** (extended range) |
| **Resolution** | 720p / 1080p / **4K** | 720p / 1080p / 4K | 720p / 1080p |
| **Aspect ratios** | 16:9, 9:16 | 16:9, 9:16 | 16:9, 9:16, **1:1** |
| **Audio** | 48 kHz stereo, AAC 192 kbps | 48 kHz stereo (lower bitrate) | 48 kHz stereo (lower bitrate) |
| **Price / sec** | **$0.40** | **$0.15** | **$0.05** (720p) |
| **Price / 8 s** | $3.20 | $1.20 | $0.40 |
| **Typical latency** | 30–90 s | 15–45 s | 10–30 s |
| **Best for** | Hero shots, brand film, 4K | Social, quick turns | Drafts, iteration, long cuts |

### Legacy: VEO 3.0

| Property | Value |
|---|---|
| **Model ID** | `veo-3.0-generate-001` |
| **Status** | GA, still available |
| **Duration** | 4, 6, 8 s |
| **Resolution** | 720p, 1080p (no 4K) |
| **Aspect ratios** | 16:9, 9:16 |
| **Pricing** | Parity with Fast: $0.15/sec, $1.20 per 8 s (doc does not specify separately) |
| **Use** | Reproduction of existing VEO 3.0 style in legacy workflows |

## 4K is AI-Upscaled, Not Native

VEO's 4K output (3840×2160) is produced by AI-powered upscaling from a
1080p base generation, not native 4K rendering. The upscale step is
included in the base price, which is why 4K costs the same as 1080p for
the Standard tier. This is also why 4K is only offered on Standard: the
upscale quality is tuned for the flagship tier and not ported down to
Lite/Fast.

## Pricing Table

| Tier | 4 s | 6 s | 8 s | Variable (Lite only) |
|---|---|---|---|---|
| Standard | $1.60 | $2.40 | $3.20 | — |
| Fast | $0.60 | $0.90 | $1.20 | — |
| Lite | $0.20 | $0.30 | $0.40 | $0.05/sec up to 60 s |
| Legacy 3.0 | $0.60 | $0.90 | $1.20 | — |

**No free tier.** Every API call is billed. Google Cloud's $300 new-user
credit can offset initial costs. Lite 1080p pricing is not explicitly
documented; the $0.05/sec rate is the attested 720p rate.

## Cost Comparison: Image vs Video

| Asset | Typical Cost |
|---|---|
| Single image (2K) | $0.078 |
| Single image (4K) | $0.156 |
| Single clip (8 s, Lite 720p) | **$0.40** |
| Single clip (8 s, Fast 1080p) | $1.20 |
| Single clip (8 s, Standard 1080p) | $3.20 |
| Single clip (8 s, Standard 4K) | $3.20 (same as 1080p) |
| Storyboard frame pair (2× 2K) | $0.156 |
| 30 s sequence, 4 clips @ Lite draft | **$1.60** |
| 30 s sequence, 4 clips @ Fast | $4.80 |
| 30 s sequence, 4 clips @ Standard | $12.80 |
| 30 s sequence with storyboard (Standard) | $13.42 |

See `video-sequences.md` for the draft-then-final workflow that uses
Lite as a $1.60 review pass before committing to the final render.

## Capability Matrix

| Feature | Standard | Fast | Lite | Legacy 3.0 |
|---|---|---|---|---|
| 4K output | ✅ (AI upscale) | ✅ (AI upscale) | ❌ | ❌ |
| Reference images (up to 3) | ✅ | ✅ | ✅ | ✅ |
| First/last frame keyframing | ✅ | ✅ | ✅ | ✅ |
| Scene Extension v2 (video input) | ✅ (720p) | ✅ (720p) | ✅ (720p) | ✅ (720p) |
| Native audio | ✅ 192 kbps | ✅ (lower) | ✅ (lower) | ✅ |
| Square 1:1 aspect | ❌ | ❌ | ✅ | ❌ |
| 5–60 s variable duration | ❌ | ❌ | ✅ | ❌ |
| Object insertion (future) | planned | planned | planned | — |

## Scene Extension v2 — ⚠️ Vertex AI only

VEO 3.1 supports extending a clip by passing the previous clip itself
(not just its last frame) as the input, preserving audio continuity
across the seam (capped at 720p). **This feature is Vertex-AI-only as
of 2026-04-10** — the Gemini API rejects the video inlineData part.
`video_generate.py --video-input <clip.mp4>` returns a clear error
pointing at this limitation; use `video_extend.py --method keyframe`
(the legacy last-frame path) for extension today. Vertex AI support is
tracked as a v3.6.0 roadmap item.

## Known Limitations

- **Character drift.** VEO treats every prompt as a fresh generation with
  no persistent character memory. Faces, clothing, and hairstyle can
  subtly or dramatically shift between clips. Reference images and
  verbatim character descriptions mitigate this but do not fully solve
  it. Competitors Kling 2.6 and Seedance 2.0 currently handle multi-shot
  character consistency better. See the scene-bible-anchors tip in
  `video-prompt-engineering.md`.
- **Text rendering is unreliable.** Signs, shirts, posters, storefronts,
  and UI elements render as plausible-looking gibberish. Never rely on
  the model for readable text — describe the area as "blank" or "out of
  frame" and composite text in post-production.
- **8-second clip ceiling** (Standard/Fast). Longer cuts require
  extension or the Lite tier's 5–60 s range.
- **Occasional silent-output failures.** A small fraction of generations
  return without audio. Retry with a new seed or a slightly rephrased
  prompt.
- **48-hour retention** on the source download URI (see below).

## Video Retention

Generated video URIs persist on Google's servers for only **48 hours**.
After that, the download URI expires and re-fetching fails. The plugin's
`video_generate.py` downloads the MP4 immediately on successful
generation, so runtime is safe, but **JSON manifests that store URIs
become stale after 48 hours.** The output manifest now includes a
`download_expires_at` timestamp so downstream tools can warn users
trying to act on an expired URI.

For long-lived workflows, prefer the Vertex AI `output_gcs_uri` path
that writes directly to Cloud Storage (not yet wrapped by the plugin as
of v3.5.0 — tracked in ROADMAP).

## Rate Limits

| Limit | Value |
|---|---|
| Requests per minute (GA) | 50 RPM |
| Requests per minute (preview) | 10 RPM |
| Concurrent operations per project | 10 |
| Videos per request (`number_of_videos`) | 1–4 (plugin hardcodes 1) |

The plugin's single-clip-at-a-time pattern is well within these limits.
`--num-videos` batching is deferred to v3.6.0 (see ROADMAP).

## Regional Availability

**Image-to-video** (first-frame, last-frame, reference images, video
input) is restricted in the EEA, Switzerland, and the UK. In those
regions, `personGeneration` defaults to `allow_adult` and certain
reference-image paths are disabled at the API layer. Text-to-video is
available everywhere.

The plugin does not set `personGeneration` explicitly, which is correct
for pure text-to-video use cases.

## Input Token Limit

VEO 3.1 accepts prompts up to **1,024 tokens, English only**. The
plugin's `video_generate.py` applies a char-based heuristic (~4
chars/token): warns at 3,800 characters (~950 tokens) and hard-rejects
at 4,500 characters (~1,125 tokens).

For longer shot plans, use `video_sequence.py` to split the script into
multiple ≤8 s shots, or use VEO's timestamp-prompting syntax inside a
single clip (see `video-prompt-engineering.md`) to pack multiple
micro-shots into one 8 s generation.

## Access Requirements

| Path | Requirement |
|---|---|
| Google AI Studio (default) | Google AI Ultra or Pro subscription, or paid API key |
| Vertex AI (Cloud) | Google Cloud project with billing enabled |
| Free tier | **None for VEO.** Every call is billed. |

## Competitive Context

VEO 3.1 currently leads the Text-to-Video Arena at Elo 1381, ahead of
Sora, Runway Gen-4, Kling, Pika, and Hailuo for general-purpose
prompting. Its core strengths are native synchronized audio,
high-fidelity physics, and prompt adherence on complex camera work.
Its weaknesses (character drift, text rendering) are exactly where Kling
and Seedance currently do better, so for multi-shot character pieces
consider routing some shots through Replicate backends in a future
plugin release.

## API Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:predictLongRunning?key={api_key}
```

Uses the same Google AI API key as Gemini image generation. Async
pattern: POST → poll the returned operation name until `done: true`,
then download the video URI.
