# VEO Video Generation Models

> Load this when selecting a model for video generation or when the user
> asks about VEO capabilities, pricing, rate limits, or known limitations.

## Backend Availability (v3.6.0+)

VEO 3.1 is served via two different Google API backends with **different
model coverage**. The plugin supports both, with `--backend auto`
(default) routing each request to the right one.

| Backend | Auth | Plugin support | Available models |
|---|---|---|---|
| **Gemini API** (`generativelanguage.googleapis.com`) | `google_ai_api_key` in `~/.banana/config.json` | ✅ Since v3.0.0 | Standard preview (`veo-3.1-generate-preview`), Fast preview (`veo-3.1-fast-generate-preview`) — text-to-video only |
| **Vertex AI** (`*-aiplatform.googleapis.com`) | `vertex_api_key` (bound to a service account) + `vertex_project_id` + `vertex_location` in `~/.banana/config.json` | ✅ **Since v3.6.0** | All of the above **plus** Lite (`veo-3.1-lite-generate-001`), Legacy 3.0 (`veo-3.0-generate-001`), GA `-001` IDs for Standard/Fast, image-to-video (first-frame, last-frame, reference images), and Scene Extension v2 (`--video-input`) |

**What this means in practice:**

- **Text-to-video on Standard or Fast preview** stays on the Gemini API path. No new credentials needed if you already had the plugin working in v3.4.x.
- **Everything else** (Lite, GA IDs, image-to-video, Scene Extension v2) auto-routes through Vertex AI. Requires Vertex credentials in `~/.banana/config.json` (see "Auth setup" below).
- **`--quality-tier draft`** in `video_sequence.py` maps to Lite via the Vertex backend — **8× cheaper than Standard**.

### Auth setup (3 minutes, one-time)

1. Open https://console.cloud.google.com/ and select (or create) a project with billing enabled and the Vertex AI API enabled.
2. Visit https://console.cloud.google.com/apis/credentials → **Create Credentials** → **API key**.
3. **Restrict the key**: in the key's settings page, **bind it to a service account** that has the `Vertex AI User` (`roles/aiplatform.user`) role on the project. The bound-to-service-account format starts with `AQ.*` and is the only API key format that works with `predictLongRunning`.
4. Add three fields to `~/.banana/config.json` (alongside the existing `google_ai_api_key`):
   ```json
   {
     "vertex_api_key": "AQ.Ab8...",
     "vertex_project_id": "your-gcp-project-id",
     "vertex_location": "us-central1"
   }
   ```
5. Verify with `python3 skills/video/scripts/_vertex_backend.py diagnose` — runs a free Gemini text-gen sanity check against the same auth path.

