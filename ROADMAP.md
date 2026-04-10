# Nano Banana Studio: Expansion Roadmap

## Context

Nano Banana Studio v3.4.0 is a comprehensive Creative Director plugin for AI image and video generation. This roadmap captures planned features, organized by implementation priority.

**Architecture:** Two interlinked skills sharing brand presets and asset registry:
1. **Image Skill** (`/banana`) — 24 commands: generation, editing, social media, slides, brand guides, assets, analytics, content pipeline
2. **Video Skill** (`/video`) — 10 commands: VEO 3.1 generation, image-to-video, multi-shot sequences with storyboard approval, clip extension, FFmpeg toolkit

---

## Completed Features

| # | Feature | Version | Notes |
|---|---------|---------|-------|
| 1 | `/banana slides` — batch slide deck pipeline | v1.6.0 | plan → prompts → generate workflow |
| 2 | `/banana brand` — conversational brand guide builder | v1.7.0 | learn → extract → refine → preview → save |
| 3 | Pre-built brand guide library (12 presets) | v1.7.0 | tech-saas, luxury-dark, organic-natural, etc. |
| 4 | `/banana social` — platform-native generation | v1.7.0 | 46 platforms, ratio grouping, 4K + auto-crop |
| 5 | `/banana asset` — persistent asset registry | v1.8.0 | characters, products, equipment, environments |
| 6 | `/banana reverse` — image-to-prompt reverse engineering | v1.9.0 | Claude vs Gemini perspectives + blended prompt |
| 7 | `/banana book` — visual brand book generator | v2.0.0 | markdown + pptx + html, 3 tiers, Pantone colors |
| 8 | `/banana formats` — multi-format image converter | v2.2.0 | PNG/WebP/JPEG at 4K/2K/1K/512, sips fallback |
| 9 | `/banana history` — session generation history | v2.3.0 | log, list, export as markdown gallery |
| 10 | `/banana ab-test` — A/B prompt variation testing | v2.4.0 | Literal/Creative/Premium + preference learning |
| 11 | `/banana deck` — slide deck builder | v2.5.0 | .pptx with 3 layouts, brand styling, logo placement |
| 12 | `/banana analytics` — analytics dashboard | v2.6.0 | HTML with SVG charts, cost/usage/quota |
| 13 | `/banana content` — multi-modal content pipeline | v2.7.0 | hero + social + email + formats orchestration |
| 14 | `/video` — VEO 3.1 video generation (core) | v3.0.0 | Text-to-video, image-to-video, first/last frame |
| 15 | `/video sequence` — multi-shot production | v3.3.0 | Storyboard approval, first/last frame chaining |
| 16 | `/video extend` + `/video stitch` — extension + FFmpeg toolkit | v3.4.0 | Clip chaining to 148s, concat/trim/convert |
| 17 | VEO 3.1 model variants + draft workflow + Scene Extension v2 | v3.5.0 | Lite/Fast/Standard tiers, `--quality-tier` flag, pricing fixes |

---

## Planned Features

### v3.5.0 — VEO 3.1 Model Variants & Draft Workflow (SHIPPED 2026-04-10)

v3.5.0 shipped the VEO 3.1 model variant work (Standard / Fast / Lite /
Legacy 3.0), corrected pricing, the `--quality-tier` draft-then-final
workflow for sequences, Scene Extension v2 as the default extension
method, token-limit prompt validation, and a full rewrite of
`veo-models.md`. See `CHANGELOG.md` for the full list.

The "Sequence Production Improvements" items below (review gate, plan
hash tracking, audio strategy split, etc.) originally slated for v3.5.0
are **deferred to v3.6.0** — the coffee shop demo surfaced the model
variant gap as a higher-priority blocker, so that work landed first.

### v3.6.0 — Vertex AI Backend + Deferred Sequence Features

**🔴 Top priority: Vertex AI backend for VEO.** Real-API verification
during v3.5.0 release surfaced that VEO 3.1's Lite tier
(`veo-3.1-lite-generate-001`), Legacy 3.0, GA `-001` IDs for Standard
and Fast, and Scene Extension v2 (`--video-input`) are all served only
via Vertex AI (`*-aiplatform.googleapis.com`), not the Gemini API
(`generativelanguage.googleapis.com`) the plugin currently uses. The
Gemini API returns HTTP 404 for every `-001` ID and rejects the video
`inlineData` part for `--video-input`. v3.5.0 ships these features
documented and gated with clear error messages, but they need a real
backend to become callable.

**Scope of the Vertex AI backend work:**

