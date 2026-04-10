# Video Sequence Production Reference

> Load this when the user wants to create a multi-shot video sequence
> (15s, 30s, 60s+) or runs `/video sequence`.

## Overview

VEO generates max 8 seconds per clip. Longer productions require a **shot list** approach: break the script into individual shots, generate storyboard frame pairs for approval, then batch-generate video clips and stitch them together.

This Gemini + VEO workflow (Gemini for still storyboard frames → VEO for
clip interpolation) is Google's officially recommended pattern for
multi-shot production, not just our opinion. It both lets you catch
composition problems at image cost before committing to video cost, and
locks in per-shot continuity via first/last frame keyframing.

## Draft-then-Final Workflow (v3.5.0+)

```
Plan → Storyboard → Generate (draft) → Review → Generate (final) → Stitch
```

With two VEO tiers available on the Gemini API today (Fast and Standard),
the cheapest validated path is to run the whole sequence at **Fast draft**
quality first, review the motion and continuity, then re-run the approved
shots at **Standard** for delivery.

```bash
# 1. First pass: draft at Fast ($0.15/sec, 2.7x cheaper than Standard)
python3 ${CLAUDE_SKILL_DIR}/scripts/video_sequence.py generate \
    --storyboard ~/storyboard --quality-tier draft

# 2. Review the MP4s. Approve, tweak prompts, or regenerate.

# 3. Final pass: Standard for delivery
python3 ${CLAUDE_SKILL_DIR}/scripts/video_sequence.py generate \
    --storyboard ~/storyboard --quality-tier standard
```

> **Note on `--quality-tier draft`:** Until the Vertex AI backend ships
> in v3.6.0, `draft` maps to **Fast** (`$0.15/sec`) rather than Lite
> (`$0.05/sec`). Lite and Scene Extension v2 are currently Vertex-AI-only
> and return a clear error if requested. See
> `references/veo-models.md` → Backend Availability for details.

### Cost Comparison (4 shots × 8 s, 30-second sequence, Gemini API today)

| Mode | Draft pass | Final pass | Total |
|---|---|---|---|
| Blind at Standard | — | $12.80 | $12.80 |
| Blind at Fast | — | $4.80 | $4.80 |
| **Draft (Fast) + Standard final** | **$4.80** | **$12.80** | **$17.60** |
| Draft (Fast) only, ship at Fast | $4.80 | — | $4.80 |

Once Vertex AI lands in v3.6.0 and Lite becomes reachable, a Lite draft
drops the first column to $1.60:

| Mode (v3.6.0+ with Vertex AI / Lite) | Draft pass | Final pass | Total |
|---|---|---|---|
| Lite draft + Fast final | $1.60 | $4.80 | **$6.40** |
| Lite draft + Standard final | $1.60 | $12.80 | **$14.40** |

Draft-then-final is only "more expensive" on paper — in practice, blind
generation at Standard typically needs 1–2 regenerations per shot because
the user cannot preview motion before committing. One regeneration of a
single 8 s Standard shot ($3.20) already exceeds the cost of draft-pass
protection in the Vertex-enabled table above. **Draft-then-final pays
for itself the first time it prevents a regeneration on any shot at
Standard tier.**

## Timestamp Prompting: Pack Multiple Shots per Clip

VEO 3.1 supports a timestamp syntax within a single prompt that directs
multi-shot sequences inside one 8-second generation. A 30-second sequence
that would otherwise need 4 clips can sometimes be compressed to 2
clips with 4 sub-shots each, cutting VEO cost by ~50%. See the
timestamp-prompting section in `video-prompt-engineering.md` for syntax
and caveats.

## Character Drift Mitigation

VEO treats each prompt as a fresh generation with no persistent
character memory. Between clips, faces, clothing, and hairstyle can
subtly or dramatically shift. The consistency rules below (identity
lock, wardrobe lock, reference images) are **mitigations, not
solutions** — see the Known Limitations section of `veo-models.md`.

## The 4-Stage Pipeline

### Stage 1: Shot List (Free)

Claude breaks the user's script/concept into individual shots:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_sequence.py plan --script "30-second product launch ad" --target 30
```

Each shot specifies: number, duration, camera, subject, action, setting, audio, consistency anchors, and prompts for start/end frame generation.

### Stage 2: Storyboard (Cheap — image cost only)

Generate start/end frame image pairs for visual approval:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_sequence.py storyboard --plan shot-list.json
```

Uses `/banana`'s `generate.py` (cross-skill) to produce still frames at ~$0.08 each. User reviews the visual storyboard and approves or requests changes before committing to video.

**Cost:** N shots x 2 frames x $0.078 = ~$0.80 for 5 shots

### Stage 3: Video Generation (Expensive — VEO cost)

Generate video clips from approved storyboard frames:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_sequence.py generate --storyboard ~/storyboard/
```

Each shot uses its start frame as `--first-frame` and end frame as `--last-frame` for VEO, ensuring frame-perfect continuity between shots.

**Cost:** N shots x $1.20 = ~$6.00 for 5 shots

### Stage 4: Assembly

Concatenate clips into final sequence:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_sequence.py stitch --clips ~/clips/ --output final.mp4
```

## First/Last Frame Chaining

The key to seamless sequences: the end frame of shot N becomes the start frame of shot N+1.

```
Shot 1: start_A → (VEO) → clip ending at frame B
Shot 2: frame B → (VEO) → clip ending at frame C
Shot 3: frame C → (VEO) → clip ending at frame D
```

The storyboard stage generates these frame pairs using Gemini image generation (cheap), then the video stage interpolates motion between them (expensive but guided).

## Target Durations

| Target | Shots | Structure | Est. Cost |
|--------|-------|-----------|-----------|
| **15s** | 2-3 | Establish → Action → Close | $3-5 |
| **30s** | 4-5 | Establish → Problem → Solution → Product → CTA | $6-9 |
| **60s** | 8-10 | Full narrative arc with B-roll | $12-16 |
| **90s** | 12-15 | Tutorial with cutaways | $18-24 |

Costs include storyboard frames + video clips. Actual cost depends on resolution and model tier.

## Consistency Rules

1. **Identity lock** — Repeat character descriptions verbatim in every shot prompt
2. **Wardrobe lock** — Never vary clothing between shots
3. **Lighting lock** — Same lighting setup described in every prompt
4. **Setting lock** — Identical environment description when shots share a location
5. **Grade lock** — Same color grade (e.g., "teal-and-magenta") in every prompt
6. **Reference images** — Use asset registry references in every shot (up to 3)

## Shot List JSON Format

```json
{
  "script": "30-second product launch ad for wireless earbuds",
  "target_duration": 30,
  "preset": "tech-saas",
  "shots": [
    {
      "number": 1,
      "duration": 8,
      "type": "establishing",
      "camera": "Slow dolly forward through glass door",
      "subject": "Modern tech showroom, minimalist white shelves",
      "action": "Camera reveals the product display",
      "setting": "Clean tech retail space, morning light",
      "audio": "Ambient: soft electronic hum, SFX: glass door sliding",
      "prompt": "Full VEO prompt here...",
      "start_frame_prompt": "Banana prompt for start frame...",
      "end_frame_prompt": "Banana prompt for end frame...",
      "consistency_notes": "Same showroom lighting throughout"
    }
  ]
}
```

## Cost Estimation

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/video_sequence.py estimate --plan shot-list.json
```

Shows breakdown: storyboard cost + video cost + total before any generation begins.