**Why API key auth works for Vertex AI** (despite many older docs saying it doesn't): bound-to-service-account API keys carry a service account principal as their identity, so they pass Vertex's `roles/aiplatform.user` IAM check. Anonymous API keys do not. This was an undocumented capability when v3.6.0 shipped — confirmed empirically and per Google's own docs convention that omits the "Authorization scopes" section on methods that accept API keys.

### Architectural history

The Gemini API VEO surface used to support image-to-video and `--video-input` in earlier preview cycles, then quietly dropped support for both when the GA `-001` IDs shipped on Vertex AI in March 2026. v3.5.0 was the last release that tried to use the Gemini API path for everything; v3.6.0's Vertex backend is the long-term home for the full feature surface.

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
| **Plugin callable** | ✅ Both backends | ✅ Both backends | ✅ Vertex only (auto-routed since v3.6.0) |
| **GA ID** (Vertex) | `veo-3.1-generate-001` | `veo-3.1-fast-generate-001` | `veo-3.1-lite-generate-001` |
| **Preview ID** (Gemini API) | `veo-3.1-generate-preview` | `veo-3.1-fast-generate-preview` | (no preview ID) |
| **Status** | GA + preview | GA + preview | GA |
| **Duration** | 4, 6, 8 s | 4, 6, 8 s | 4, 6, 8 s |
| **Resolution** | 720p / 1080p / **4K** | 720p / 1080p / 4K | 720p / 1080p |
| **Aspect ratios** | 16:9, 9:16 | 16:9, 9:16 | 16:9, 9:16 |
| **Audio** | 48 kHz stereo, AAC 192 kbps | 48 kHz stereo (lower bitrate) | 48 kHz stereo (lower bitrate) |
| **Price / sec** | **$0.40** | **$0.15** | **$0.05** |
| **Price / 8 s** | $3.20 | $1.20 | $0.40 |
| **Typical latency** | 30–90 s | 15–45 s | 25–40 s |
| **Best for** | Hero shots, brand film, 4K | Social, quick turns | Drafts, iteration, draft-then-final |

**Doc corrections from v3.5.0 → v3.6.0** (real-API testing surfaced these):

- **Lite duration is 4, 6, or 8 s** — same as Standard and Fast. v3.5.0 documented 5–60 s based on unverified docs; the API explicitly rejects 5-second Lite requests with `"supported durations are [8,4,6] for feature text_to_video"`.
- **Aspect ratio is 16:9 or 9:16 only — no 1:1.** v3.5.0 claimed Lite supported 1:1 but the Vertex docs and the SDK enum both list only the two landscape/portrait ratios. The plugin now rejects 1:1 for all tiers.
- **Lite latency is ~25–40 s** (not 10–30 s as v3.5.0 estimated) per real-API smoke tests on us-central1.

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

| Tier | 4 s | 6 s | 7 s (extension) | 8 s |
|---|---|---|---|---|
| Standard | $1.60 | $2.40 | $2.80 | $3.20 |
| Fast | $0.60 | $0.90 | $1.05 | $1.20 |
| Lite | $0.20 | $0.30 | **$0.35** | $0.40 |
| Legacy 3.0 | $0.60 | $0.90 | $1.05 | $1.20 |

**No free tier.** Every API call is billed. Google Cloud's $300 new-user
credit can offset initial costs. The 7-second column applies to Scene
Extension v2 hops (`video_extend.py --method video`) — Vertex AI's
`feature=video_extension` accepts only `durationSeconds=7`.

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
| Text-to-video | ✅ both backends | ✅ both backends | ✅ Vertex | ✅ Vertex |
| Image-to-video (`--first-frame`) | ✅ Vertex | ✅ Vertex | ✅ Vertex | ✅ Vertex |
| First+last frame interpolation | ✅ Vertex (v3.6.1+) | ✅ Vertex (v3.6.1+) | ✅ Vertex (v3.6.1+) | ❌ (not supported by model) |
| Reference images (up to 3) | ✅ Vertex (v3.6.1+) | ✅ Vertex (v3.6.1+) | ❌ (not supported by model) | ❌ |
| Scene Extension v2 (video input) | ✅ Vertex (720p, 7 s) | ✅ Vertex (720p, 7 s) | ✅ Vertex (720p, 7 s) | ✅ Vertex (720p, 7 s) |
| Native audio | ✅ 192 kbps | ✅ (lower) | ✅ (lower) | ✅ |
| Object insertion | planned | planned | planned | — |

**Why image-to-video and Scene Extension v2 are Vertex-only:** the
Gemini API surface (`generativelanguage.googleapis.com`) used to accept
the `inlineData` image and video parts in earlier preview cycles, then
quietly dropped support when the GA `-001` IDs shipped on Vertex AI in
March 2026. v3.6.0's `--backend auto` routes any request that needs
these features through Vertex automatically.

## Scene Extension v2

VEO 3.1 supports extending a clip by passing the previous clip itself
(not just its last frame) as the input, preserving audio continuity
across the seam at 720p. Use `video_generate.py --video-input <clip.mp4>`
or `video_extend.py --method video` (the v3.6.0 default).

**Constraints:**

- `durationSeconds=7` is the only allowed value (`video_extend.py`
  enforces this; `video_generate.py` auto-overrides from the default 8).
- Resolution is forced to 720p.
- Source video is passed as inline base64 (~1-5 MB clips work fine; the
  plugin enforces a 15 MB cap to stay under any reasonable inline limit).
- First call on a fresh GCP project may return a transient "Service
  agents are being provisioned" error that auto-resolves in ~60-90 s.
  `video_generate.py` retries automatically once after a 90 s sleep.

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
- **8-second clip ceiling** for all VEO 3.1 tiers. Longer cuts require
  extension via `video_extend.py` (max 148 s total).
- **Occasional silent-output failures.** A small fraction of generations
  return without audio. Retry with a new seed or a slightly rephrased
  prompt.
- **48-hour retention** on Gemini API download URIs (Vertex AI returns
  inline bytes — no expiry).

## Video Retention

**Gemini API path:** generated video URIs persist on Google's servers
for only **48 hours**. After that, the download URI expires and
re-fetching fails. The plugin's `video_generate.py` downloads the MP4
immediately on successful generation, so runtime is safe, but JSON
manifests that store URIs become stale after 48 hours. The output
manifest includes a `download_expires_at` timestamp so downstream tools
can warn users trying to act on an expired URI.

**Vertex AI path:** the API returns video bytes inline as base64 in the
poll response — there is no URI, no separate download, and no expiry.
Output manifests for Vertex generations omit the `download_expires_at`
field entirely. Long-lived workflows benefit from this automatically;
no GCS bucket setup is required.

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
