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
| `/video sequence plan --script "..." --target Ns [--shot-types ...]` | Break a script into a shot list with semantic shot-type defaults |
| `/video sequence storyboard --plan PATH [--shots 1,3-5]` | Generate start/end frame pairs (optionally a subset) |
| `/video sequence review --plan PATH --storyboard DIR` | Generate REVIEW-SHEET.md — mandatory approval gate in v3.6.3+ |
| `/video sequence generate --storyboard PATH [--skip-review]` | Batch-generate clips from approved frames (review-gated) |
| `/video sequence stitch --clips DIR --output PATH` | Assemble clips into final sequence |
| `/video extend <clip> [--to Ns]` | Extend a clip (+7s per hop, max 148s) |
| `/video stitch <clips...>` | Concatenate arbitrary clips via FFmpeg |
| `/video audio pipeline --video V --text "..." --music-prompt "..." [--music-source lyria\|elevenlabs]` | **v3.7.1+v3.7.2** end-to-end: parallel TTS + music (Lyria default, ElevenLabs alt), mix, swap into video |
| `/video audio narrate --text "..." [--voice ROLE]` | **v3.7.1** generate ElevenLabs TTS narration only |
| `/video audio music --prompt "..." [--source lyria\|elevenlabs] [--negative-prompt "..."]` | **v3.7.2** generate background music — Lyria 2 default ($0.06/clip), ElevenLabs alternative |
| `/video audio mix --narration N --music M` | **v3.7.1** mix existing narration + music with side-chain ducking |
| `/video audio swap --video V --audio A` | **v3.7.1** swap an audio file into a video (lossless video) |
| `/video voice design --description "..."` | **v3.7.1** generate 3 voice previews from a text description |
| `/video voice promote --generated-id ID --name N --role R` | **v3.7.1** save a chosen preview as a permanent custom voice |
| `/video voice list` | **v3.7.1** list saved custom voices from `~/.banana/config.json` |
| `/video cost [estimate]` | Video cost estimation |
| `/video status` | Check VEO API access and FFmpeg availability |
| `/video audio status` | **v3.7.1** check ElevenLabs API key + ffmpeg + custom voices |

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
| Poll timeout | Generation took too long (>300s). Retry once, or try `veo-3.1-lite-generate-001` (Lite, ~25-40 s typical) for faster results. |
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

For sequences longer than 8 seconds: **plan → storyboard → review → generate → stitch**. See `references/video-sequences.md`.

The storyboard stage generates still frame pairs using `/banana generate` for visual approval before committing to video generation. This saves costs ($0.08/frame vs $1.20+/clip). The **review** stage (v3.6.2) produces a `REVIEW-SHEET.md` that interleaves each shot's frames, VEO prompt, cost estimate, and parameters into a single markdown file you can open in Quick Look. v3.6.3 promotes review to a **mandatory gate**: `generate` refuses to run unless `REVIEW-SHEET.md` exists and its embedded frame hashes match the current storyboard. Pass `--skip-review` to bypass for CI/automation.

**Shot-type semantic defaults** (v3.6.3): pass `--shot-types establishing,medium,closeup,product` to `plan` to pre-fill duration, camera hints, and `use_veo_interpolation` defaults from a built-in 8-type table. Useful for standard commercial structures. Claude can override any field in plan.json after generation.

**Partial iteration:** if one frame needs a redo but the rest are approved, use `video_sequence.py storyboard --shots 3` (or `--shots 1,3-5`) to regenerate only a subset. Shots with `use_veo_interpolation: true` in plan.json skip the end frame entirely — useful for establishing shots that cut away to unrelated material.

## /video extend