- **Auth path:** OAuth via Application Default Credentials (ADC) or a
  service account JSON. This requires `google-auth` as a dependency,
  which contradicts the script's stdlib-only posture. Options: (a)
  accept `google-auth` as a narrow video-only dependency with
  clear gate-on-import handling, (b) implement OAuth2 token refresh
  manually against Google's token endpoint using stdlib `urllib`
  (harder, but preserves the zero-dependency property), (c) shell out
  to `gcloud auth print-access-token` if installed and fall back.
- **Endpoint:** `https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/google/models/{model}:predictLongRunning`
  — different from the Gemini API pattern, requires a project ID and
  a region.
- **Request shape:** slightly different from Gemini API. Image parts
  use `bytesBase64Encoded` instead of `inlineData.data` (this is the
  same landmine v3.4.1 fixed in the other direction).
- **Config:** add `vertex_project_id` and `vertex_region` to
  `~/.banana/config.json`. Prompt for them in `/banana setup` when
  the user opts into Vertex.
- **Backend selection:** new `--backend {gemini-api,vertex-ai,auto}`
  flag on `video_generate.py`. `auto` picks Vertex when the model ID
  is in `MODELS_VERTEX_ONLY`, otherwise stays on the Gemini API.
- **Once shipped:** remove the gates in `video_generate.py`, re-point
  `--quality-tier draft` back to Lite (from its current Fast fallback),
  and update the draft-then-final workflow tables in
  `video-sequences.md` to show the full 15× cost reduction.

**Carry-over from v3.5.0 plan (original sequence production scope):**

These learnings came from producing the first real 30-second multi-shot sequence (the coffee shop demo for the README). The theoretical pipeline shipped in v3.3.0 works, but these specific gaps surfaced during actual use:

#### Process & UX — Make the approval gate impossible to skip

- **`/video sequence review` subcommand** — Given a plan.json with populated prompts and a storyboard directory, generate a `REVIEW-SHEET.md` that interleaves each shot's frames inline with its VEO prompt, cost estimate, and parameters. This is the artifact I hand-wrote during the demo. The sequence skill should produce it automatically whenever the storyboard changes, so it's always fresh and always current.
- **Default output location should be visible from Finder** — The current `video_sequence.py` writes plans to `/tmp` by default, which is hidden on macOS. Change default to `~/Documents/nano-banana-sequences/<project-name>/` so users can review with Quick Look (`Space` key) out of the box. Keep `--output` flag for explicit overrides.
- **Review sheet should be the mandatory gate between `storyboard` and `generate`** — `video_sequence.py generate` should refuse to run if no `REVIEW-SHEET.md` exists for the current plan, or if the plan hash in the review sheet doesn't match the current plan.json hash (detects stale reviews). Override flag `--skip-review` for CI/automation use.
- **Rename the approval gate step explicitly** — Currently steps are `plan → storyboard → generate → stitch`. Rename to `plan → storyboard → review → generate → stitch`, making the human approval a first-class pipeline stage.

#### Plan freshness — Prevent prompt drift from frame updates

- **Plan hash tracking** — When storyboard frames are regenerated, the sequence script should detect that the frames changed and flag the corresponding prompts as potentially stale. One option: store a SHA-256 of each frame in the plan.json, compare on review-sheet generation, and emoji-flag any shot where the frame has changed since the prompt was last edited.
- **`/video sequence update-prompts` subcommand** — Given a plan with regenerated frames, suggest updated prompt wording that references the new frame details. This would use the image-to-text capability of Gemini to describe the current frame, then propose prompt edits that match.
- **Single source of truth** — During the demo, the plan.json said one thing ("overhead shot") while the actual frames showed another ("three-quarter high angle"). The review-sheet generation should actually *read* the frames and compare against prompt claims before presenting for approval.

#### Sequence architecture — Support "end frame optional" shots

- **Flag: `end_frame: null` explicitly means VEO interpolates** — Add a `use_veo_interpolation: true` field to shots in plan.json. When true, only the start frame is used, and the VEO call drops `--last-frame`. This was a real architectural need in Shot 1 of the coffee shop demo: cutting to an unrelated Shot 2 meant we didn't need to constrain where Shot 1 ended, freeing VEO to execute a dramatic push-in.
- **`video_sequence.py storyboard --shots 1,3` partial regeneration** — Add ability to regenerate frames for specific shots without rebuilding the whole storyboard. Critical for iteration when one frame has a bug but others are approved.
- **Store shot types explicitly: `establishing`, `medium`, `closeup`, `product`, `transition`, `cutaway`, `b-roll`** — This field exists in the plan.json schema but has no semantic effect. It should drive defaults like duration, camera style hints, and whether an end frame is recommended.

#### Image-to-image frame chaining — Make it first-class

