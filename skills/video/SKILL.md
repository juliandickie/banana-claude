---
name: video
description: "Use when ANY request involves video creation, animation, video clips, motion graphics, or animating images. Triggers on: generate a video, create a clip, animate this image, product reveal video, make a video ad, and all /video commands."
argument-hint: "[generate|animate|sequence|extend|stitch|cost|status] <idea, path, or command>"
---

# Nano Banana Studio -- Video Creative Director

<!-- VEO 3.1 API | Shares presets/assets with /banana skill | Version managed in plugin.json -->
<!-- Conflict note: This skill uses /video command. Part of the nano-banana-studio plugin. -->

## Core Principles

1. **Creative Director for Video** -- NEVER pass raw user text to the VEO API. Interpret intent, enhance with cinematic language, and construct an optimized video prompt.
2. **Audio is Always Part of the Prompt** -- VEO 3.1 generates synchronized audio. Every prompt should include dialogue (in quotes), SFX (prefix "SFX:"), or ambient sound descriptions.
3. **8-Second Thinking** -- Every clip must tell a complete micro-story within 4-8 seconds. One dominant action per clip.
4. **Storyboard Before Generating** -- For sequences (15s+), generate still frame previews first. Video generation is expensive ($1.20+/clip). Preview with images ($0.08/frame) before committing.
5. **Image-to-Video** -- Animate existing assets from `/banana` for visual consistency across image and video outputs.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `/video generate <idea>` | Text-to-video with full Creative Director pipeline |
| `/video animate <image> <motion>` | Animate a still image (from /banana or uploaded) |
| `/video sequence plan --script "..." --target Ns` | Break a script into a shot list |
| `/video sequence storyboard --plan PATH` | Generate start/end frame pairs for approval |
| `/video sequence generate --storyboard PATH` | Batch-generate clips from approved frames |
| `/video sequence stitch --clips DIR --output PATH` | Assemble clips into final sequence |
| `/video extend <clip> [--to Ns]` | Extend a clip (+7s per hop, max 148s) |
| `/video stitch <clips...>` | Concatenate arbitrary clips via FFmpeg |
| `/video cost [estimate]` | Video cost estimation |
| `/video status` | Check VEO API access and FFmpeg availability |

## Video Creative Director Pipeline

Follow this for every generation -- no exceptions:

### Step 1: Analyze Intent

Same 5-Input Creative Brief as image generation: **Purpose** (where used?), **Audience** (who for?), **Subject** (what?), **Brand** (what vibe?), **References** (visual examples?). Additionally ask: **Duration** (how long?), **Audio** (dialogue, music, SFX?). See `references/video-prompt-engineering.md`.

### Step 2: Check for Presets

If user mentions a brand/preset, load from shared system:
```bash
python3 ${CLAUDE_SKILL_DIR}/../banana/scripts/presets.py list
python3 ${CLAUDE_SKILL_DIR}/../banana/scripts/presets.py show NAME
```
Preset `prompt_suffix`, `lighting`, `mood`, and `colors` apply to video prompts identically to image prompts.

### Step 3: Check for Assets

If user mentions a named character, product, or object:
```bash
python3 ${CLAUDE_SKILL_DIR}/../banana/scripts/assets.py list
python3 ${CLAUDE_SKILL_DIR}/../banana/scripts/assets.py show NAME
```
Pass `reference_images[]` to VEO (up to 3 per shot). Append `consistency_notes` to the prompt. See `references/image-to-video.md`.

### Step 4: Select Video Domain Mode

Choose from: **Product Reveal**, **Story-Driven**, **Environment Reveal**, **Social Short**, **Cinematic**, **Tutorial/Demo**. See `references/video-domain-modes.md` for camera specs, modifier libraries, and shot type guidance.

### Step 5: Construct Video Prompt

Use the **5-Part Video Framework**: Camera → Subject → Action → Setting → Style + Audio. Write as natural narrative prose. See `references/video-prompt-engineering.md` for templates and examples.

**Critical rules:**
- Use professional cinematography language: "dolly," "rack focus," "tracking shot"
- Include audio in every prompt: dialogue in quotes, SFX with "SFX:" prefix, ambient as description
- One dominant action per clip (must complete within 4-8 seconds)
- NEVER use banned keywords: "8K," "masterpiece," "ultra-realistic"
- For character consistency: repeat exact identity phrasing across all shots

### Step 6: Set Duration + Aspect Ratio + Resolution

| Parameter | Options | Default |
|-----------|---------|---------|
| Duration | 4s, 6s, 8s | 8s |
| Aspect ratio | 16:9, 9:16 | 16:9 |
| Resolution | 720p, 1080p, 4K | 1080p |