Extend a clip by chaining: extract last frame, use as reference for next clip. +7s per hop, max 148s total.
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_extend.py --input clip.mp4 --target-duration 30
```

## Model Routing

| Scenario | Model | Duration | Backend | When |
|----------|-------|----------|---------|------|
| Draft / motion check | `veo-3.1-lite-generate-001` | 4-8s | Vertex (auto) | **First pass** for sequences ($0.05/sec) |
| Quick turnaround social | `veo-3.1-fast-generate-preview` | 4s | Gemini API | TikTok, Reels, Shorts ($0.15/sec) |
| Standard production | `veo-3.1-generate-preview` | 8s | Gemini API | Default single-clip ($0.40/sec) |
| Hero / brand work | `veo-3.1-generate-preview` + 4K | 8s | Gemini API | Premium campaign (same $0.40/sec) |
| Image-to-video / Scene Ext v2 | any tier | 4-8s (or 7s for ext) | Vertex (auto) | first-frame, --video-input |
| Legacy / reproduction | `veo-3.0-generate-001` | 8s | Vertex (auto) | Match existing VEO 3.0 style |

Default model: `veo-3.1-generate-preview`. Default backend: `auto`
(routes Vertex-only features through Vertex automatically; keeps
text-to-video on Gemini API for v3.4.x compat). **For sequences, always
draft at Lite first** — see the draft-then-final workflow in
`references/video-sequences.md`.

**Vertex AI setup** (3 minutes, one-time): add `vertex_api_key`,
`vertex_project_id`, and `vertex_location` to `~/.banana/config.json`.
See `references/veo-models.md` → Backend Availability for the bound-
to-service-account API key creation steps.

## Audio Quick Guide

VEO 3.1 generates synchronized audio. Include in every prompt:
- **Dialogue:** `A man says, "Welcome to our studio."` (in quotes)
- **SFX:** `SFX: glass shattering, metallic echo` (prefix "SFX:")
- **Ambient:** `Quiet hum of machinery, distant traffic` (natural description)
- **Music:** `Soft piano melody in the background` (describe style)
- **Narration (no visible speaker):** `A narrator says, "..."` — works ONLY when no human is visible in frame; if a person is visible, VEO will lip-sync them to the line regardless of prompt wording (verified spike 1, 2026-04-14)
- **Narration line length:** for an 8s clip, target ~16 words at narrator pace. Shorter lines trigger a known failure mode where VEO sings the line to fill time. See `references/video-audio.md` F2.

See `references/video-audio.md` for VEO-native audio prompting and the 12 empirical findings from the strategic reset spikes.

## v3.7.1+v3.7.2 Audio Replacement Pipeline (for multi-clip sequences)

**When to use:** the user is producing a multi-clip stitched sequence and (a) wants narration over visible characters, OR (b) wants a continuous music bed without seams at clip boundaries, OR (c) wants a custom-designed branded narrator voice instead of VEO's emergent voice, OR (d) wants higher-fidelity music than VEO's emergent bed (Lyria 2 is 48kHz/192kbps stereo).

**What it does:** strips the VEO video's audio entirely and replaces it with continuous ElevenLabs TTS narration + background music (**Google Lyria 2 by default** as of v3.7.2, ElevenLabs Music as the alternative) + FFmpeg ducked mix. The TTS and music API calls run in parallel for ~12s total latency.

**Music source choice (v3.7.2):** Lyria is the default after winning the 5-way bake-off in spike 4 (Lyria > ElevenLabs > MusicGen > MiniMax > Stable Audio per user listening verdict). Use `--music-source elevenlabs` to opt into the alternative when you need custom durations >32.768s, prefer ElevenLabs's character for a specific genre, or want subscription-billed cost on the Creator tier. See `references/audio-pipeline.md` for the full decision matrix.

**Canonical command:**

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/audio_pipeline.py pipeline \
  --video stitched-sequence.mp4 \
  --text "Each year... the seasons change across this valley, painting the forest in red and gold. [exhales] The river runs COLD here..." \
  --music-prompt "Cinematic nature documentary background score, slow contemplative warm orchestral strings with soft piano, instrumental only, no vocals, around 70 BPM" \
  --voice narrator \
  --out final.mp4
```

**Routing rules (Creative Director discipline):**

- **Single-shot social reel with no visible character** → use VEO native narration (`A narrator says, "..."`). Cheaper, simpler, fewer dependencies.
- **Single-shot reel WITH visible character but you want narration** → use the v3.7.1 pipeline. VEO will otherwise lip-sync the visible character to the narration line.
- **Multi-shot sequence (2+ clips) with narration** → use the v3.7.1 pipeline. VEO's per-clip music seams will otherwise be audible at every cut.
- **Multi-shot sequence without narration** → VEO native ambient + SFX is fine. Music seams are still present but less obvious without speech to draw attention to them.

**Voice selection:**

- Default: `--voice narrator` reads the saved `custom_voices.narrator` from `~/.banana/config.json`.
- To use a different role: `--voice character_a` (reads `custom_voices.character_a`).
- To use a literal ElevenLabs voice ID: `--voice 21m00Tcm4TlvDq8ikWAM` (any non-role string is treated as a literal ID).
- To create a new custom voice: `voice-design` then `voice-promote`. See `references/audio-pipeline.md`.

**Music prompt restriction (TOS guardrail):** Eleven Music blocks prompts that name copyrighted creators or brands (e.g. "Annie Leibovitz", "BBC Earth"). Use generic descriptors only — genre, mood, instrumentation, tempo. This is music-API-specific — image generation prompts welcome creator names.

**Prompt engineering for ElevenLabs TTS narration:**

- Use `eleven_v3` model (default) for expressiveness
- Insert audio tags like `[exhales]`, `[reverent]`, `[contemplative]` for emotional beats — tag set is open-ended, not whitelisted
- Use ellipses (`...`) for contemplative pauses
- Use selective CAPS for emphasis on key words
- Match line length to the *voice's* WPM (different voices have different pacing — see `references/audio-pipeline.md` line-length calibration section)

See `references/audio-pipeline.md` for the full architecture, FFmpeg parameter rationale, voice design flow, custom voice schema, and prompt engineering for both TTS and music.

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
- `references/video-audio.md` -- VEO native dialogue, SFX, ambient audio prompting + 12 empirical findings from spike sessions
- `references/audio-pipeline.md` -- v3.7.1 audio replacement pipeline (ElevenLabs TTS + music + ducked mix), voice design, custom voice schema
- `references/image-to-video.md` -- Animate-a-still pipeline, reference image handling