- **Add `--reference-image` flag to `generate.py`** — Currently the only way to do reference-based generation is to use `edit.py`, which is misleadingly named. Add `--reference-image PATH` to `generate.py` that passes the image as an `inlineData` part alongside the text prompt. This is the same thing `edit.py` does under the hood, but using `generate.py` makes the intent clear: "generate a new image informed by this reference", not "edit this image".
- **Document the conservatism bias** — Image-to-image mode anchors heavily on source geometry and is excellent for continuity (same cup across shots) but bad for large camera moves (dolly from wide to close-up). The prompt engineering reference should document when to use text-only vs image-reference:
  - **Text-only generation** — Large camera moves, dramatic framing changes, establishing → close-up transitions within a shot
  - **Image-reference generation** — Character/object identity locks, cross-shot prop continuity, minor framing adjustments, style matching
- **Output resolution warning** — Image-reference mode returns half-resolution (~1376×768 from a 2K source). For VEO input this is acceptable (above 720p minimum), but the user should know. Add a note to the generate script's output JSON that says `{"source_resolution": "2K", "output_resolution": "1K-ish", "reason": "image-to-image downscaling"}` when applicable.

#### Audio strategy — Decide dialogue and narration up front

The sequence pipeline currently has a single free-text `audio` field per shot that mixes ambient sound, SFX, dialogue, and narration indiscriminately. In practice these are three architecturally different audio modes, and the decision must be made *before* shot prompts are written because it changes the visuals, timing, and duration:

