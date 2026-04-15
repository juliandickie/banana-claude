# Kling Video Models (v3.8.0+)

> Load this when selecting a Kling model for video generation or when the
> user asks about Kling capabilities, pricing, extended workflows, or known
> limitations. The authoritative source for all content in this file is the
> Kling v3 Std model card at `dev-docs/kwaivgi-kling-v3-video-llms.md`. Any
> discrepancies should be resolved in favor of that file.

## Default model (v3.8.0+)

**Kling v3 Std** (`kwaivgi/kling-v3-video`) is the default video model as of
v3.8.0. It replaces VEO 3.1 Standard, which is now opt-in backup only via
`--provider veo --tier {lite|fast|standard}`.

## Why Kling is the default

Spike 5 (94 video generations, ~$53 total spend) decisively proved Kling v3
Std should replace VEO 3.1 as the plugin's default video model:

- **Kling won 8 of 15 playback-verified shot types** (01 narrative, 04
  product hero, 05 dialogue, 06 action, 07 POV, 08 nature B-roll, 09 fashion,
  11 mascot). VEO 3.1 Fast won 0.
- **7.5× cheaper per 8s clip** than VEO Fast ($0.16 vs $1.20) and 20× cheaper
  than VEO Standard ($0.16 vs $3.20).
- **Native 1:1 aspect ratio support** — VEO does not support 1:1, which
  blocked Instagram-square workflows on the old plugin default.
- **Coherent extended workflows**: Kling's `multi_prompt` produces coherent
  30-second narratives in a single call. VEO's extended workflow (Scene
  Extension v2 + keyframe fallback) produced "glitches, inconsistent actors,
  definitely do not use" per user verdict 2026-04-15.

Full spike findings:
[`spikes/v3.8.0-provider-bakeoff/writeup/v3.8.0-bakeoff-findings.md`](../../../spikes/v3.8.0-provider-bakeoff/writeup/v3.8.0-bakeoff-findings.md)

## Model capabilities

| Property | Kling v3 Std |
|---|---|
| Resolution | 720p (`mode: "standard"`) or 1080p (`mode: "pro"`) |
| Aspect ratios | 16:9, 9:16, **1:1** (VEO does not support 1:1) |
| Duration | **3–15 seconds** per call (integer seconds) |
| Audio | Native, generated with video. **English and Chinese only** per model card |
| Multi-shot | `multi_prompt` JSON array string, up to **6 shots** per call |
| Negative prompts | Supported via `negative_prompt` |
| First + last frame | Supported via `start_image` + `end_image` |
| Prompt max length | 2500 characters (both `prompt` and `negative_prompt`) |

## Pricing

Per the Kling v3 Std model card + spike 5 observed costs at `pro` mode (1080p):

- **8 seconds**: $0.16
- **15 seconds**: ~$0.30
- **Effective rate**: ~$0.02/second (slight fixed-call overhead on short clips)
- **Extended 30s via shot-list pipeline**: ~$0.60 (4 × 8s or 2 × 15s)

Compared to VEO 3.1 at the same duration:

| Model | 8s price | Ratio vs Kling |
|---|---|---|
| Kling v3 Std (pro) | $0.16 | 1.0× |
| VEO 3.1 Lite | $0.40 | 2.5× |
| VEO 3.1 Fast | $1.20 | 7.5× |
| VEO 3.1 Standard | $3.20 | 20× |

## Multi_prompt JSON format

`multi_prompt` is a **JSON array passed as a STRING** (not a parsed list). The
plugin preserves it verbatim without re-serializing. Each shot object has
`prompt` and `duration` fields. **Critical rule from the model card**: the
sum of shot durations must equal the top-level `duration` parameter exactly.

Example for a 15-second 3-shot narrative:

```json
{
  "input": {
    "prompt": "A multi-shot short film",
    "duration": 15,
    "aspect_ratio": "16:9",
    "mode": "pro",
    "generate_audio": true,
    "multi_prompt": "[{\"prompt\": \"An astronaut floats alone in deep space, Earth glowing blue behind them, camera slowly rotating around their helmet reflecting the stars\", \"duration\": 5}, {\"prompt\": \"The astronaut turns to see a massive golden nebula forming into the shape of a human hand reaching toward them, light particles swirling\", \"duration\": 5}, {\"prompt\": \"The astronaut reaches out and touches the nebula hand, which explodes into a billion stars that rush past the camera in every direction\", \"duration\": 5}]"
  }
}
```

Constraints:
- **Max 6 shots** per call
- **Min 1 second per shot**
- **Sum of shot durations must equal the top-level `duration`** — the plugin
  validates this client-side via `_replicate_backend.validate_kling_params()`
  before submitting

## Extended workflows (> 15 seconds)

For clips longer than 15 seconds, use `video_sequence.py` with the existing
plan → storyboard → generate → stitch pipeline. Each shot is an independent
Kling v3 Std API call, stitched by FFmpeg. This is the recommended v3.8.0+
extended workflow path.

```bash
# Plan a 30-second sequence as 4×8s shots
python3 video_sequence.py plan --script "30-second product launch" --target 30

# Generate shots individually (each is a Kling API call)
python3 video_sequence.py generate --storyboard /path/to/storyboard

# Stitch with FFmpeg
python3 video_sequence.py stitch --clips /path/to/clips --output final.mp4
```

