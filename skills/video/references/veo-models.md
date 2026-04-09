# VEO Video Generation Models

> Load this when selecting a model for video generation or when the user
> asks about VEO capabilities, pricing, or rate limits.

## Available Models

### veo-3.1-generate-preview (DEFAULT)

| Property | Value |
|----------|-------|
| **Model ID** | `veo-3.1-generate-preview` |
| **Status** | Preview -- **Active, recommended default** |
| **Speed** | Standard (~30-90 seconds generation) |
| **Duration** | 4, 6, or 8 seconds per clip |
| **Resolution** | 720p, 1080p, 4K at 24fps |
| **Aspect Ratios** | 16:9, 9:16 |
| **Audio** | Native synchronized (dialogue, SFX, ambient) |
| **Reference Images** | Up to 3 per shot |
| **First/Last Frame** | Yes -- keyframe interpolation between two images |
| **Rate Limits** | 10 RPM (preview), 50 RPM (production) |
| **Pricing** | $0.15/sec standard ($1.20 per 8s clip) |
| **Best For** | All standard production -- ads, brand films, product reveals |

### veo-3.1-generate-lite-preview

| Property | Value |
|----------|-------|
| **Model ID** | `veo-3.1-generate-lite-preview` |
| **Status** | Preview -- **Active** |
| **Speed** | Faster (~15-45 seconds generation) |
| **Duration** | 4, 6, or 8 seconds per clip |
| **Resolution** | 720p, 1080p |
| **Pricing** | ~$0.075/sec (~$0.60 per 8s clip) |
| **Best For** | Drafts, rapid iteration, budget-conscious workflows |

## Video Extension

VEO supports extending clips by chaining:
- Each hop adds ~7 seconds
- Maximum: 20 hops = 148 seconds total
- Uses last frame of current clip as reference for next
- Quality degrades after 5-6 extensions

## Pricing Table

| Model | 4s | 6s | 8s |
|-------|-----|-----|-----|
| veo-3.1-generate-preview | $0.60 | $0.90 | $1.20 |
| veo-3.1-generate-lite-preview | $0.30 | $0.45 | $0.60 |

**No free tier.** Every API call is billed. Google Cloud's $300 new-user credit can offset initial costs.

## Cost Comparison: Image vs Video

| Asset | Typical Cost |
|-------|-------------|
| Single image (2K) | $0.078 |
| Single image (4K) | $0.156 |
| Single video clip (8s, 1080p) | $1.20 |
| Storyboard frame pair (2 images) | $0.156 |
| 30-second sequence (4 clips) | $4.80 |
| 30-second sequence with storyboard | $5.42 (storyboard: $0.62 + clips: $4.80) |

## Replicate Video Models (Future)

For v3.5+, Replicate provides alternative backends:

| Model | Cost/8s | Strengths |
|-------|---------|-----------|
| Kling 3.0 | ~$0.50 | 15s clips, character consistency |
| Hailuo 2.3 | ~$0.40 | Realistic humans |
| Wan 2.5 | ~$0.05 | Budget prototyping |
| PixVerse v5 | ~$0.30 | Anime, stylized content |

Currently VEO-only. Replicate routing planned for future release.

## API Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:predictLongRunning?key={api_key}
```

Uses same Google AI API key as Gemini image generation. Async pattern: POST → poll GET until done.