- **Ambient + SFX (VEO generates natively)** — Background atmosphere and action-matched sound effects. VEO handles these well and they don't constrain the visual prompt. This is what the coffee shop demo uses.
- **On-camera dialogue (VEO generates with lip-sync)** — A character speaks visible lines during the shot. VEO supports this in English with strict constraints:
  - 8-second duration limit (dialogue clips can't be extended)
  - Lip-sync is reliable only for short phrases (3-8 words per clip)
  - The speaking character must be visible in the frame
  - The prompt must explicitly include the line in quotation marks
  - Changes the prompt structure: `A woman says, "Welcome to our cafe," as she places a latte on the counter.`
- **Voiceover narration (post-production overlay)** — Narrator speaks over the sequence without appearing on camera. VEO doesn't generate this; it's added in post. But it affects:
  - Total sequence duration (narration paces the cut lengths)
  - Shot pacing (each shot must be long enough for its share of narration)
  - Visual framing (shots can't introduce audio-distracting elements during narration)
  - Cost (no extra VEO cost, but needs text-to-speech or voice actor + audio editing)

**Implementation tasks for v3.5.0:**

- **Add a sequence-level `narration` field to plan.json** — `narration: null` (none), `narration: "text..."` (voiceover text to be added in post), or `narration: "sync"` (on-camera dialogue only, see per-shot `dialogue` field below).
- **Add a per-shot `dialogue` field to plan.json** — separate from the `audio` field. When present, it signals on-camera sync-sound dialogue and triggers VEO prompt construction that includes the line, timing cues, and lip-sync requirements.
- **Split the `audio` field into `ambient` and `sfx`** — two clean fields instead of one blob. VEO prompts should always include both.
- **`/video sequence plan` should ask about audio strategy up front** — before generating shot skeletons, the planning step should prompt Claude (via the SKILL.md instructions) to ask the user: "Does this sequence have voiceover narration? On-camera dialogue? Ambient only?" and record the answer in the plan. This single decision cascades into every shot's prompt.
- **`/video sequence narration` subcommand** — post-generation, given a finished stitched MP4 and a narration script, call a TTS service (or accept a prerecorded audio file) and mix it into the video using FFmpeg. This lets the same visual sequence be re-used with different narrations (English, French, Spanish) without regenerating any VEO clips. Huge cost saver for multi-language deliverables.
- **Audio strategy reference doc** — Write `references/video-audio.md` additions that cover the three modes, when to use which, VEO's dialogue limitations, and how to structure prompts for each case. Also document the hybrid case: VEO generates ambient + SFX during the shot, post-production adds voiceover on top.

#### Prompt engineering — Discoveries captured in video-prompt-engineering.md

The specific prompt engineering discoveries from this demo have been captured in `skills/video/references/video-prompt-engineering.md` under a new **"Discoveries and Tips from Real Sequence Production"** section. That file is the long-term home for learnings that accumulate over time as we run more sequences.

**Initial tips captured** (see the reference file for full details and examples):

1. Scene bible anchors locked across prompts — identical phrasing, not paraphrases ✅
2. Off-frame composition beats forcing all elements visible ✅
3. Explicit percentage framing for camera moves ✅
4. Image-to-image has conservatism bias ✅
5. ALL CAPS for anatomical and count constraints 🔬
6. Real camera brand names anchor color and grade ✅
7. Audio is three distinct things, not one ✅
8. Not every shot needs an end frame ✅
9. Hybrid storyboard generation (text-only for first frames, image-reference for continuations) ✅

**Evidence levels used in the reference file:**
- ✅ **Demonstrated** — observed in real generation output, bug or improvement reproducible
- 🔬 **Unverified** — reasonable guess from general knowledge or one-shot observation, not yet eval-tested
- 📊 **Measured** — backed by a formal eval run with multiple samples (none yet)

This honest framing means future developers know which tips to trust and which to test. When v3.5.0 implementation work starts, the 🔬 Unverified tips should be targeted for eval runs to promote them to 📊 Measured.

#### VEO API integration fixes already shipped in v3.4.1

These bugs were discovered during the first real VEO test and are documented here so future developers understand the pitfalls:

- ✅ `personGeneration: "allow_adult"` rejected for text-to-video — only omit it, or use `"allow_all"`
- ✅ Image format is `inlineData.data`, not `bytesBase64Encoded`
- ✅ Response path is `response.generateVideoResponse.generatedSamples[0].video.uri`, not `response.generatedSamples`
- ✅ Video URIs require the API key as a query parameter for authenticated download

#### New v3.6.0 items surfaced during v3.5.0 research

- **`--num-videos` flag (1–4 per API call)** — VEO 3.1 supports generating up to 4 variations in a single `predictLongRunning` request, amortizing the setup/denoise overhead. Adds a new output shape (array of paths). Overlaps with the banana skill's `/banana ab-test` — might belong there instead.
- **Object insertion support** — VEO 3.1 can add elements into generated video while maintaining consistent lighting and physics. New flag probably looks like `--insert-object <image.png> --insert-description "a coffee cup on the table"`.
- **Parallel batch execution in `video_sequence.py`** — Currently shots are generated sequentially. Up to 10 concurrent operations are allowed per project. Parallel execution would cut a 4-shot sequence wall-clock from ~4 min to ~1 min at the cost of losing the "fail fast on shot 1" pattern.
- **`output_gcs_uri` support** — Write directly to Cloud Storage instead of downloading and re-uploading. Required for workflows that need videos to outlive the 48-hour retention window without local storage.
- **Regional restrictions awareness** — Detect EEA/Swiss/UK locale and warn when image-to-video features will be restricted. Also surface the `personGeneration: allow_adult` default in those regions.
- **1080p Lite pricing verification** — The reference doc only explicitly states $0.05/sec for 720p Lite. 1080p Lite pricing is unverified. Run a real API call to confirm and update the PRICING dict.
- **Character consistency improvements** — VEO's character drift is a documented limitation. Consider routing character-heavy shots through Replicate backends (Kling 2.6, Seedance 2.0) which handle multi-shot consistency better.

#### Cost and workflow wins to preserve

These worked well and should be documented in the video-sequences reference so future users follow the same pattern:

- **Storyboard:video cost ratio is 15×** ($0.08 per frame vs ~$1.20 per clip) — this is the economic argument for the approval gate. A 30-second, 4-shot sequence costs $0.64 in storyboard and $4.50 in video. If one frame has a bug, the cost of a storyboard regeneration is 0.13% of the cost of regenerating the corresponding clip.
- **Sequential VEO testing over parallel** — fire one clip, inspect it, then decide whether to proceed. A bug found on clip 1 avoids burning 3× the cost on clips 2-4.
- **Hybrid generation mode for storyboard** — use text-only for the first frame of each shot (full control), then image-reference chaining for subsequent frames (consistency). Cross-shot continuity (e.g., the cup in shot 3 end → shot 4 start) uses image-reference.

---

## Future Considerations

- **Figma Plugin Bridge** — Export to Figma frames via API
- **CMS Integration** — Auto-upload to WordPress, Contentful, Sanity
- **E-Commerce Automation** — Connect to Shopify/WooCommerce for product shots
- **3D Object Generation** — When model support exists
- **Interactive Prototypes** — Generate clickable UI mockups
- **Team Collaboration** — Shared presets via git repo

---

## Priority Summary

| # | Feature | Effort | Impact | Status |
|---|---------|--------|--------|--------|
| 1 | v3.5.0 — VEO 3.1 model variants + draft workflow + pricing fixes | Medium | Very High | **Shipped 2026-04-10** |
| 2 | v3.6.0 — Vertex AI backend (unblocks Lite, Scene Extension v2, GA `-001` IDs) | Large | Very High | **Next** |
| 3 | v3.6.0 — Deferred sequence production improvements + batch/parallel features | Medium | High | Next (alongside Vertex) |
| 4 | Replicate video model routing (Kling, Wan, PixVerse) for character consistency | Medium | High | Future |