**v3.8.0 does NOT include a dedicated "Kling chain" helper** for generating a
single continuous > 15s shot via last-frame extraction. The spike's
`extended_run.py` proved this is possible, but the existing shot-list
pipeline already serves extended workflows via independent API calls per
shot. If a future version introduces a single-continuous-long-shot use case,
the Kling chain helper can be added to `video_sequence.py` in v3.8.x.

## Image-to-video (start_image + end_image)

Kling v3 Std supports both first-frame and first-and-last-frame
interpolation via the `start_image` and `end_image` fields. Constraints from
the model card:

- **Format**: `.jpg / .jpeg / .png`
- **Max size**: **10 MB** (enforced client-side by `image_path_to_data_uri()`)
- **Min dimension**: 300 px on the shortest side
- **Aspect ratio**: must be in [1:2.5, 2.5:1] range
- **`end_image` requires `start_image`** (fails validation otherwise)

**Important caveat from the model card**: `aspect_ratio` is **IGNORED when
`start_image` is provided**. The output uses the start image's native aspect
ratio. The plugin logs a WARNING via `validate_kling_params()` when both are
set, so users aren't surprised.

## Wall time expectations

Kling v3 Std typical wall time per call:
- **Single prompt 8s**: 3–5 minutes
- **Single prompt 15s**: 4–6 minutes
- **Multi-prompt 15s**: 5–7 minutes (3–6 shots)

This is notably longer than VEO 3.1 Lite (~2 minutes per call). Users who
chain many shots in a sequence should expect overall wait times proportional
to `num_shots × ~5 minutes`.

If speed is critical (e.g., rapid iteration), users can drop to
`--provider veo --tier lite` which is ~2 minutes per call but accepts the
spike 5 quality trade-off (glitches in multi-shot workflows).

## Known limitations

Per the Kling v3 Std model card's "Limitations" section, verbatim:

- **Maximum 15 seconds per generation** (use shot-list pipeline for longer)
- **Audio works best in English and Chinese** — other languages are unverified
- **Character appearance can vary across separate generations** — important
  for extended workflows where continuity matters across multiple Kling calls.
  For brand-character consistency, use the same `start_image` across sibling
  calls or adopt the v3.8.x-candidate DreamActor motion-transfer approach
- **Complex physics interactions may not look fully natural**
- **For longer videos, generate multiple clips and stitch them together**
  (this is exactly what the plugin's existing pipeline does)

## When NOT to use Kling

- If the user explicitly requests VEO after reviewing the spike 5 findings
  (`--provider veo --tier lite`)
- If the user needs 4K resolution (Kling maxes at 1080p pro mode; VEO Fast
  and Standard preview IDs support 4K)
- If the user needs video editing mode (not supported by Kling v3 Std; Kling
  v3 Omni has it but was deferred from spike 5 Phase 1 for 25+ min wall time)
- If the user needs reference-image-guided generation (Kling v3 Std does not
  support this; VEO 3.1 does via `referenceImages` at the instance level)
- If the user needs Scene Extension v2 on an existing MP4 (Kling has no
  direct equivalent; use `video_extend.py --acknowledge-veo-limitations` only
  after accepting the spike 5 findings)

## Seedance 2.0 retest outcome (v3.8.1, 2026-04-15)

**Verdict: PERMANENTLY REJECTED for human-subject workflows. Non-human subjects work.**

Spike 5 Phase 1 rejected ByteDance Seedance 2.0 on safety filter E005 with
the bearded-man subject. v3.8.1 retested with 3 diverse Phase 2 subjects
to see if the filter behaved differently:

| Test | Subject | Result | Failure code |
|---|---|---|---|
| `test_02_talking_head` | Woman in home office | **FAILED** (5.5s wall) | `E005 — input/output flagged as sensitive` |
| `test_06_action_sports` | Woman athlete doing kettlebell swing | **FAILED** (8.8s wall) | `E005 — input/output flagged as sensitive` |
| `test_11_brand_mascot` | Cartoon robot | **SUCCESS** ($0.14, 123s wall) | — |

**Pattern**: the E005 filter is consistent across Phase 1 and Phase 2 for
**any human subject** — bearded man, woman in home office, female athlete
all triggered it. Only the non-human cartoon robot mascot passed.

**Implication for the plugin**: Seedance is NOT usable for the plugin's
primary workflows (product demos, talking heads, social creator content)
because those workflows overwhelmingly involve human subjects. A model
that works on "1 out of 3" diverse subjects — and specifically fails on
the most common subject type — can't be a reliable default or even a
reliable backup.

**Decision**: Seedance 2.0 is **NOT wired into the plugin** (neither as a
default, backup, nor tertiary provider). v3.8.0's decision to go with
Kling (primary) + VEO (opt-in backup) stands. If a user has a
specifically non-human workflow (brand mascots, animated characters,
CGI props), they can call Seedance directly via Replicate's SDK — but
the plugin doesn't provide a first-class path.

**Retest spend**: $0.14 (1 successful generation) + $0.48 (12 anchor
images generated for the retest matrix). Total: $0.62. The spike harness
idempotent skip + reservation logic prevented any wasted generation
on the 2 failed cells — ledger correctly released the reservations.

**What would change the verdict**: ByteDance relaxing the E005 filter
specifically for human subjects. No timeline or public roadmap for this.
If a user reports Seedance E005 changes via the Replicate playground,
run the retest again with the same 3 subjects and re-evaluate.

**Full retest artifacts**: `spikes/v3.8.0-provider-bakeoff/runs/phase2-2026-04-15T10-55-10Z/` contains the `meta.json` files with the full E005 error payloads.