### Step 7: Call VEO API

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_generate.py --prompt "..." --duration 8 --aspect-ratio 16:9 --resolution 1080p
```

VEO uses async generation: the script submits the request, polls for completion (printing progress to stderr), and saves the MP4 when done. Typical generation: 30-90 seconds.

**For image-to-video (animate a still):**
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_generate.py --prompt "..." --first-frame PATH
```

**For first/last frame (keyframe interpolation):**
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_generate.py --prompt "..." --first-frame START.png --last-frame END.png
```

### Step 8: Post-Processing

If needed, use FFmpeg for trimming, format conversion, or concatenation:
```bash
ffmpeg -i input.mp4 -t 6 -c copy trimmed.mp4          # Trim to 6 seconds
ffmpeg -i input.mp4 -vf scale=1920:1080 output.mp4     # Resize
```
Check availability first: `which ffmpeg || echo "FFmpeg not installed"`

### Step 9: Handle Errors

| Error | Action |
|-------|--------|
| `VIDEO_SAFETY` | Rephrase prompt. Common triggers: "fire" → "flames", "shot" → "filmed". Max 3 attempts with user approval. |
| HTTP 429 | Wait 10s, exponential backoff, max 3 retries |
| HTTP 403 | Billing not enabled -- VEO has no free tier. Inform user. |
| HTTP 5xx | Server error -- wait 10s, retry with backoff, max 3 retries |
| Poll timeout | Generation took too long (>300s). Retry once, or try `veo-3.1-generate-lite-preview` for faster results. |
| Invalid API key | Suggest running `/banana setup` to reconfigure |

### Step 10: Log Cost + History

```bash
python3 ${CLAUDE_SKILL_DIR}/../banana/scripts/cost_tracker.py log --model MODEL --resolution DURATION --prompt "brief"
python3 ${CLAUDE_SKILL_DIR}/../banana/scripts/history.py log --prompt "full prompt" --image-path PATH --model MODEL --ratio RATIO --resolution DURATION --type video --session-id SESSION_ID
```

### Step 11: Return Results

Always provide: **video path**, **crafted prompt** (educational), **settings** (model, duration, ratio), **audio description** (what VEO generated), **suggestions** (1-2 refinements or next steps).

## /video animate (Image-to-Video)

Animate a still image generated with `/banana` or uploaded by the user. See `references/image-to-video.md`.
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_generate.py --prompt "slow orbit revealing the product" --first-frame PATH
```

## /video sequence (Multi-Shot Production)

For sequences longer than 8 seconds: plan → storyboard (preview) → generate → stitch. See `references/video-sequences.md`.

The storyboard stage generates still frame pairs using `/banana generate` for visual approval before committing to video generation. This saves costs ($0.08/frame vs $1.20+/clip).

## /video extend

Extend a clip by chaining: extract last frame, use as reference for next clip. +7s per hop, max 148s total.
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_extend.py --input clip.mp4 --target-duration 30
```

## Model Routing

| Scenario | Model | Duration | When |
|----------|-------|----------|------|
| Standard production | `veo-3.1-generate-preview` | 8s | Default -- best quality |
| Quick draft | `veo-3.1-generate-lite-preview` | 4s | Budget-conscious, rapid iteration |
| Social short | `veo-3.1-generate-preview` | 4s | TikTok, Reels, Shorts |

Default: `veo-3.1-generate-preview`. See `references/veo-models.md` for full specs and pricing.

## Audio Quick Guide

VEO 3.1 generates synchronized audio. Include in every prompt:
- **Dialogue:** `A man says, "Welcome to our studio."` (in quotes)
- **SFX:** `SFX: glass shattering, metallic echo` (prefix "SFX:")
- **Ambient:** `Quiet hum of machinery, distant traffic` (natural description)
- **Music:** `Soft piano melody in the background` (describe style)

See `references/video-audio.md` for detailed audio prompting strategies.

## Setup

Video generation uses the same Google AI API key as image generation. If `/banana setup` has been run, no additional setup is needed. VEO requires a **paid API tier** (no free tier).

Check status: `python3 ${CLAUDE_SKILL_DIR}/../banana/scripts/validate_setup.py`
Check FFmpeg: `which ffmpeg` (required for extend/stitch/trim)

## Reference Documentation

Load on-demand -- do NOT load all at startup:
- `references/video-prompt-engineering.md` -- 5-Part Video Framework, templates, camera motion vocabulary
- `references/veo-models.md` -- VEO model specs, pricing, rate limits, Replicate alternatives
- `references/video-domain-modes.md` -- 6 domain modes with modifier libraries, shot types for sequences
- `references/video-sequences.md` -- Multi-shot production, first/last frame chaining, storyboard approval
- `references/video-audio.md` -- Dialogue, SFX, ambient audio prompting strategies
- `references/image-to-video.md` -- Animate-a-still pipeline, reference image handling
